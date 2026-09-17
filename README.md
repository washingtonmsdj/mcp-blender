# MCP Blender + Unity CLI

Ponte local para controlar **Blender CLI** e **Unity CLI** por MCP e para executar validações pelo GitHub em um self-hosted runner.

O antigo Ordax Engine foi removido da `main`. O snapshot anterior está preservado em:

`archive/ordax-engine-before-cleanup-2026-09-17`

## Arquitetura

```text
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
```

O HORDAX permanece no repositório `washingtonmsdj/HORDAX-game`.

## Estrutura

```text
mcp_blender_unity/
  config.py
  process.py
  server.py

scripts/windows/
  blender-run.ps1
  mcp-start.ps1
  toolchain-status.ps1
  unity-run.ps1

.github/workflows/
  toolchain-smoke.yml
  unity-hordax-validate.yml

docs/
  SELF_HOSTED_RUNNER.md
```

## MCP local

Requer Python 3.11+.

```powershell
.\scripts\windows\mcp-start.ps1
```

Na primeira execução o script cria `.venv` e instala o pacote em modo editável.

Instalação manual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m mcp_blender_unity.server
```

Variáveis opcionais:

- `BLENDER_EXE`
- `UNITY_EXE`
- `DEFAULT_UNITY_PROJECT`

## Tools MCP

- `toolchain_status`
- `blender_version`
- `blender_run_python`
- `unity_compile_project`
- `unity_validate_project`
- `unity_run_method`

`unity_compile_project` abre/importa o projeto em batch mode e inspeciona o log por erros de compilação.

`unity_validate_project` também executa, por padrão:

`HORDAX.EditorTools.CiValidation.Run`

## CLI direto

Unity:

```powershell
.\scripts\windows\unity-run.ps1 `
  -ProjectPath "C:\dev\HORDAX-game" `
  -ExecuteMethod "HORDAX.EditorTools.CiValidation.Run"
```

Somente compilação/import:

```powershell
.\scripts\windows\unity-run.ps1 -ProjectPath "C:\dev\HORDAX-game"
```

Blender:

```powershell
.\scripts\windows\blender-run.ps1 -PythonScript "C:\dev\scripts\generate_asset.py"
```

## GitHub self-hosted runner

Veja `docs/SELF_HOSTED_RUNNER.md`.

O workflow **Validate HORDAX in Unity** faz checkout do HORDAX em diretório isolado, roda o Unity em batch mode e publica o log como artifact.

Os workflows são manuais por segurança.

## Segurança

Não versione tokens, segredos ou dados de licença. Use variáveis de ambiente locais e GitHub Secrets quando necessário.
