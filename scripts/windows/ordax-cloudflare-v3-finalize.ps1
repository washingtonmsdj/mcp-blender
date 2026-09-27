param(
    [ValidateRange(10, 300)]
    [int]$HeartbeatMaxAgeSeconds = 45,
    [ValidateRange(10, 300)]
    [int]$MinimumBootAdvanceSeconds = 30
)

$ErrorActionPreference = 'Stop'
$stateDir = Join-Path $env:LOCALAPPDATA 'OrdaX\DevAgent'
$cutoverStatePath = Join-Path $stateDir 'cloudflare-v3-cutover.json'
$finalizedProofPath = Join-Path $stateDir 'cloudflare-v3-finalized.json'
$settingsPath = Join-Path $stateDir 'agent-settings.json'
$statusUrl = 'http://127.0.0.1:8765/status'
$mutex = New-Object System.Threading.Mutex($false, 'Local\OrdaXDeviceSetup')
$locked = $false

function Write-AtomicText([string]$Path, [string]$Text) {
    $temp = "$Path.next"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($temp, $Text, $utf8NoBom)
    Move-Item -LiteralPath $temp -Destination $Path -Force
}

function Write-AtomicJson([string]$Path, $Value) {
    Write-AtomicText -Path $Path -Text ($Value | ConvertTo-Json -Depth 20)
}

function Remove-JsonProperty($Object, [string]$Name) {
    if ($Object -and $Object.PSObject.Properties[$Name]) {
        $Object.PSObject.Properties.Remove($Name)
    }
}

function Retire-DevelopmentV2LocalState(
    [string]$ExpectedDeviceId,
    [string]$ExpectedControlPlaneUrl,
    [string]$LastBlenderAction,
    [double]$HeartbeatAgeSeconds,
    [double]$CurrentBootEpochMs
) {
    if (-not (Test-Path $settingsPath -PathType Leaf)) {
        throw 'AGENT_SETTINGS_MISSING_DURING_V2_RETIREMENT'
    }
    $cloudflareTokenPath = Join-Path $stateDir 'device-token.cloudflare-v3.txt'
    if (-not (Test-Path $cloudflareTokenPath -PathType Leaf)) {
        throw 'CLOUDFLARE_V3_CREDENTIAL_MISSING_DURING_V2_RETIREMENT'
    }

    $settings = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $settings) {
        throw 'AGENT_SETTINGS_INVALID_DURING_V2_RETIREMENT'
    }
    if ([string]$settings.control_plane_protocol -ne 'cloudflare-v3') {
        throw 'V2_RETIREMENT_REQUIRES_CLOUDFLARE_V3_ACTIVE'
    }
    if ([string]$settings.development_device_id -ne $ExpectedDeviceId) {
        throw 'V2_RETIREMENT_DEVICE_ID_MISMATCH'
    }
    $settingsUrl = if ($settings.control_plane_url) {
        ([string]$settings.control_plane_url).TrimEnd('/')
    } else {
        ''
    }
    if ($settingsUrl -ne $ExpectedControlPlaneUrl) {
        throw 'V2_RETIREMENT_CONTROL_PLANE_URL_MISMATCH'
    }

    if (
        $settings.PSObject.Properties['control_plane_identities'] -and
        $settings.control_plane_identities
    ) {
        Remove-JsonProperty -Object $settings.control_plane_identities -Name 'development-v2'
    }
    Remove-JsonProperty -Object $settings -Name 'supabase_url'
    Remove-JsonProperty -Object $settings -Name 'publishable_key'

    $proof = [ordered]@{
        status = 'retiring-development-v2'
        finalized_at = [DateTime]::UtcNow.ToString('o')
        control_plane_protocol = 'cloudflare-v3'
        control_plane_url = $ExpectedControlPlaneUrl
        device_id = $ExpectedDeviceId
        windows_boot_epoch_ms = $CurrentBootEpochMs
        heartbeat_age_seconds = $HeartbeatAgeSeconds
        last_blender_action = $LastBlenderAction
        development_v2_local_state_retired = $false
    }

    Write-AtomicJson -Path $finalizedProofPath -Value $proof
    Write-AtomicJson -Path $settingsPath -Value $settings

    $sanitized = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (
        -not $sanitized -or
        [string]$sanitized.control_plane_protocol -ne 'cloudflare-v3' -or
        [string]$sanitized.development_device_id -ne $ExpectedDeviceId -or
        (([string]$sanitized.control_plane_url).TrimEnd('/')) -ne $ExpectedControlPlaneUrl
    ) {
        throw 'SANITIZED_CLOUDFLARE_V3_SETTINGS_INVALID'
    }
    if (
        $sanitized.PSObject.Properties['supabase_url'] -or
        $sanitized.PSObject.Properties['publishable_key']
    ) {
        throw 'SANITIZED_SETTINGS_STILL_CONTAIN_SUPABASE_KEYS'
    }
    if (
        $sanitized.PSObject.Properties['control_plane_identities'] -and
        $sanitized.control_plane_identities -and
        $sanitized.control_plane_identities.PSObject.Properties['development-v2']
    ) {
        throw 'SANITIZED_SETTINGS_STILL_CONTAIN_DEVELOPMENT_V2_IDENTITY'
    }

    $legacyCredentialFiles = @(
        'device-token.development-v2.txt',
        'device-token.development-v2.txt.pending-setup',
        'device-token.development-v2.txt.pending-recovery',
        'device-token.development-v2.txt.pending-enrollment',
        'device-token.txt',
        'device-token.txt.pending-setup',
        'device-token.txt.pending-recovery',
        'device-token.txt.pending-enrollment'
    )
    foreach ($name in $legacyCredentialFiles) {
        $path = Join-Path $stateDir $name
        Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
        if (Test-Path $path) {
            throw "V2_RETIREMENT_CREDENTIAL_DELETE_FAILED=$name"
        }
    }

    if (-not (Test-Path $cloudflareTokenPath -PathType Leaf)) {
        throw 'CLOUDFLARE_V3_CREDENTIAL_LOST_DURING_V2_RETIREMENT'
    }

    [Environment]::SetEnvironmentVariable('ORDAX_SUPABASE_URL', $null, 'User')
    [Environment]::SetEnvironmentVariable('ORDAX_SUPABASE_PUBLISHABLE_KEY', $null, 'User')

    $proof.status = 'finalized'
    $proof.development_v2_local_state_retired = $true
    Write-AtomicJson -Path $finalizedProofPath -Value $proof
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

    $retirementArgs = @{
        ExpectedDeviceId = [string]$cutover.target_device_id
        ExpectedControlPlaneUrl = $expectedUrl
        LastBlenderAction = $lastAction
        HeartbeatAgeSeconds = $heartbeatAge
        CurrentBootEpochMs = $currentBoot
    }
    Retire-DevelopmentV2LocalState @retirementArgs

    $backupPath = [string]$cutover.backup_path
    if ($backupPath) {
        Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $cutoverStatePath -Force

    Write-Output 'ORDAX_CLOUDFLARE_V3_REBOOT_PROOF=PASS'
    Write-Output "CONTROL_PLANE_URL=$expectedUrl"
    Write-Output "DEVICE_ID=$($cutover.target_device_id)"
    Write-Output "BLENDER_JOB=$lastAction"
    Write-Output "FINALIZED_PROOF=$finalizedProofPath"
    Write-Output 'DEVELOPMENT_V2_LOCAL_STATE=RETIRED'
    Write-Output 'SUPABASE_ROLLBACK_SNAPSHOT=RELEASED'
} finally {
    if ($locked) {
        $mutex.ReleaseMutex()
        $mutex.Dispose()
    }
}
