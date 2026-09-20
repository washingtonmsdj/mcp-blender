@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0\..\.."
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "BRANCH=main"
set /a RETRY_SECONDS=10
set "SKIP_SAFE_UPDATE=0"

if not exist "%PYTHON%" (
  echo OrdaX Dev Agent: .venv nao encontrado.
  echo Execute scripts\windows\ordax-agent-install.ps1 uma vez para preparar o ambiente.
  exit /b 2
)

cd /d "%ROOT%"

:run
if "%SKIP_SAFE_UPDATE%"=="0" (
  call :safe_update
"%PYTHON%" -m ordax_dev_agent.update_policy --check-clean "%ROOT%" >nul 2>nul
if errorlevel 2 (
  echo OrdaX Dev Agent: falha ao verificar alteracoes locais; iniciando codigo local.
  goto :eof
)
if errorlevel 1 (
  echo OrdaX Dev Agent: alteracoes locais rastreadas; auto-update ignorado.
  goto :eof
)

for /f "delims=" %%H in ('git -c core.fsmonitor=false rev-parse HEAD 2^>nul') do set "PREV_SHA=%%H"
if not defined PREV_SHA (
  echo OrdaX Dev Agent: nao foi possivel ler o commit atual; iniciando codigo local.
  goto :eof
)

git -c core.fsmonitor=false fetch --quiet origin "%BRANCH%" 2>nul
if errorlevel 1 (
  echo OrdaX Dev Agent: remoto indisponivel; iniciando codigo local.
  goto :eof
)

git -c core.fsmonitor=false merge --ff-only --quiet "origin/%BRANCH%" 2>nul
if errorlevel 1 (
  echo OrdaX Dev Agent: fast-forward indisponivel; iniciando codigo local sem sobrescrever alteracoes.
  goto :eof
)

"%PYTHON%" -m compileall -q "%ROOT%\mcp_blender_unity" "%ROOT%\ordax_dev_agent"
if errorlevel 1 (
  echo OrdaX Dev Agent: update remoto falhou no compile gate. Restaurando !PREV_SHA!.
  git reset --hard "!PREV_SHA!" >nul 2>nul
  if errorlevel 1 (
    echo OrdaX Dev Agent: falha ao restaurar commit anterior.
    exit /b 3
  )
)
goto :eof
