# MCP Blender + Unity CLI

Este repositório foi reduzido para uma única função: ponte local MCP + automação de Blender e Unity por CLI.

O antigo conteúdo do Ordax Engine foi removido da main. Uma cópia histórica ficou preservada na branch:

archive/ordax-engine-before-cleanup-2026-09-17

## Objetivo

~~~text
ChatGPT / cliente MCP
        |
        v
mcp-blender-unity
        |
        +--> Blender CLI
        |
        +--> Unity CLI
                 |
                 +--> HORDAX-game
~~~

Este repositório não contém o jogo HORDAX. O HORDAX continua no repositório próprio.

## Estrutura

~~~text
mcp_blender_unity/
  config.py
  process.py
  server.py

scripts/windows/
  blender-run.ps1
  toolchain-status.ps1
  unity-run.ps1

.github/workflows/
  toolchain-smoke.yml
  unity-hordax-validate.yml

.env.example
pyproject.toml
~~~

## Instalação local

Requer Python 3.11+.

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
~~~

Variáveis suportadas:

- BLENDER_EXE
- UNITY_EXE
- DEFAULT_UNITY_PROJECT

Se BLENDER_EXE e UNITY_EXE não forem definidos, o servidor tenta localizar instalações comuns automaticamente.

## Executar o MCP por stdio

~~~powershell
python -m mcp_blender_unity.server
~~~

## Tools MCP

O servidor expõe:

- toolchain_status
- blender_version
- blender_run_python
- unity_validate_project
- unity_run_method

Os processos são executados diretamente, sem shell=True.

## Unity CLI

~~~powershell
.\scripts\windows\unity-run.ps1 -ProjectPath "C:\dev\HORDAX-game" -ExecuteMethod "HORDAX.EditorTools.CiValidation.Run"
~~~

O wrapper usa -batchmode -quit -projectPath -executeMethod -logFile.

## Blender CLI

~~~powershell
.\scripts\windows\blender-run.ps1 -PythonScript "C:\dev\scripts\generate_asset.py"
~~~

## Self-hosted runner

Os workflows deste repositório são deliberadamente limitados a workflow_dispatch. Não execute código de pull requests não confiáveis em uma máquina self-hosted com Blender/Unity instalados.

toolchain-smoke.yml confirma que Blender e Unity podem ser localizados.

unity-hordax-validate.yml executa o Unity em batch mode em uma máquina self-hosted. Configure a variável de repositório HORDAX_PROJECT_PATH com o caminho local do clone do HORDAX nessa máquina.

## Segurança

Não versione tokens, chaves, licenças ou credenciais. O antigo .env versionado foi removido da main.

Use GitHub Secrets, variáveis do runner ou variáveis de ambiente locais.
