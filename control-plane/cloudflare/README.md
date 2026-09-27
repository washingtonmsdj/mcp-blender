# OrdaX Control Plane v3 — Cloudflare

Este diretório contém o Control Plane remoto de produção do OrdaX Device Agent.

## Runtime

- **Worker**: autenticação de dispositivo, API administrativa e gateway HTTP de artifacts.
- **Durable Object por dispositivo**: WebSocket persistente, entrega serializada de jobs,
  leases, progresso e terminal reports.
- **D1**: dispositivos, jobs, eventos e metadados de artifacts.
- **R2**: bytes de screenshots, snapshots e exports.

O `ActionRegistry` local continua sendo a autoridade final. O backend não
adiciona shell remoto genérico.

## Provisionamento

O setup oficial do Windows usa:

`scripts/windows/ordax-device-agent-setup.ps1`

A credencial é gerada localmente em:

`%LOCALAPPDATA%\OrdaX\DevAgent\device-token.cloudflare-v3.txt`

Somente o SHA-256 é enviado ao Worker.

`agent-settings.json` mantém `control_plane_protocol`, `control_plane_url`
e `device_id`.

## Deploy

O workflow **Deploy Cloudflare v3 Control Plane** cria/localiza os recursos,
aplica migrations, publica o Worker, valida `/health` e executa o E2E remoto.

Configuração:

- `wrangler.toml`: configuração de produção.
- `wrangler.ci.toml`: configuração isolada para CI/local.
- `migrations/`: schema D1.
- `src/index.ts`: Worker e Durable Objects.

## Artifact integrity

Uploads são enviados diretamente ao R2 com SHA-256 fornecido pelo Agent como
checksum nativo. O backend também registra tamanho e digest em D1 e valida a
integridade antes de publicar o artifact.

Artifacts pequenos usam PUT direto. Arquivos acima do limite de upload direto
continuam sujeitos ao contrato de tamanho documentado pelo Agent até existir
suporte multipart explícito.

## Segurança

- token administrativo separado do token do dispositivo;
- token do dispositivo armazenado somente como SHA-256 no D1;
- binding máquina/dispositivo;
- API tipada e allow-list local;
- URLs temporárias de leitura para artifacts;
- sem shell remoto genérico.
