# ORDAX Studio para Windows

## Objetivo

O produto Windows não depende de Codex, ChatGPT, Claude, Git ou Python instalados na máquina do usuário. Esses sistemas podem atuar como clientes do ORDAX MCP, mas não fazem parte do runtime do produto.

A distribuição canônica é um instalador clicável:

`ORDAX-Studio-Setup-<versão>-x64.exe`

Depois da instalação, existem dois entrypoints nativos:

- `ORDAX Studio.exe`: interface gráfica do produto;
- `ORDAX Runtime.exe`: conector persistente da máquina com o ORDAX Control Plane.

## Layout instalado

A instalação por usuário fica em `%LOCALAPPDATA%\Programs\ORDAX Studio` e contém:

```text
ORDAX Studio.exe
ORDAX Runtime.exe
product-manifest.json
runtime\
  python.exe
  pythonw.exe
  Lib\site-packages\...
scripts\
redist\
  MicrosoftEdgeWebview2Setup.exe
```

O CPython em `runtime\` é privado ao produto. Ele não é registrado no `PATH`, não substitui o Python do usuário e não é uma dependência externa.

## Inicialização

O instalador registra `ORDAX Runtime.exe` no auto-start do usuário. O runtime inicia sem console, cria uma única instância e supervisiona o Device Agent. Se o processo do agente cair, o supervisor nativo reinicia com backoff limitado.

`ORDAX Studio.exe` também é single-instance e inicia `ordax_studio.web_desktop` pelo runtime privado.

Os launchers definem somente defaults de produto para `ORDAX_PACKAGED_ROOT`, `ORDAX_AGENT_REPO_PATH` e `ORDAX_BRIDGE_PATH`. Variáveis explicitamente configuradas pelo ambiente continuam tendo precedência.

## Conectividade

O fluxo de produto é:

```text
Cliente MCP autorizado
        |
        v
ORDAX Remote MCP / Control Plane
        |
        v
ORDAX Runtime no Windows
        |
        +-- projetos / Git / preview
        +-- Blender Live
        +-- Unity / adapters
```

O computador abre a conexão para o Control Plane; o usuário não precisa expor portas no roteador nem iniciar um servidor manual em PowerShell.

## Compatibilidade com o desenvolvimento

`scripts/windows/ordax-studio-install.ps1`, `mcp-start.ps1` e os launchers de desenvolvimento permanecem no repositório para smoke, recuperação e desenvolvimento local. Eles não são o fluxo de instalação destinado ao usuário final.

## Build

O build oficial roda em Windows x64 e:

1. baixa uma versão fixada do CPython embeddable;
2. instala o pacote ORDAX e dependências dentro do runtime privado;
3. valida imports usando o próprio Python privado;
4. compila os launchers Win32 com MSVC;
5. inclui o bootstrapper oficial do WebView2;
6. compila o instalador com Inno Setup;
7. publica o `Setup.exe` e `SHA256SUMS.txt` como artifact do GitHub Actions.

O pipeline está em `.github/workflows/windows-product-build.yml` e o build local/CI em `scripts/windows/build-ordax-studio-product.ps1`.

## ORDAX OS

O empacotamento descrito neste documento é apenas o host Windows. O core, o Device Agent, os contratos MCP e as capabilities não devem depender dele. No `prototipo-ordax-os`, o Studio será um app first-party sobre o mesmo runtime/capabilities, sem carregar o instalador ou os launchers Win32.
