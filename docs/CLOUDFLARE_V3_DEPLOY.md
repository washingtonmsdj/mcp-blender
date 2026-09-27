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

1. localiza o subdomínio `workers.dev` da conta; se ainda não existir, cria
   `ordax-<prefixo-da-conta>` automaticamente;
2. localiza ou cria `ordax-control-plane-v3` no D1;
3. localiza ou cria `ordax-device-artifacts` no R2;
4. gera configuração Wrangler temporária fora do checkout, com `workers_dev=true`;
5. aplica migrations D1 remotas;
6. cria um arquivo de secrets temporário fora do checkout e com permissão restrita;
7. faz um único `wrangler deploy --secrets-file`, enviando código + `ORDAX_OPERATOR_TOKEN` juntos;
8. descobre a URL pública final e espera `GET /health` responder;
9. executa o E2E completo contra a Cloudflare real: WebSocket, job, lease, D1,
   R2 upload/download e terminal report;
10. remove o device/job/artifact temporário usado na prova;
11. apaga configuração e arquivo de secrets temporários ao sair.

O ID do banco D1 não é commitado. Os arquivos gerados ficam no diretório
temporário do runner e são removidos por `trap` ao final. O primeiro deploy não
depende de um Worker pré-existente: o secret é enviado junto com o código via
`--secrets-file`.

## Primeiro corte

O workflow de deploy já comprova automaticamente `/health` e o E2E remoto.
Se ele terminar verde, ficam pendentes somente a prova de enrollment GitHub da
máquina real e o corte do Device Agent:

1. validar `POST /v3/device/setup` através do setup oficial com o login GitHub
   de um administrador do repositório;
2. atualizar o Device Agent usando a URL verificada mostrada no Summary do workflow:

   ```powershell
   .\scripts\windows\ordax-device-agent-setup.ps1 `
     -ControlPlaneProtocol cloudflare-v3 `
     -ControlPlaneUrl "https://<worker>.workers.dev"
   ```

   O PC gera a nova credencial localmente; não copie token do dashboard.

3. confirmar que o Agent ficou em:
   - `control_plane_protocol = cloudflare-v3`
   - `control_plane_url = https://<worker>.workers.dev`
   - o `development_device_id` provisionado;
4. reiniciar a Scheduled Task e confirmar reconnect;
5. fazer um reboot real do Windows e confirmar novo `boot_id` + job Blender;
6. manter Supabase v2 disponível até essa prova pós-reboot;
7. remover v2 apenas em uma mudança posterior e explícita.
