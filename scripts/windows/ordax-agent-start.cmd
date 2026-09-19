@echo off
setlocal
set "ROOT=%~dp0\..\.."
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "BRANCH=feat/ordax-dev-agent"

if not exist "%PYTHON%" (
  echo OrdaX Dev Agent: .venv nao encontrado.
  echo Execute scripts\windows\ordax-agent-install.ps1 uma vez para preparar o ambiente.
  exit /b 2
)

cd /d "%ROOT%"

:run
call :safe_update

"%PYTHON%" -m ordax_dev_agent.main
set "CODE=%ERRORLEVEL%"

if "%CODE%"=="42" (
  echo OrdaX Dev Agent atualizado. Reiniciando...
  timeout /t 2 >nul
  goto :run
)

if not "%CODE%"=="0" (
  echo OrdaX Dev Agent encerrou com codigo %CODE%.
  echo Nova tentativa em 10 segundos; uma correcao remota podera recuperar o agente.
  timeout /t 10 >nul
  goto :run
)

exit /b 0

:safe_update
for /f "delims=" %%S in ('git status --porcelain --untracked-files=no 2^>nul') do (
  echo OrdaX Dev Agent: alteracoes locais rastreadas; auto-update ignorado.
  goto :eof
)

git fetch --quiet origin "%BRANCH%" 2>nul
if errorlevel 1 (
  echo OrdaX Dev Agent: remoto indisponivel; iniciando codigo local.
  goto :eof
)

git merge --ff-only --quiet "origin/%BRANCH%" 2>nul
if errorlevel 1 (
  echo OrdaX Dev Agent: fast-forward indisponivel; iniciando codigo local sem sobrescrever alteracoes.
)
goto :eof
