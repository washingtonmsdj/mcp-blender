# Deploy de produção — Cloudflare v3

Cloudflare v3 é o Control Plane de produção do OrdaX Device Agent.

Endpoint verificado:

`https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev`

## Secrets obrigatórios

Configure no environment GitHub `cloudflare-v3`:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `ORDAX_OPERATOR_TOKEN`

Nenhum desses valores deve ser commitado.

## Workflow de deploy

Use **Deploy Cloudflare v3 Control Plane** via `workflow_dispatch`.

O workflow falha antes do checkout se algum secret obrigatório estiver ausente.
Depois:

1. localiza/cria o subdomínio `workers.dev`;
2. localiza/cria D1 `ordax-control-plane-v3`;
3. localiza/cria R2 `ordax-device-artifacts`;
4. gera configuração Wrangler temporária fora do checkout;
5. aplica migrations D1;
6. publica Worker + Durable Objects + secret em uma operação controlada;
7. espera `GET /health`;
8. executa E2E remoto completo: WebSocket, job, lease, D1, R2 e terminal report;
9. remove o device/job/artifact temporário da prova;
10. apaga arquivos temporários do runner.

## Enrollment de dispositivo

No Windows:

```powershell
.\scripts\windows\ordax-device-agent-setup.ps1
```

O endpoint padrão já é o Worker de produção. O token do dispositivo é gerado
localmente e somente seu SHA-256 é enviado ao Control Plane.

## Smoke de dispositivo

Use o workflow **Cloudflare v3 Device Smoke** com o UUID do dispositivo.

A ação padrão é:

`blender.version`

O workflow cria um job tipado, espera o resultado terminal e falha se o job
terminar como `failed`, `cancelled` ou exceder o prazo.

## Evidência de produção

Em 2026-09-27 foram confirmados:

- `/health` saudável;
- enrollment Cloudflare v3;
- reconexão após reboot real do Windows;
- heartbeat fresco;
- smoke remoto `blender.version` bem-sucedido;
- estado local de providers antigos removido.

A partir do Device Agent 1.22.0, Cloudflare v3 é o único provider remoto
suportado pelo repositório.
