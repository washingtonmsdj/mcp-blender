@echo off
setlocal
set "ROOT=%~dp0\..\.."
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo OrdaX Dev Agent: .venv nao encontrado.
  echo Execute scripts\windows\mcp-start.ps1 uma vez para preparar o ambiente.
  exit /b 2
)

cd /d "%ROOT%"
"%PYTHON%" -m ordax_dev_agent.main
exit /b %ERRORLEVEL%
