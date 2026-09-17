param(
    [switch]$Reinstall
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$venv = Join-Path $repoRoot ".venv"
$python = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Creating virtual environment..."
    python -m venv $venv
}

if ($Reinstall) {
    & $python -m pip install --upgrade pip
    & $python -m pip install -e $repoRoot --upgrade
}
else {
    & $python -c "import mcp_blender_unity" 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $python -m pip install -e $repoRoot
    }
}

& $python -m mcp_blender_unity.server
exit $LASTEXITCODE
