param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string]$ControlPlaneUrl,
    [switch]$NonInteractive,
    [ValidateRange(20, 600)]
    [int]$ReadyTimeoutSeconds = 120,
    [ValidateRange(20, 600)]
    [int]$RollbackTimeoutSeconds = 90
)

$ErrorActionPreference = 'Stop'
$ControlPlaneUrl = $ControlPlaneUrl.TrimEnd('/')
$stateDir = Join-Path $env:LOCALAPPDATA 'OrdaX\DevAgent'
$repo = Join-Path $stateDir 'src'
$python = Join-Path $repo '.venv\Scripts\python.exe'
$settingsPath = Join-Path $stateDir 'agent-settings.json'
$backupPath = Join-Path $stateDir 'agent-settings.pre-cloudflare-v3.json'
$cutoverStatePath = Join-Path $stateDir 'cloudflare-v3-cutover.json'
$taskName = 'OrdaX Dev Agent'
$statusUrl = 'http://127.0.0.1:8765/status'
$mutex = New-Object System.Threading.Mutex($false, 'Local\OrdaXDeviceSetup')
$locked = $false
$cutoverCommitted = $false

function Write-AtomicText([string]$Path, [string]$Text) {
    $temp = "$Path.next"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($temp, $Text, $utf8NoBom)
    Move-Item -LiteralPath $temp -Destination $Path -Force
}

function Write-AtomicJson([string]$Path, $Value) {
    Write-AtomicText -Path $Path -Text ($Value | ConvertTo-Json -Depth 20)
}

function Get-AgentStatus {
    try {
        return Invoke-RestMethod -Uri $statusUrl -TimeoutSec 3
    } catch {
        return $null
    }
}

function Get-WindowsBootEpochMilliseconds {
    return [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() - [Environment]::TickCount64
}

function Get-HeartbeatAgeSeconds($Status) {
    if (-not $Status -or -not $Status.runtime -or -not $Status.runtime.last_heartbeat_at) {
        return [double]::PositiveInfinity
    }
    return [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - [double]$Status.runtime.last_heartbeat_at
}

function Test-LocalAgentUsable($Status) {
    if (-not $Status -or -not $Status.runtime) { return $false }
    if ($Status.runtime.state -eq 'busy') { return $false }
    if ($Status.runtime.state -eq 'stopping') { return $false }
    return $true
}

function Get-AgentPid($Status) {
    if ($Status -and $Status.runtime -and $Status.runtime.pid) {
        return [int]$Status.runtime.pid
    }
    return 0
}

function Restart-ManagedAgent([int]$OldPid) {
    $null = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
    Disable-ScheduledTask -TaskName $taskName | Out-Null
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

    if ($OldPid -gt 0) {
        Start-Sleep -Milliseconds 750
        $process = Get-Process -Id $OldPid -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $OldPid -Force -ErrorAction Stop
        }
    }

    Start-Sleep -Seconds 2
    Enable-ScheduledTask -TaskName $taskName | Out-Null
    Start-ScheduledTask -TaskName $taskName
}

function Wait-AgentProvider(
    [string]$Protocol,
    [string]$DeviceId,
    [string]$ExpectedUrl,
    [int]$PreviousPid,
    [int]$TimeoutSeconds,
    [switch]$RequireRemoteHeartbeat
) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $status = Get-AgentStatus
        if ($status) {
            $pid = Get-AgentPid $status
            $pidChanged = $PreviousPid -le 0 -or ($pid -gt 0 -and $pid -ne $PreviousPid)
            $protocolMatches = [string]$status.control_plane_protocol -eq $Protocol
            $deviceMatches = [string]$status.development_device_id -eq $DeviceId
            $urlMatches = $true
            if ($Protocol -eq 'cloudflare-v3') {
                $configured = if ($status.control_plane_url) {
                    ([string]$status.control_plane_url).TrimEnd('/')
                } else {
                    ''
                }
                $urlMatches = $configured -eq $ExpectedUrl
            }
            $heartbeatFresh = (Get-HeartbeatAgeSeconds $status) -lt 45
            $runtimeState = if ($status.runtime) { [string]$status.runtime.state } else { '' }
            $runtimeUsable = $runtimeState -in @('ready', 'busy', 'control-plane-error')

            if (
                $pidChanged -and
                $protocolMatches -and
                $deviceMatches -and
                $urlMatches -and
                $runtimeUsable -and
                ((-not $RequireRemoteHeartbeat) -or $heartbeatFresh)
            ) {
                return $status
            }
        }
        Start-Sleep -Seconds 2
    }
    return $null
}

