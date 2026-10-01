param(
    [string]$RepoRoot = "",
    [string]$TaskName = "ORDAX Dev Web Bridge",
    [switch]$StartNow,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
Import-Module ScheduledTasks -ErrorAction Stop

if ($Uninstall) {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    [pscustomobject]@{
        task_name = $TaskName
        installed = $false
        removed = [bool]$existing
    } | ConvertTo-Json -Compress
    exit 0
}

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$RepoRoot = (Resolve-Path $RepoRoot).Path

$PythonwCandidates = @(
    (Join-Path $RepoRoot "runtime\pythonw.exe"),
    (Join-Path $RepoRoot ".venv\Scripts\pythonw.exe"),
    (Join-Path $env:LOCALAPPDATA "OrdaX\DevAgent\src\.venv\Scripts\pythonw.exe")
)
$Pythonw = $null
foreach ($candidate in $PythonwCandidates) {
    if (Test-Path $candidate) {
        $Pythonw = (Resolve-Path $candidate).Path
        break
    }
}
if (-not $Pythonw) {
    $command = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($command) { $Pythonw = $command.Source }
}
if (-not $Pythonw) {
    throw "ORDAX Web Bridge runtime missing: pythonw.exe was not found"
}

$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
if (-not $CurrentUser) {
    throw "Could not resolve the current Windows user"
}

$Action = New-ScheduledTaskAction -Execute $Pythonw -Argument "-m ordax_chat_app.web_bridge_daemon" -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $CurrentUser
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
$Principal = New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType Interactive -RunLevel Limited
$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "ORDAX Dev Secure MCP Web Bridge supervisor"

Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force | Out-Null

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
}

$Installed = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
[pscustomobject]@{
    task_name = $TaskName
    installed = $true
    state = [string]$Installed.State
    user = $CurrentUser
    executable = $Pythonw
    repo_root = $RepoRoot
    starts_at_logon = $true
    start_now = [bool]$StartNow
} | ConvertTo-Json -Compress
