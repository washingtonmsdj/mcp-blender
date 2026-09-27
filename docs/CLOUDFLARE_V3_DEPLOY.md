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
Depois disso, use o cutover transacional na estação Windows:

```powershell
.\scripts\windows\ordax-cloudflare-v3-cutover.ps1 \
  -ControlPlaneUrl "https://<worker>.<subdomain>.workers.dev"
```

O cutover:

1. recusa interromper um job em andamento;
2. preserva a identidade/credencial `development-v2`;
3. faz o enrollment `cloudflare-v3` enquanto o agente v2 ainda está rodando;
4. salva snapshot da configuração;
5. reinicia somente o Device Agent;
6. exige novo processo, provider/URL/device corretos e heartbeat v3 recente;
7. se qualquer etapa v3 falhar, restaura `development-v2` e reinicia;
8. se v3 passar, mantém o snapshot v2 até a prova pós-reboot.

O limite do Supabase já pode estar esgotado. Por isso um heartbeat v2 remoto
desatualizado não impede o corte se o agente local estiver respondendo e ocioso.
Já o novo v3 **não é aceito** sem heartbeat Cloudflare recente.

## Prova final antes de retirar Supabase

Depois do cutover bem-sucedido:

1. salve o trabalho e faça um **reboot real do Windows**;
2. faça login e aguarde o Device Agent reconectar;
3. envie pelo novo Control Plane pelo menos um job remoto `blender.*` e confirme
   sucesso;
4. execute:

```powershell
.\scripts\windows\ordax-cloudflare-v3-finalize.ps1
```

O finalizador usa o relógio monotônico do Windows (`TickCount64`) para provar
que houve um novo boot, exige heartbeat v3 recente e exige que o último job remoto
bem-sucedido seja `blender.*`. Só então:

1. grava `cloudflare-v3-finalized.json` com a evidência local, sem segredo;
2. remove `supabase_url`, `publishable_key` e a identidade
   `development-v2` de `agent-settings.json`;
3. remove apenas os arquivos de credencial v2/legados conhecidos;
4. preserva `device-token.cloudflare-v3.txt`;
5. remove o snapshot local de rollback.

Isso aposenta o Supabase **na estação** somente depois da prova final. A remoção
do código/backend Supabase do repositório continua sendo uma mudança posterior,
separada e auditável.
