param(
    [Parameter(Mandatory = $true)]
    [int]$AgentPid,
    [int]$StartupGraceSeconds = 60,
    [int]$ProbeIntervalSeconds = 10,
    [int]$MaxConsecutiveFailures = 6,
    [int]$MaxBusyMinutes = 15,
    [string]$RestartTaskName = "OrdaX Dev Agent",
    [int]$RestartDelaySeconds = 5
)

$ErrorActionPreference = "SilentlyContinue"
$healthUrl = "http://127.0.0.1:8765/status"
$stateDir = Join-Path $env:LOCALAPPDATA "OrdaX\DevAgent"
$logPath = Join-Path $stateDir "watchdog.log"
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

function Write-WatchdogLog([string]$Message) {
    $stamp = [DateTime]::UtcNow.ToString("o")
    Add-Content -Path $logPath -Value "$stamp $Message" -Encoding UTF8
}

function Stop-AgentTree([string]$Reason) {
    Write-WatchdogLog "RECOVERY $Reason pid=$AgentPid"
    & taskkill.exe /PID $AgentPid /T /F | Out-Null
}

function Request-AgentRestartIfNeeded {
    Start-Sleep -Seconds $RestartDelaySeconds

    $successor = Get-CimInstance Win32_Process |
        Where-Object {
            $_.ProcessId -ne $AgentPid -and
            $_.CommandLine -and
            $_.CommandLine -like "*ordax_dev_agent.main*" -and
            $_.CommandLine -like "*OrdaX*DevAgent*"
        } |
        Select-Object -First 1

    if ($successor) {
        Write-WatchdogLog "SUCCESSOR pid=$($successor.ProcessId); scheduled restart not needed"
        return
    }

    $task = Get-ScheduledTask -TaskName $RestartTaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-WatchdogLog "RESTART_SKIP scheduled task missing name=$RestartTaskName"
        return
    }
    if ($task.State -eq "Disabled") {
        Write-WatchdogLog "RESTART_SKIP scheduled task disabled name=$RestartTaskName"
        return
    }
    if ($task.State -eq "Running") {
        Write-WatchdogLog "RESTART_SKIP scheduled task already running name=$RestartTaskName"
        return
    }

    try {
        Start-ScheduledTask -TaskName $RestartTaskName -ErrorAction Stop
        Write-WatchdogLog "RESTART_REQUEST task=$RestartTaskName"
    } catch {
        Write-WatchdogLog "RESTART_FAIL task=$RestartTaskName error=$($_.Exception.Message)"
    }
}

Write-WatchdogLog "START pid=$AgentPid grace=$StartupGraceSeconds interval=$ProbeIntervalSeconds maxBusyMinutes=$MaxBusyMinutes restartTask=$RestartTaskName"

Start-Sleep -Seconds $StartupGraceSeconds

$consecutiveFailures = 0
$busyJobId = ""
$busySince = $null

while ($true) {
    $process = Get-Process -Id $AgentPid -ErrorAction SilentlyContinue
    if (-not $process) {
        Write-WatchdogLog "EXIT parent process ended pid=$AgentPid"
        Request-AgentRestartIfNeeded
        exit 0
    }

    $status = $null
    try {
        $status = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3
    } catch {
        $consecutiveFailures += 1
        Write-WatchdogLog "HEALTH_FAIL count=$consecutiveFailures pid=$AgentPid"
        if ($consecutiveFailures -ge $MaxConsecutiveFailures) {
            Stop-AgentTree "local health endpoint failed $consecutiveFailures consecutive probes"
            exit 20
        }
        Start-Sleep -Seconds $ProbeIntervalSeconds
        continue
    }

    $consecutiveFailures = 0
    $runtime = $status.runtime
    $runtimeState = if ($runtime) { [string]$runtime.state } else { "" }
    $currentJob = if ($runtime) { [string]$runtime.last_job_id } else { "" }

    if ($runtimeState -eq "busy" -and $currentJob) {
        if ($currentJob -ne $busyJobId) {
            $busyJobId = $currentJob
            $busySince = [DateTime]::UtcNow
            Write-WatchdogLog "BUSY_START job=$busyJobId pid=$AgentPid"
        } elseif ($busySince) {
            $busyAge = [DateTime]::UtcNow - $busySince
            if ($busyAge.TotalMinutes -ge $MaxBusyMinutes) {
                Stop-AgentTree ("job $busyJobId remained busy for " + [Math]::Round($busyAge.TotalMinutes, 1) + " minutes")
                exit 21
            }
        }
    } else {
        if ($busyJobId) {
            Write-WatchdogLog "BUSY_END job=$busyJobId state=$runtimeState"
        }
        $busyJobId = ""
        $busySince = $null
    }

    Start-Sleep -Seconds $ProbeIntervalSeconds
}
