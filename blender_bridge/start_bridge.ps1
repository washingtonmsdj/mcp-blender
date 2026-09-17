param(
    [switch]$AllowSceneChanges,
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 9876
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$currentBranch = (git branch --show-current).Trim()
if ($currentBranch -ne "blender-bridge") {
    Write-Host "Branch atual: $currentBranch" -ForegroundColor Yellow
    Write-Host "Trocando para blender-bridge..."
    git fetch origin
    git checkout blender-bridge
}

$env:BLENDER_HOST = $HostAddress
$env:BLENDER_PORT = "$Port"
$env:BLENDER_BRIDGE_BRANCH = "blender-bridge"
$env:BLENDER_BRIDGE_POLL_SECONDS = "3"
$env:BLENDER_BRIDGE_ALLOW_CODE = if ($AllowSceneChanges) { "1" } else { "0" }

Write-Host ""
Write-Host "OpenAI Blender Bridge" -ForegroundColor Cyan
Write-Host "Blender: $HostAddress`:$Port"
Write-Host "Alteracoes na cena: $AllowSceneChanges"
Write-Host ""

python blender_bridge/relay.py
