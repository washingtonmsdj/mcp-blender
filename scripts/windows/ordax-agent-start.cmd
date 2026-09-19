@echo off
setlocal
set "ROOT=%~dp0\..\.."
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo OrdaX Dev Agent: .venv nao encontrado.
  echo Execute scripts\windows\ordax-agent-install.ps1 uma vez para preparar o ambiente.
  exit /b 2
)

cd /d "%ROOT%"

:run
"%PYTHON%" -m ordax_dev_agent.main
set "CODE=%ERRORLEVEL%"

if "%CODE%"=="42" (
  echo OrdaX Dev Agent atualizado. Reiniciando...
  timeout /t 2 >nul
  goto :run
)

exit /b %CODE%
