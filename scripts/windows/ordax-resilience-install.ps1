param(
    [string]$RunnerPath = ""
)

$ErrorActionPreference = "Stop"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this installer from an elevated PowerShell. Administrator privileges are required only to install/harden the GitHub Actions runner service."
    }
}

Assert-Administrator

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$agentInstaller = Join-Path $repoRoot "scripts\windows\ordax-agent-install.ps1"
$runnerInstaller = Join-Path $repoRoot "scripts\windows\ordax-runner-service.ps1"

if (-not (Test-Path $agentInstaller)) { throw "Missing agent installer: $agentInstaller" }
if (-not (Test-Path $runnerInstaller)) { throw "Missing runner service installer: $runnerInstaller" }

Write-Host "=== OrdaX resilience bootstrap ==="
Write-Host "Repository: $repoRoot"
Write-Host ""

Write-Host "[1/3] Installing/updating persistent interactive OrdaX task..."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $agentInstaller -StartNow
if ($LASTEXITCODE -ne 0) {
    throw "OrdaX agent scheduled-task installation failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "[2/3] Installing/hardening GitHub self-hosted runner service..."
$runnerArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $runnerInstaller
)
if ($RunnerPath) {
    $runnerArgs += @("-RunnerPath", $RunnerPath)
}
& powershell.exe @runnerArgs
if ($LASTEXITCODE -ne 0) {
    throw "GitHub Actions runner service setup failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "[3/3] Verifying both independent recovery channels..."

$taskName = "OrdaX Dev Agent"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
$taskInfo = Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction Stop

$runner = Get-CimInstance Win32_Service |
    Where-Object { $_.Name -like "actions.runner.*" } |
    Select-Object -First 1
if (-not $runner) {
    throw "GitHub Actions runner service was not found after installation."
}

$agentStatus = $null
$deadline = [DateTime]::UtcNow.AddSeconds(45)
while ([DateTime]::UtcNow -lt $deadline) {
    try {
        $agentStatus = Invoke-RestMethod -Uri "http://127.0.0.1:8765/status" -TimeoutSec 2
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

Write-Host ""
Write-Host "OrdaX scheduled task:"
Write-Host ("  State: " + $task.State)
Write-Host ("  LastTaskResult: " + $taskInfo.LastTaskResult)
Write-Host ("  NextRunTime: " + $taskInfo.NextRunTime)

Write-Host "GitHub Actions runner service:"
Write-Host ("  Name: " + $runner.Name)
Write-Host ("  State: " + $runner.State)
Write-Host ("  StartMode: " + $runner.StartMode)

if ($agentStatus) {
    Write-Host "OrdaX local health endpoint: ONLINE"
    if ($agentStatus.agent_version) {
        Write-Host ("  Agent version: " + $agentStatus.agent_version)
    }
} else {
    Write-Warning "The scheduled task is installed but the local OrdaX health endpoint did not answer within 45 seconds."
    Write-Warning "The task/launcher restart policy will keep retrying; inspect scripts/windows/ordax-resilience-status.ps1 if it remains offline."
}

if ($runner.State -ne "Running" -or $runner.StartMode -ne "Auto") {
    throw "Runner service is not healthy after setup."
}

Write-Host ""
Write-Host "Resilience bootstrap completed."
Write-Host "Recovery channel A: Windows Task Scheduler -> OrdaX interactive agent"
Write-Host "Recovery channel B: Windows Service Control Manager -> GitHub Actions runner"
Write-Host "Each channel can recover the other without arbitrary remote shell access."
