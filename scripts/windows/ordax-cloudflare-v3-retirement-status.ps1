param(
    [ValidateRange(10, 300)]
    [int]$HeartbeatMaxAgeSeconds = 90
)

$ErrorActionPreference = 'Stop'
$stateDir = Join-Path $env:LOCALAPPDATA 'OrdaX\DevAgent'
$proofPath = Join-Path $stateDir 'cloudflare-v3-finalized.json'
$settingsPath = Join-Path $stateDir 'agent-settings.json'
$cutoverPath = Join-Path $stateDir 'cloudflare-v3-cutover.json'
$cloudflareTokenPath = Join-Path $stateDir 'device-token.cloudflare-v3.txt'
$statusUrl = 'http://127.0.0.1:8765/status'
$blockers = [System.Collections.Generic.List[string]]::new()

function Add-Blocker([string]$Value) {
    if (-not $blockers.Contains($Value)) {
        [void]$blockers.Add($Value)
    }
}

function Read-JsonFile([string]$Path, [string]$MissingCode, [string]$InvalidCode) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        Add-Blocker $MissingCode
        return $null
    }
    try {
        $value = Get-Content $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        Add-Blocker $InvalidCode
        return $null
    }
    if (-not $value) {
        Add-Blocker $InvalidCode
        return $null
    }
    return $value
}

$proof = Read-JsonFile $proofPath 'FINALIZED_PROOF_MISSING' 'FINALIZED_PROOF_INVALID'
$settings = Read-JsonFile $settingsPath 'AGENT_SETTINGS_MISSING' 'AGENT_SETTINGS_INVALID'

if ($proof) {
    if ([string]$proof.status -ne 'finalized') {
        Add-Blocker 'FINALIZED_PROOF_NOT_FINALIZED'
    }
    if ([string]$proof.control_plane_protocol -ne 'cloudflare-v3') {
        Add-Blocker 'FINALIZED_PROOF_PROTOCOL_MISMATCH'
    }
    if ($proof.development_v2_local_state_retired -ne $true) {
        Add-Blocker 'DEVELOPMENT_V2_LOCAL_STATE_NOT_RETIRED'
    }
}

if ($settings) {
    if ([string]$settings.control_plane_protocol -ne 'cloudflare-v3') {
        Add-Blocker 'ACTIVE_PROTOCOL_NOT_CLOUDFLARE_V3'
    }
    if (-not $settings.control_plane_url) {
        Add-Blocker 'CLOUDFLARE_CONTROL_PLANE_URL_MISSING'
    }
    if (-not $settings.development_device_id) {
        Add-Blocker 'CLOUDFLARE_DEVICE_ID_MISSING'
    }
    if (
        $settings.PSObject.Properties['supabase_url'] -or
        $settings.PSObject.Properties['publishable_key']
    ) {
        Add-Blocker 'SUPABASE_SETTINGS_STILL_PRESENT'
    }
    if (
        $settings.PSObject.Properties['control_plane_identities'] -and
        $settings.control_plane_identities -and
        $settings.control_plane_identities.PSObject.Properties['development-v2']
    ) {
        Add-Blocker 'DEVELOPMENT_V2_IDENTITY_STILL_PRESENT'
    }
}

if ($proof -and $settings) {
    $proofUrl = ([string]$proof.control_plane_url).TrimEnd('/')
    $settingsUrl = ([string]$settings.control_plane_url).TrimEnd('/')
    if ($proofUrl -ne $settingsUrl) {
        Add-Blocker 'FINALIZED_PROOF_URL_MISMATCH'
    }
    if ([string]$proof.device_id -ne [string]$settings.development_device_id) {
        Add-Blocker 'FINALIZED_PROOF_DEVICE_MISMATCH'
    }
}

if (-not (Test-Path $cloudflareTokenPath -PathType Leaf)) {
    Add-Blocker 'CLOUDFLARE_V3_CREDENTIAL_MISSING'
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
$legacyCredentialsPresent = @(
    $legacyCredentialFiles | Where-Object {
        Test-Path (Join-Path $stateDir $_)
    }
)
if ($legacyCredentialsPresent.Count -gt 0) {
    Add-Blocker 'DEVELOPMENT_V2_CREDENTIALS_STILL_PRESENT'
}
if (Test-Path $cutoverPath) {
    Add-Blocker 'CUTOVER_STATE_STILL_PENDING'
}

$live = $null
$heartbeatAge = $null
try {
    $live = Invoke-RestMethod -Uri $statusUrl -TimeoutSec 4
} catch {
    Add-Blocker 'LOCAL_AGENT_STATUS_UNAVAILABLE'
}
if ($live) {
    if ([string]$live.control_plane_protocol -ne 'cloudflare-v3') {
        Add-Blocker 'LIVE_PROTOCOL_NOT_CLOUDFLARE_V3'
    }
    if ($proof) {
        if ([string]$live.development_device_id -ne [string]$proof.device_id) {
            Add-Blocker 'LIVE_DEVICE_MISMATCH'
        }
        $liveUrl = ([string]$live.control_plane_url).TrimEnd('/')
        $proofUrl = ([string]$proof.control_plane_url).TrimEnd('/')
        if ($liveUrl -ne $proofUrl) {
            Add-Blocker 'LIVE_CONTROL_PLANE_URL_MISMATCH'
        }
    }
    if (-not $live.runtime -or -not $live.runtime.last_heartbeat_at) {
        Add-Blocker 'LIVE_HEARTBEAT_MISSING'
    } else {
        $heartbeatAge = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - [double]$live.runtime.last_heartbeat_at
        if ($heartbeatAge -ge $HeartbeatMaxAgeSeconds) {
            Add-Blocker 'LIVE_HEARTBEAT_STALE'
        }
    }
}

$result = [ordered]@{
    ready_for_repository_v2_removal = ($blockers.Count -eq 0)
    checked_at = [DateTime]::UtcNow.ToString('o')
    control_plane_protocol = if ($settings) { [string]$settings.control_plane_protocol } else { $null }
    control_plane_url = if ($settings) { [string]$settings.control_plane_url } else { $null }
    device_id = if ($settings) { [string]$settings.development_device_id } else { $null }
    finalized_proof_exists = (Test-Path $proofPath -PathType Leaf)
    cloudflare_credential_present = (Test-Path $cloudflareTokenPath -PathType Leaf)
    development_v2_local_state_retired = if ($proof) { [bool]$proof.development_v2_local_state_retired } else { $false }
    legacy_credential_file_count = $legacyCredentialsPresent.Count
    cutover_state_pending = (Test-Path $cutoverPath)
    live_agent_available = [bool]$live
    heartbeat_age_seconds = $heartbeatAge
    blockers = @($blockers)
}

$result | ConvertTo-Json -Depth 8 -Compress
