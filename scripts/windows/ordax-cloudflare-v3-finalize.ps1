param(
    [ValidateRange(10, 300)]
    [int]$HeartbeatMaxAgeSeconds = 45,
    [ValidateRange(10, 300)]
    [int]$MinimumBootAdvanceSeconds = 30
)

$ErrorActionPreference = 'Stop'
$stateDir = Join-Path $env:LOCALAPPDATA 'OrdaX\DevAgent'
$cutoverStatePath = Join-Path $stateDir 'cloudflare-v3-cutover.json'
$statusUrl = 'http://127.0.0.1:8765/status'
$mutex = New-Object System.Threading.Mutex($false, 'Local\OrdaXDeviceSetup')
$locked = $false

function Get-WindowsBootEpochMilliseconds {
    return [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() - [Environment]::TickCount64
}

function Get-HeartbeatAgeSeconds($Status) {
    if (-not $Status -or -not $Status.runtime -or -not $Status.runtime.last_heartbeat_at) {
        return [double]::PositiveInfinity
    }
    return [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - [double]$Status.runtime.last_heartbeat_at
}

if (-not $mutex.WaitOne(0)) {
    throw 'DEVICE_SETUP_OR_CUTOVER_ALREADY_RUNNING'
}
$locked = $true

try {
    if (-not (Test-Path $cutoverStatePath -PathType Leaf)) {
        throw 'NO_PENDING_CLOUDFLARE_V3_CUTOVER_PROOF'
    }

    $cutover = Get-Content $cutoverStatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $cutover -or [string]$cutover.status -ne 'awaiting-reboot-proof') {
        throw 'CLOUDFLARE_V3_CUTOVER_NOT_READY_FOR_FINAL_PROOF'
    }

    $previousBoot = [double]$cutover.source_windows_boot_epoch_ms
    $currentBoot = [double](Get-WindowsBootEpochMilliseconds)
    $requiredAdvance = [double]$MinimumBootAdvanceSeconds * 1000
    if (
        $previousBoot -le 0 -or
        $currentBoot -le ($previousBoot + $requiredAdvance)
    ) {
        throw 'REAL_WINDOWS_REBOOT_REQUIRED'
    }

    try {
        $status = Invoke-RestMethod -Uri $statusUrl -TimeoutSec 4
    } catch {
        throw 'LOCAL_AGENT_STATUS_UNAVAILABLE_AFTER_REBOOT'
    }

    if ([string]$status.control_plane_protocol -ne 'cloudflare-v3') {
        throw 'CLOUDFLARE_V3_NOT_ACTIVE_AFTER_REBOOT'
    }
    if ([string]$status.development_device_id -ne [string]$cutover.target_device_id) {
        throw 'CLOUDFLARE_V3_DEVICE_CHANGED_AFTER_REBOOT'
    }

    $activeUrl = if ($status.control_plane_url) {
        ([string]$status.control_plane_url).TrimEnd('/')
    } else {
        ''
    }
    $expectedUrl = ([string]$cutover.target_url).TrimEnd('/')
    if ($activeUrl -ne $expectedUrl) {
        throw 'CLOUDFLARE_V3_URL_CHANGED_AFTER_REBOOT'
    }

    $heartbeatAge = Get-HeartbeatAgeSeconds $status
    if ($heartbeatAge -ge $HeartbeatMaxAgeSeconds) {
        throw 'CLOUDFLARE_V3_HEARTBEAT_STALE_AFTER_REBOOT'
    }

    if (-not $status.runtime -or [int]$status.runtime.jobs_completed -lt 1) {
        throw 'REMOTE_JOB_REQUIRED_AFTER_REBOOT'
    }
    $lastAction = [string]$status.runtime.last_job_action
    if (-not $lastAction.StartsWith('blender.')) {
        throw 'REMOTE_BLENDER_JOB_REQUIRED_AFTER_REBOOT'
    }
    if (
        -not $status.runtime.last_result -or
        $status.runtime.last_result.ok -ne $true
    ) {
        throw 'REMOTE_BLENDER_JOB_MUST_SUCCEED_AFTER_REBOOT'
    }

    $backupPath = [string]$cutover.backup_path
    if ($backupPath) {
        Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $cutoverStatePath -Force

    Write-Output 'ORDAX_CLOUDFLARE_V3_REBOOT_PROOF=PASS'
    Write-Output "CONTROL_PLANE_URL=$expectedUrl"
    Write-Output "DEVICE_ID=$($cutover.target_device_id)"
    Write-Output "BLENDER_JOB=$lastAction"
    Write-Output 'SUPABASE_ROLLBACK_SNAPSHOT=RELEASED'
} finally {
    if ($locked) {
        $mutex.ReleaseMutex()
        $mutex.Dispose()
    }
}
