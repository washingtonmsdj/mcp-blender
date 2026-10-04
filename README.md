# ORDAX Studio

> **Nome histórico do repositório:** `mcp-blender`. O nome do repositório é mantido por compatibilidade. O produto user-facing é **ORDAX Studio**.

ORDAX Studio é a bancada de projetos e ferramentas do ORDAX. Ele é **provider-neutral**: ChatGPT, Grok, Codex e outros clientes de IA são integrações externas autorizadas, não runtimes ou variantes do Studio.

No Windows, o produto usa um host persistente **ORDAX Runtime** para manter projetos e capacidades do computador disponíveis mesmo com a janela do Studio fechada. O launcher instalado ainda pode usar o nome histórico `ORDAX Dev.exe` durante a janela de compatibilidade de upgrade; isso não define a identidade do produto.

A arquitetura de providers está em [`docs/ORDAX_PROVIDER_CONNECTORS.md`](docs/ORDAX_PROVIDER_CONNECTORS.md). Modos de IA, handoff e consumo de cota estão em [`docs/ORDAX_INTELLIGENCE_MODES.md`](docs/ORDAX_INTELLIGENCE_MODES.md).

## Como funciona

```text
ChatGPT / Grok / outro cliente autorizado
              |
              | conector/protocolo autenticado
              v
ORDAX Control Plane · Cloudflare
              |
              | conexão persistente de saída
              v
ORDAX Runtime.exe · Windows
              |
              +-- projetos / arquivos / Git
              +-- processos / preview / artifacts
              +-- sessões / checkpoints
              +-- Computer Control
              +-- Blender / Unity / adapters
```

O **ORDAX Studio** é a superfície de produto. O **ORDAX Runtime.exe** é infraestrutura local provider-neutral e inicia com o Windows. O Runtime não depende de ChatGPT, Grok ou Codex para existir ou executar capacidades locais autorizadas.

## Produto Windows

A distribuição atual permanece compatível com instalações anteriores:

`ORDAX-Dev-Setup-<versão>-x64.exe`

O instalador inclui runtime Python privado e WebView2 quando necessário. Não exige Python instalado pelo usuário e não adiciona Python ao PATH.

No Studio você encontra:

- catálogo de projetos/workspaces;
- visão geral de repositório e conexão;
- arquivos e editor;
- busca no código;
- Git diff/status;
- memória, tarefas e checkpoints;
- MCP/capabilities;
- Computer Control e política local;
- preview web e evidência visual;
- adapters Blender e Unity.

Nesta etapa **não existe licença, assinatura ou plano pago**. A conexão de Conta ORDAX é separada das integrações de IA e serve para autenticação/vínculo do dispositivo quando o fluxo remoto exigir.

Veja [produto Windows](docs/ORDAX_STUDIO_WINDOWS_PRODUCT.md) e [arquitetura do produto](docs/ORDAX_STUDIO_PRODUCT.md).

## Conectores de IA

O conector atual do ChatGPT se chama **ORDAX for ChatGPT** e vive em `plugins/ordax-chatgpt/`. Ele aponta para o mesmo MCP remoto provider-neutral do Control Plane:

`https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/mcp`

No futuro, **ORDAX for Grok** ou outro provider deve reutilizar o mesmo Control Plane, grants e ações tipadas. Não deve existir implementação `chatgpt_*`, `grok_*` ou `codex_*` das capacidades locais.

Veja [conectores de provider](docs/ORDAX_PROVIDER_CONNECTORS.md) e [conexão ChatGPT atual](docs/PRODUCT_MCP_CONNECT.md).

## Runtime e arquitetura

O Runtime usa um único `ActionRegistry` tipado. Arquivos, Git, preview, Computer Control, Blender, Unity e futuros adapters não mantêm backends paralelos por provider.

Componentes principais:

```text
ordax_studio/        superfície e experiência do Studio
ordax_dev_agent/     ActionRegistry e ações locais
ordax_device_agent/  runtime persistente do dispositivo
ordax_core/          infraestrutura compartilhada do host atual
control-plane/       Control Plane Cloudflare
plugins/             conectores/manifests para clientes externos
packaging/windows/   instalador e launchers do produto Windows
```

No OrdaX OS, o Studio será um app first-party que consome os ports públicos da plataforma; ele não deve empacotar uma segunda cópia de Identity, Memory, Intelligence, permissions, updater ou trust. O destino arquitetural está em `washingtonmsdj/ordax-apps`.

O MCP local continua disponível para desenvolvimento e diagnóstico:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
ordax-studio-mcp
```

Esse MCP local não é dependência do fluxo de produto remoto. Aliases históricos permanecem apenas quando necessários para compatibilidade.

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
- provider/client metadata não concede autoridade por si só;
- o Runtime faz conexão de saída; não expõe o computador inteiro como um shell público;
- a UI do ORDAX Studio não é uma fronteira de autoridade: as validações continuam no Runtime/Control Plane;
- um conector de provider não pode contornar grants nem a política local do dispositivo.

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
