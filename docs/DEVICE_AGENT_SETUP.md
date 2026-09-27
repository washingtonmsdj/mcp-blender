# Instalação e recuperação do Device Agent

O OrdaX Device Agent usa **Cloudflare v3** como único Control Plane remoto.

Endpoint de produção:

`https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev`

## Instalação no Windows

Na cópia do repositório:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\ordax-device-agent-setup.ps1
```

O script:

1. mantém o checkout gerenciado em `%LOCALAPPDATA%\OrdaX\DevAgent\src`;
2. aceita somente fast-forward da `main`;
3. preserva árvore local divergente/suja em vez de usar `reset --hard`;
4. cria ou repara o ambiente Python;
5. instala o supervisor externo e a Scheduled Task;
6. faz enrollment/recovery no Cloudflare v3;
7. espera heartbeat remoto recente antes de emitir `ORDAX_DEVICE_AGENT=READY`.

Use `-NonInteractive` quando o login GitHub já estiver válido e nenhuma UI puder ser aberta.

Para testar outro endpoint compatível:

```powershell
.\scripts\windows\ordax-device-agent-setup.ps1 `
  -ControlPlaneUrl "https://control.example"
```

## Identidade e credencial

O setup usa o GitHub CLI para provar que o usuário possui permissão `admin` no
repositório oficial. A identidade do usuário não vira credencial do Agent.

Cada máquina possui um binding SHA-256 derivado do Windows MachineGuid. O token
aleatório do dispositivo nasce localmente e fica em:

`%LOCALAPPDATA%\OrdaX\DevAgent\device-token.cloudflare-v3.txt`

Somente o SHA-256 do token é enviado ao Worker. O token bruto não é salvo no
GitHub, D1 ou logs.

`agent-settings.json` mantém somente os campos ativos do Control Plane:

- `control_plane_protocol: "cloudflare-v3"`
- `control_plane_url`
- `device_id`

O setup remove automaticamente chaves e arquivos conhecidos de providers antigos
somente depois de confirmar uma identidade Cloudflare válida.

## Recuperação no boot

A Scheduled Task executa o bootstrap externo em:

`%LOCALAPPDATA%\OrdaX\DevAgent\bootstrap\ordax-agent-bootstrap.ps1`

O bootstrap:

- inicia no desktop do usuário, não em Session 0;
- valida a credencial Cloudflare;
- recupera a identidade usando o setup compartilhado quando necessário;
- nunca usa um provider alternativo;
- mantém o Agent vivo sem depender do GitHub Runner;
- executa atualização segura somente entre execuções do Agent;
- aceita apenas fast-forward;
- compila o código antes de aceitar uma atualização;
- restaura o commit anterior se a compilação/instalação falhar.

Erros de rede não rotacionam a credencial automaticamente.

## Critério de prontidão

`ORDAX_DEVICE_AGENT=READY` exige:

- `control_plane_protocol == "cloudflare-v3"`;
- `device_id` válido e igual ao settings;
- URL do Control Plane esperada;
- heartbeat recente;
- supervisor externo ativo;
- Scheduled Task apontando para o bootstrap externo;
- projetos locais conhecidos registrados quando presentes.

`paired=true` sozinho não é prova de conexão.

## Verificação e smoke real

Verificação local/reboot:

```powershell
.\scripts\windows\ordax-device-agent-verify.ps1 -PrepareReboot
# reinicie o Windows
.\scripts\windows\ordax-device-agent-verify.ps1 -AfterReboot
```

Smoke remoto de produção: workflow **Cloudflare v3 Device Smoke**. A ação padrão
é `blender.version`, enviada pelo Control Plane usando o secret
`ORDAX_OPERATOR_TOKEN` do environment `cloudflare-v3`.

O fluxo de produção foi validado em 2026-09-27 com reboot real, heartbeat
Cloudflare recente e `blender.version` concluído com sucesso.

## GitHub Actions

O GitHub Runner não participa do boot, heartbeat, enrollment ou recovery normal.
Ele permanece apenas como canal secundário para CI e ações manuais que exigem o
toolchain da estação.

Referências:

- GitHub authenticated user API
- GitHub repository permissions API
- Cloudflare Workers, Durable Objects, D1 e R2
