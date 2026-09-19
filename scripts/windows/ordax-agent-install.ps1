param(
    [string]$SupabaseUrl = "",
    [string]$PublishableKey = "",
    [string]$PairingCode = "",
    [string]$AgentName = "TONECOS-HORDAX",
    [switch]$StartNow
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$startup = [Environment]::GetFolderPath("Startup")
$linkPath = Join-Path $startup "OrdaX Dev Agent.lnk"
$launcher = Join-Path $repoRoot "scripts\windows\ordax-agent-start.cmd"
$stateDir = Join-Path $env:LOCALAPPDATA "OrdaX\DevAgent"
$settingsPath = Join-Path $stateDir "agent-settings.json"
$pairingPath = Join-Path $stateDir "pairing-code.txt"

if (-not (Test-Path $python)) {
    $basePython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $basePython) {
        throw "Python not found."
    }

    & $basePython.Source -m venv (Join-Path $repoRoot ".venv")
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create .venv."
    }
}

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }

& $python -m pip install -e $repoRoot
if ($LASTEXITCODE -ne 0) { throw "OrdaX Dev Agent install failed." }

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

if ($SupabaseUrl -and $PublishableKey) {
    $settings = [ordered]@{
        agent_name = $AgentName
        supabase_url = $SupabaseUrl
        publishable_key = $PublishableKey
        poll_seconds = 5
        hordax_path = "C:\Users\TONECOS\Documents\github\HORDAX-game"
        bridge_path = $repoRoot
    }

    $settings | ConvertTo-Json | Set-Content -Path $settingsPath -Encoding UTF8
}

if ($PairingCode) {
    Set-Content -Path $pairingPath -Value $PairingCode -Encoding ASCII
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($linkPath)
$shortcut.TargetPath = $launcher
$shortcut.WorkingDirectory = $repoRoot
$shortcut.Description = "OrdaX Dev Agent - Unity, Blender, Git and diagnostics"
$shortcut.WindowStyle = 7
$shortcut.Save()

Write-Host "OrdaX Dev Agent installed."
Write-Host "Startup shortcut: $linkPath"
Write-Host "Local status endpoint: http://127.0.0.1:8765/status"

if ($SupabaseUrl -and $PublishableKey) {
    Write-Host "Supabase control plane configured."
} else {
    Write-Host "Supabase control plane not configured."
}

if ($PairingCode) {
    Write-Host "One-time pairing code installed."
}

if ($StartNow) {
    Start-Process -FilePath $launcher -WorkingDirectory $repoRoot -WindowStyle Minimized
}
