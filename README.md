# ORDAX Dev

> **Nome histórico do repositório:** `mcp-blender`. O nome do repositório é mantido por compatibilidade; o produto atual é **ORDAX Dev**.

ORDAX Dev é um host local de desenvolvimento para Windows. Ele mantém projetos e ferramentas do computador disponíveis para clientes MCP autorizados, sem incorporar um segundo chat ou depender do Codex.

A arquitetura de IA, handoff e consumo de cotas é é definida em [`docs/ORDAX_INTELLIGENCE_MODES.md`](docs/ORDAX_INTELLIGENCE_MODES.md). Em particular, uso do plano ChatGPT por um aplicativo externo é distinto do chat normal e deve ser apresentado como consumo da cota de **ChatGPT Work e Codex** quando esse modo estiver disponível.

## Como funciona

```text
ChatGPT normal / outro cliente MCP
              |
              | MCP HTTPS autenticado
              v
ORDAX Control Plane · Cloudflare
              |
              | conexão persistente de saída
              v
ORDAX Runtime.exe · Windows
              |
              +-- projetos / arquivos / Git
              +-- processos / preview / artifacts
              +-- memória / sessões / checkpoints
              +-- Blender / Unity / adapters
```

O **ORDAX Dev.exe** é o painel local. O **ORDAX Runtime.exe** inicia com o Windows e permanece disponível mesmo quando o painel é fechado.

## Produto Windows

A distribuição canônica é:

`ORDAX-Dev-Setup-<versão>-x64.exe`

O instalador inclui runtime Python privado e WebView2 quando necessário. Não exige Python instalado pelo usuário e não adiciona Python ao PATH.

No painel você encontra:

- catálogo de projetos/workspaces;
- visão geral de repositório e conexão;
- arquivos e editor;
- busca no código;
- Git diff/status;
- memória, tarefas e checkpoints;
- MCP/capabilities;
- preview web e evidência visual;
- adapters Blender e Unity.

Nesta etapa **não existe licença, assinatura ou plano pago**. A conexão de conta ORDAX é opcional e serve somente para autenticar/vincular o dispositivo.

Veja [produto Windows](docs/ORDAX_STUDIO_WINDOWS_PRODUCT.md) e [arquitetura do produto](docs/ORDAX_STUDIO_PRODUCT.md).

## ChatGPT / MCP remoto

O adaptador oficial está em `plugins/ordax-studio/` e aponta para:

`https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/mcp`

A conversa permanece no ChatGPT normal. O ORDAX fornece as ferramentas locais.

Veja [conexão MCP](docs/PRODUCT_MCP_CONNECT.md).

## Runtime e arquitetura

O Runtime usa um único `ActionRegistry` tipado. Arquivos, Git, preview, Blender, Unity e futuros adapters não mantêm backends paralelos.

Componentes principais:

```text
ordax_studio/        painel, MCP e superfície de produto
ordax_dev_agent/     ActionRegistry e ações locais
ordax_device_agent/  runtime persistente do dispositivo
ordax_core/          memória e infraestrutura compartilhada
control-plane/       Control Plane Cloudflare
plugins/             manifests para clientes externos
packaging/windows/   instalador e launchers do produto
```

O MCP local continua disponível para desenvolvimento e diagnóstico:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
ordax-studio-mcp
```

Aliases históricos permanecem apenas quando necessários para compatibilidade.

## Device Agent

Para recuperar/configurar uma estação de desenvolvimento existente:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\ordax-device-agent-setup.ps1
```

O GitHub Runner não é requisito para uso normal do produto. Ele é utilizado somente em validações que realmente precisam da estação física, Blender ou Unity.

Veja [Device Agent setup](docs/DEVICE_AGENT_SETUP.md).

## Blender e Unity

Blender e Unity são adapters do mesmo ORDAX Runtime.

O Blender Live mantém contratos tipados, fingerprints, checkpoints, quality gates, multiview e operações de modelagem promovidas por testes. Unity mantém descoberta de Editor, compile/validation, recuperação e captura.

Documentação técnica:

- [Blender modeling contracts](docs/BLENDER_MODELING_CONTRACTS.md)
- [Blender roadmap](docs/BLENDER_MODELING_ROADMAP.md)
- [Reference Contract](docs/REFERENCE_CONTRACT.md)
- [Versionamento por componente](docs/VERSIONING.md)

## Segurança

- nenhuma credencial deve ser versionada;
- acesso remoto é autenticado e auditável;
- projetos são registrados explicitamente;
- capacidades privilegiadas são separadas por policy/grant;
- o Runtime faz conexão de saída; não expõe o computador inteiro como um shell público;
- a UI do ORDAX Dev não é uma fronteira de autoridade: as validações continuam no Runtime/Control Plane.

## Desenvolvimento

Validação principal:

```powershell
python -m unittest
```

Workflows relevantes:

- **Bridge CI** — unit tests, contratos, scripts e Cloudflare;
- **Windows Product Build** — compila instalador, instala, atualiza sobre runtime ativo e desinstala;
- **OrdaX Agent Recovery** — recuperação da estação Windows;
- workflows Blender/Unity específicos — apenas quando necessário.

A arquitetura canônica deve ser alterada sem criar atalhos paralelos ou fallbacks que escondam falhas.