function Ensure-V2IdentityMetadata($Status) {
    if (-not (Test-Path $settingsPath -PathType Leaf)) {
        throw 'AGENT_SETTINGS_MISSING'
    }
    $settings = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $settings) { throw 'AGENT_SETTINGS_INVALID' }

    $v2DeviceId = [string]$Status.development_device_id
    $v2Url = if ($settings.supabase_url) { ([string]$settings.supabase_url).TrimEnd('/') } else { '' }
    if ($v2DeviceId -notmatch '^[0-9a-fA-F-]{36}$' -or -not $v2Url) {
        throw 'DEVELOPMENT_V2_IDENTITY_INCOMPLETE'
    }

    if (-not $settings.PSObject.Properties['control_plane_identities'] -or -not $settings.control_plane_identities) {
        $settings | Add-Member -NotePropertyName control_plane_identities -NotePropertyValue ([pscustomobject]@{}) -Force
    }
    $identity = [pscustomobject]@{
        device_id = $v2DeviceId
        control_plane_url = $v2Url
    }
    $settings.control_plane_identities |
        Add-Member -NotePropertyName 'development-v2' -NotePropertyValue $identity -Force

    Write-AtomicJson -Path $settingsPath -Value $settings
    return $identity
}

function Restore-V2ActiveSettings {
    $settings = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (
        -not $settings -or
        -not $settings.control_plane_identities -or
        -not $settings.control_plane_identities.'development-v2'
    ) {
        throw 'ROLLBACK_V2_IDENTITY_MISSING'
    }

    $identity = $settings.control_plane_identities.'development-v2'
    $deviceId = [string]$identity.device_id
    $url = ([string]$identity.control_plane_url).TrimEnd('/')
    if ($deviceId -notmatch '^[0-9a-fA-F-]{36}$' -or -not $url) {
        throw 'ROLLBACK_V2_IDENTITY_INVALID'
    }

    $settings | Add-Member -NotePropertyName control_plane_protocol -NotePropertyValue 'development-v2' -Force
    $settings | Add-Member -NotePropertyName development_device_id -NotePropertyValue $deviceId -Force
    $settings | Add-Member -NotePropertyName supabase_url -NotePropertyValue $url -Force
    Write-AtomicJson -Path $settingsPath -Value $settings
    return $identity
}

if (-not $mutex.WaitOne(0)) {
    throw 'DEVICE_SETUP_OR_CUTOVER_ALREADY_RUNNING'
}
$locked = $true

