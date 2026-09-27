# Deploy de produção — Cloudflare v3

O deploy de produção é **manual** pelo workflow GitHub Actions
`Deploy Cloudflare v3 Control Plane`. A `main` não publica automaticamente.

## Secrets obrigatórios

Configure no environment GitHub `cloudflare-v3`:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `ORDAX_OPERATOR_TOKEN`

Não grave nenhum desses valores no repositório.

O token Cloudflare deve ficar restrito à conta usada pelo OrdaX. Para o primeiro
provisionamento ele precisa conseguir criar/administrar o Worker, o banco D1 e o
bucket R2. Depois que os recursos existem, a permissão pode ser reduzida para o
mínimo necessário à rotina de deploy/migrations.

`ORDAX_OPERATOR_TOKEN` é uma credencial própria do OrdaX para as rotas
administrativas `/v3/devices` e `/v3/jobs`. Use um segredo aleatório forte e
independente da credencial Cloudflare e das credenciais do Device Agent.

## O que o workflow faz

O script `scripts/cloudflare/deploy-v3.sh` é idempotente:

1. localiza ou cria `ordax-control-plane-v3` no D1;
2. localiza ou cria `ordax-device-artifacts` no R2;
3. gera configuração Wrangler temporária fora do checkout;
4. aplica migrations D1 remotas;
5. cria um arquivo de secrets temporário fora do checkout e com permissão restrita;
6. faz um único `wrangler deploy --secrets-file`, enviando código + `ORDAX_OPERATOR_TOKEN` juntos;
7. apaga configuração e arquivo de secrets temporários ao sair.

O ID do banco D1 não é commitado. Os arquivos gerados ficam no diretório
temporário do runner e são removidos por `trap` ao final. O primeiro deploy não
depende de um Worker pré-existente: o secret é enviado junto com o código via
`--secrets-file`.

## Primeiro corte

Depois do primeiro deploy:

1. testar `GET /health`;
2. executar a prova remota de job + artifact com uma identidade de teste;
3. validar `POST /v3/device/setup` com o login GitHub de um administrador do repositório;
4. somente então atualizar um Device Agent usando o setup oficial:

   ```powershell
   .\scripts\windows\ordax-device-agent-setup.ps1 `
     -ControlPlaneProtocol cloudflare-v3 `
     -ControlPlaneUrl "https://<worker>.workers.dev"
   ```

   O PC gera a nova credencial localmente; não copie token do dashboard.

5. confirmar que o Agent ficou em:
   - `control_plane_protocol = cloudflare-v3`
   - `control_plane_url = https://<worker>.workers.dev`
   - o `development_device_id` provisionado;
6. reiniciar a Scheduled Task e confirmar reconnect;
7. fazer um reboot real do Windows e confirmar novo `boot_id` + job Blender;
8. manter Supabase v2 disponível até essa prova pós-reboot;
9. remover v2 apenas em uma mudança posterior e explícita.
