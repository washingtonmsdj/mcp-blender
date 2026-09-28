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

Uploads de até 90 MiB são enviados diretamente ao R2 com SHA-256 fornecido pelo
Agent como checksum nativo. O backend registra tamanho e digest em D1 e só
publica o artifact depois de validar a integridade.

Arquivos maiores usam multipart R2 com sessão idempotente em D1. Cada parte é
autenticada e verificada por SHA-256 no Worker; na conclusão o objeto inteiro é
relido como stream e validado por SHA-256 antes da publicação. O Agent usa partes
de 64 MiB e até 10.000 partes, mantendo cada request abaixo do limite do Worker.
Uploads multipart abandonados são descartados pelo lifecycle do R2 e as sessões
D1 antigas são limpas antes de novos uploads.

## Segurança

- token administrativo separado do token do dispositivo;
- token do dispositivo armazenado somente como SHA-256 no D1;
- binding máquina/dispositivo;
- API tipada e allow-list local;
- URLs temporárias de leitura para artifacts;
- sem shell remoto genérico.

### Terminal report replay

Terminal job results carry a unique `report_id` stored in D1. An identical replay
with the same lease, execution epoch, runtime identity, status, result digest,
canonical result JSON and error code is acknowledged as already committed. Any divergent
replay is rejected as `terminal_report_conflict`.

### Durable terminal outbox

The Device Agent persists terminal reports under its local state directory before
network delivery. Startup recovery uses `POST /v3/device/recover-report` with the
device credential and the original execution context, before opening the device
WebSocket. D1 accepts the report only if that execution context is still current,
or acknowledges it if the identical terminal report was already committed.

A `running` job is never re-leased automatically. It fences later jobs for that
device until terminal recovery succeeds or an operator resolves the stalled job.
This prevents an expired lease from becoming an implicit second execution of a
Blender/Unity/Git mutation.
