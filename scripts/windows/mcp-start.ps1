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

$needsInstall = $Reinstall

if (-not $needsInstall) {
    & $python -c "from mcp.server.fastmcp import FastMCP; import mcp_blender_unity; print('MCP bridge dependencies OK')" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $needsInstall = $true
    }
}

if ($needsInstall) {
    Write-Host "Installing compatible MCP bridge dependencies..."
    & $python -m pip install --upgrade pip
    & $python -m pip install -e $repoRoot --upgrade

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install MCP bridge dependencies."
    }

    & $python -c "from mcp.server.fastmcp import FastMCP; import mcp_blender_unity; print('MCP bridge dependencies OK')"
    if ($LASTEXITCODE -ne 0) {
        throw "MCP bridge dependency validation failed after installation."
    }
}

Write-Host "Starting MCP Blender + Unity bridge..."
& $python -m mcp_blender_unity.server
exit $LASTEXITCODE
