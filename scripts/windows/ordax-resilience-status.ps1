$ErrorActionPreference = "Continue"

$taskName = "OrdaX Dev Agent"
$bootstrapPath = Join-Path $env:LOCALAPPDATA "OrdaX\DevAgent\bootstrap\ordax-agent-bootstrap.ps1"
$bootstrapPolicyPath = Join-Path $env:LOCALAPPDATA "OrdaX\DevAgent\bootstrap\update_policy.py"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
$taskInfo = if ($task) { Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction SilentlyContinue } else { $null }

$runner = Get-CimInstance Win32_Service |
    Where-Object { $_.Name -like "actions.runner.*" } |
    Select-Object -First 1

$agentProcess = Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine -like "*ordax_dev_agent.main*"
    } |
    Select-Object ProcessId,Name,CommandLine

$agentStatus = $null
try {
    $agentStatus = Invoke-RestMethod -Uri "http://127.0.0.1:8765/status" -TimeoutSec 2
} catch {}

$result = [ordered]@{
    timestamp_utc = [DateTime]::UtcNow.ToString("o")
    scheduled_task = if ($task) {
        [ordered]@{
            exists = $true
            state = [string]$task.State
            last_run_time = if ($taskInfo) { $taskInfo.LastRunTime } else { $null }
            last_task_result = if ($taskInfo) { $taskInfo.LastTaskResult } else { $null }
            next_run_time = if ($taskInfo) { $taskInfo.NextRunTime } else { $null }
            actions = @(
                $task.Actions | ForEach-Object {
                    [ordered]@{
                        execute = $_.Execute
                        arguments = $_.Arguments
                        working_directory = $_.WorkingDirectory
                    }
                }
            )
        }
    } else {
        [ordered]@{ exists = $false }
    }
    agent_processes = @($agentProcess)
    external_bootstrap = [ordered]@{
        script_exists = Test-Path $bootstrapPath
        policy_exists = Test-Path $bootstrapPolicyPath
        script_path = $bootstrapPath
        policy_path = $bootstrapPolicyPath
    }
    local_health = if ($agentStatus) { $agentStatus } else { $null }
    github_runner_service = if ($runner) {
        [ordered]@{
            exists = $true
            name = $runner.Name
            state = $runner.State
            start_mode = $runner.StartMode
            start_name = $runner.StartName
            path_name = $runner.PathName
        }
    } else {
        [ordered]@{ exists = $false }
    }
}

$result | ConvertTo-Json -Depth 8
