param(
    [string]$SupabaseUrl = "",
    [string]$PublishableKey = "",
    [string]$PairingCode = "",
    [string]$AgentName = "TONECOS-HORDAX",
    [string]$HordaxPath = "C:\Users\TONECOS\Documents\github\HORDAX-game",
    [string]$BridgePath = "",
    [switch]$StartNow
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$startup = [Environment]::GetFolderPath("Startup")
$legacyLinkPath = Join-Path $startup "OrdaX Dev Agent.lnk"
$taskName = "OrdaX Dev Agent"
$launcher = Join-Path $repoRoot "scripts\windows\ordax-agent-start.cmd"
$stateDir = Join-Path $env:LOCALAPPDATA "OrdaX\DevAgent"
$settingsPath = Join-Path $stateDir "agent-settings.json"
$pairingPath = Join-Path $stateDir "pairing-code.txt"

if (-not $BridgePath) {
    $BridgePath = $repoRoot
}

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
        hordax_path = $HordaxPath
        bridge_path = $BridgePath
    }

    $settingsJson = $settings | ConvertTo-Json
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($settingsPath, $settingsJson, $utf8NoBom)
}

if ($PairingCode) {
    Set-Content -Path $pairingPath -Value $PairingCode -Encoding ASCII
}

if (Test-Path $legacyLinkPath) {
    Remove-Item -Force $legacyLinkPath
}

Import-Module ScheduledTasks -ErrorAction Stop

$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$actionParams = @{
    Execute = $env:ComSpec
    Argument = ('/d /c "' + $launcher + '"')
    WorkingDirectory = $repoRoot
}
$action = New-ScheduledTaskAction @actionParams
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId

$settingsParams = @{
    MultipleInstances = "IgnoreNew"
    RestartCount = 999
    RestartInterval = (New-TimeSpan -Minutes 1)
    StartWhenAvailable = $true
    AllowStartIfOnBatteries = $true
    DontStopIfGoingOnBatteries = $true
    ExecutionTimeLimit = [TimeSpan]::Zero
}
$settings = New-ScheduledTaskSettingsSet @settingsParams
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "OrdaX Dev Agent - persistent interactive Unity/Blender control plane"
Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null

Write-Host "OrdaX Dev Agent installed."
Write-Host "Scheduled task: $taskName"
Write-Host "Run context: $userId (interactive desktop)"
Write-Host "Restart policy: 999 attempts, 1 minute interval"
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
    Start-ScheduledTask -TaskName $taskName
}
