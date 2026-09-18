param(
    [string]$ProjectPath = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$script = Join-Path $repoRoot "scripts\mcp_smoke.py"

if (-not (Test-Path $python)) {
    throw ".venv Python not found. Run .\scripts\windows\mcp-start.ps1 first."
}

$scriptArgs = @()
if ($ProjectPath) { $scriptArgs += $ProjectPath }
& $python $script @scriptArgs
exit $LASTEXITCODE