try {
    if (-not (Test-Path $python -PathType Leaf)) { throw 'MANAGED_PYTHON_MISSING' }
    if (-not (Test-Path $settingsPath -PathType Leaf)) { throw 'AGENT_SETTINGS_MISSING' }
    if (-not (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue)) {
        throw 'AGENT_SCHEDULED_TASK_MISSING'
    }

    $initial = Get-AgentStatus
    if (-not (Test-LocalAgentUsable $initial)) {
        if ($initial -and $initial.runtime -and $initial.runtime.state -eq 'busy') {
            throw 'AGENT_BUSY_CUTOVER_REFUSED'
        }
        throw 'LOCAL_AGENT_HEALTH_REQUIRED'
    }

    if ([string]$initial.control_plane_protocol -eq 'cloudflare-v3') {
        $savedSettings = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $savedUrl = if ($savedSettings.control_plane_url) {
            ([string]$savedSettings.control_plane_url).TrimEnd('/')
        } else {
            ''
        }
        if ($savedUrl -ne $ControlPlaneUrl) {
            throw 'CLOUDFLARE_V3_ALREADY_ACTIVE_WITH_DIFFERENT_URL'
        }
        if ((Get-HeartbeatAgeSeconds $initial) -ge 45) {
            throw 'CLOUDFLARE_V3_ACTIVE_BUT_REMOTE_HEARTBEAT_STALE'
        }
        Write-Output 'ORDAX_CLOUDFLARE_V3_CUTOVER=ALREADY_ACTIVE'
        Write-Output "CONTROL_PLANE_URL=$ControlPlaneUrl"
        exit 0
    }

    if ([string]$initial.control_plane_protocol -ne 'development-v2') {
        throw 'CUTOVER_REQUIRES_DEVELOPMENT_V2_ACTIVE'
    }

    $migrateV2Token = 'from pathlib import Path; import sys; from ordax_dev_agent.device_credentials import resolve_token_path; p=resolve_token_path(Path(sys.argv[1]), "development-v2"); sys.exit(0 if p.is_file() else 2)'
    & $python -c $migrateV2Token $stateDir
    if ($LASTEXITCODE -ne 0) { throw 'DEVELOPMENT_V2_CREDENTIAL_MISSING' }

    $v2Identity = Ensure-V2IdentityMetadata $initial
    Copy-Item -LiteralPath $settingsPath -Destination $backupPath -Force

    $initialHeartbeatAge = Get-HeartbeatAgeSeconds $initial
    if ($initialHeartbeatAge -ge 45) {
        Write-Warning 'Supabase v2 remote heartbeat is stale; local agent is usable, so Cloudflare cutover will continue.'
    }

    $setupArgs = @(
        '-m', 'ordax_dev_agent.device_setup',
        '--protocol', 'cloudflare-v3',
        '--control-plane-url', $ControlPlaneUrl
    )
    if (-not $NonInteractive) { $setupArgs += '--interactive' }
    & $python @setupArgs
    if ($LASTEXITCODE -ne 0) {
        Copy-Item -LiteralPath $backupPath -Destination "$settingsPath.next" -Force
        Move-Item -LiteralPath "$settingsPath.next" -Destination $settingsPath -Force
        throw 'CLOUDFLARE_V3_ENROLLMENT_FAILED_V2_LEFT_ACTIVE'
    }

    $targetSettings = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $v3Identity = $targetSettings.control_plane_identities.'cloudflare-v3'
    if (-not $v3Identity) {
        Copy-Item -LiteralPath $backupPath -Destination "$settingsPath.next" -Force
        Move-Item -LiteralPath "$settingsPath.next" -Destination $settingsPath -Force
        throw 'CLOUDFLARE_V3_IDENTITY_NOT_PERSISTED_V2_RESTORED'
    }
    $v3DeviceId = [string]$v3Identity.device_id
    if ($v3DeviceId -notmatch '^[0-9a-fA-F-]{36}
    $cutoverState = [ordered]@{
        status = 'switching'
        started_at = [DateTime]::UtcNow.ToString('o')
        previous_protocol = 'development-v2'
        previous_device_id = [string]$v2Identity.device_id
        target_protocol = 'cloudflare-v3'
        target_device_id = $v3DeviceId
        target_url = $ControlPlaneUrl
        backup_path = $backupPath
        source_windows_boot_epoch_ms = Get-WindowsBootEpochMilliseconds
    }
    Write-AtomicJson -Path $cutoverStatePath -Value $cutoverState

    $oldPid = Get-AgentPid $initial
    Restart-ManagedAgent -OldPid $oldPid

    $verifyArgs = @{
        Protocol = 'cloudflare-v3'
        DeviceId = $v3DeviceId
        ExpectedUrl = $ControlPlaneUrl
        PreviousPid = $oldPid
        TimeoutSeconds = $ReadyTimeoutSeconds
        RequireRemoteHeartbeat = $true
    }
    $verified = Wait-AgentProvider @verifyArgs

    if ($verified) {
        $cutoverState.status = 'awaiting-reboot-proof'
        $cutoverState.verified_at = [DateTime]::UtcNow.ToString('o')
        $cutoverState.verified_agent_pid = Get-AgentPid $verified
        $cutoverState.verified_heartbeat_at = $verified.runtime.last_heartbeat_at
        Write-AtomicJson -Path $cutoverStatePath -Value $cutoverState

        Write-Output 'ORDAX_CLOUDFLARE_V3_CUTOVER=PASS'
        Write-Output "CONTROL_PLANE_URL=$ControlPlaneUrl"
        Write-Output "DEVICE_ID=$v3DeviceId"
        Write-Output 'ROLLBACK_SNAPSHOT=PRESERVED_UNTIL_REBOOT_PROOF'
        $cutoverCommitted = $true
        exit 0
    }

    Write-Warning 'Cloudflare v3 did not become remotely healthy in time; restoring development-v2.'
    $current = Get-AgentStatus
    $rollbackIdentity = Restore-V2ActiveSettings
    $rollbackOldPid = Get-AgentPid $current
    Restart-ManagedAgent -OldPid $rollbackOldPid

    $rollbackArgs = @{
        Protocol = 'development-v2'
        DeviceId = [string]$rollbackIdentity.device_id
        ExpectedUrl = [string]$rollbackIdentity.control_plane_url
        PreviousPid = $rollbackOldPid
        TimeoutSeconds = $RollbackTimeoutSeconds
    }
    $rolledBack = Wait-AgentProvider @rollbackArgs

    if (-not $rolledBack) {
        $cutoverState.status = 'rollback-failed'
        $cutoverState.rollback_failed_at = [DateTime]::UtcNow.ToString('o')
        Write-AtomicJson -Path $cutoverStatePath -Value $cutoverState
        throw 'CLOUDFLARE_V3_CUTOVER_AND_V2_ROLLBACK_FAILED'
    }

    $rollbackHeartbeatFresh = (Get-HeartbeatAgeSeconds $rolledBack) -lt 45
    Remove-Item -LiteralPath $cutoverStatePath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue

    Write-Output 'ORDAX_CLOUDFLARE_V3_CUTOVER=ROLLED_BACK'
    if ($rollbackHeartbeatFresh) {
        Write-Output 'V2_REMOTE_HEARTBEAT=FRESH'
    } else {
        Write-Output 'V2_REMOTE_HEARTBEAT=DEGRADED'
    }
    throw 'CLOUDFLARE_V3_CUTOVER_FAILED_V2_ROLLBACK_OK'
} catch {
    $originalError = $_
    if (-not $cutoverCommitted) {
        try {
            if (Test-Path $settingsPath -PathType Leaf) {
                $activeSettings = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
                if ($activeSettings -and [string]$activeSettings.control_plane_protocol -eq 'cloudflare-v3') {
                    Write-Warning 'Unexpected cutover error after v3 activation; attempting emergency v2 rollback.'
                    $emergencyIdentity = Restore-V2ActiveSettings
                    $emergencyStatus = Get-AgentStatus
                    $emergencyOldPid = Get-AgentPid $emergencyStatus
                    Restart-ManagedAgent -OldPid $emergencyOldPid
                    $emergencyArgs = @{
                        Protocol = 'development-v2'
                        DeviceId = [string]$emergencyIdentity.device_id
                        ExpectedUrl = [string]$emergencyIdentity.control_plane_url
                        PreviousPid = $emergencyOldPid
                        TimeoutSeconds = $RollbackTimeoutSeconds
                    }
                    $emergencyRollback = Wait-AgentProvider @emergencyArgs
                    if (-not $emergencyRollback) {
                        throw 'EMERGENCY_V2_ROLLBACK_FAILED'
                    }
                    Remove-Item -LiteralPath $cutoverStatePath -Force -ErrorAction SilentlyContinue
                    Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
                    Write-Warning 'Emergency v2 rollback completed.'
                }
            }
        } catch {
            throw "CLOUDFLARE_V3_CUTOVER_ERROR=$($originalError.Exception.Message); ROLLBACK_ERROR=$($_.Exception.Message)"
        }
    }
    throw $originalError
} finally {
    if ($locked) {
        $mutex.ReleaseMutex()
        $mutex.Dispose()
    }
}
) {
        Copy-Item -LiteralPath $backupPath -Destination "$settingsPath.next" -Force
        Move-Item -LiteralPath "$settingsPath.next" -Destination $settingsPath -Force
        throw 'CLOUDFLARE_V3_DEVICE_ID_INVALID_V2_RESTORED'
    }

    $cutoverState = [ordered]@{
        status = 'switching'
        started_at = [DateTime]::UtcNow.ToString('o')
        previous_protocol = 'development-v2'
        previous_device_id = [string]$v2Identity.device_id
        target_protocol = 'cloudflare-v3'
        target_device_id = $v3DeviceId
        target_url = $ControlPlaneUrl
        backup_path = $backupPath
    }
    Write-AtomicJson -Path $cutoverStatePath -Value $cutoverState

    $oldPid = Get-AgentPid $initial
    Restart-ManagedAgent -OldPid $oldPid

    $verifyArgs = @{
        Protocol = 'cloudflare-v3'
        DeviceId = $v3DeviceId
        ExpectedUrl = $ControlPlaneUrl
        PreviousPid = $oldPid
        TimeoutSeconds = $ReadyTimeoutSeconds
        RequireRemoteHeartbeat = $true
    }
    $verified = Wait-AgentProvider @verifyArgs

    if ($verified) {
        $cutoverState.status = 'awaiting-reboot-proof'
        $cutoverState.verified_at = [DateTime]::UtcNow.ToString('o')
        $cutoverState.verified_agent_pid = Get-AgentPid $verified
        $cutoverState.verified_heartbeat_at = $verified.runtime.last_heartbeat_at
        Write-AtomicJson -Path $cutoverStatePath -Value $cutoverState

        Write-Output 'ORDAX_CLOUDFLARE_V3_CUTOVER=PASS'
        Write-Output "CONTROL_PLANE_URL=$ControlPlaneUrl"
        Write-Output "DEVICE_ID=$v3DeviceId"
        Write-Output 'ROLLBACK_SNAPSHOT=PRESERVED_UNTIL_REBOOT_PROOF'
        exit 0
    }

    Write-Warning 'Cloudflare v3 did not become remotely healthy in time; restoring development-v2.'
    $current = Get-AgentStatus
    $rollbackIdentity = Restore-V2ActiveSettings
    $rollbackOldPid = Get-AgentPid $current
    Restart-ManagedAgent -OldPid $rollbackOldPid

    $rollbackArgs = @{
        Protocol = 'development-v2'
        DeviceId = [string]$rollbackIdentity.device_id
        ExpectedUrl = [string]$rollbackIdentity.control_plane_url
        PreviousPid = $rollbackOldPid
        TimeoutSeconds = $RollbackTimeoutSeconds
    }
    $rolledBack = Wait-AgentProvider @rollbackArgs

    if (-not $rolledBack) {
        $cutoverState.status = 'rollback-failed'
        $cutoverState.rollback_failed_at = [DateTime]::UtcNow.ToString('o')
        Write-AtomicJson -Path $cutoverStatePath -Value $cutoverState
        throw 'CLOUDFLARE_V3_CUTOVER_AND_V2_ROLLBACK_FAILED'
    }

    $rollbackHeartbeatFresh = (Get-HeartbeatAgeSeconds $rolledBack) -lt 45
    Remove-Item -LiteralPath $cutoverStatePath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue

    Write-Output 'ORDAX_CLOUDFLARE_V3_CUTOVER=ROLLED_BACK'
    if ($rollbackHeartbeatFresh) {
        Write-Output 'V2_REMOTE_HEARTBEAT=FRESH'
    } else {
        Write-Output 'V2_REMOTE_HEARTBEAT=DEGRADED'
    }
    throw 'CLOUDFLARE_V3_CUTOVER_FAILED_V2_ROLLBACK_OK'
} finally {
    if ($locked) {
        $mutex.ReleaseMutex()
        $mutex.Dispose()
    }
}
