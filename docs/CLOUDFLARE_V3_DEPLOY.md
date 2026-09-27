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
5. atualiza `ORDAX_OPERATOR_TOKEN` como Worker secret;
6. faz deploy do Worker + Durable Object.

O ID do banco D1 não é commitado. O arquivo gerado fica no diretório temporário
do runner, portanto uma conta Cloudflare nunca fica acoplada ao código-fonte.

## Primeiro corte

Depois do primeiro deploy:

1. testar `GET /health`;
2. provisionar uma identidade de teste em `POST /v3/devices`;
3. executar a prova remota de job + artifact;
4. somente então atualizar um Device Agent para:
   - `control_plane_protocol = cloudflare-v3`
   - `control_plane_url = https://<worker>.workers.dev`
   - o `development_device_id` provisionado;
5. reiniciar e confirmar reconnect;
6. manter Supabase v2 disponível até a prova pós-reboot;
7. remover v2 apenas em uma mudança posterior e explícita.
