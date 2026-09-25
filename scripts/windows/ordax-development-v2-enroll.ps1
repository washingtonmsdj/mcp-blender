param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F-]{36}$')]
    [string]$DeviceId,

    [Parameter(Mandatory = $true)]
    [ValidateLength(40, 128)]
    [string]$GrantCode,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{64}$')]
    [string]$ExpectedMachineBindingSha256,

    [string]$ControlPlaneUrl = "https://eobcxuyvhkvdmkbaihwh.supabase.co"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$installer = Join-Path $repoRoot "scripts\windows\ordax-agent-install.ps1"
$stateDir = Join-Path $env:LOCALAPPDATA "OrdaX\DevAgent"
$settingsPath = Join-Path $stateDir "agent-settings.json"
$tokenPath = Join-Path $stateDir "device-token.txt"
$pendingPath = Join-Path $stateDir "device-token.txt.pending-enrollment"
$endpoint = $ControlPlaneUrl.TrimEnd("/") + "/functions/v1/ordax-device-enrollment"

if (-not (Test-Path $python -PathType Leaf)) {
    throw "Managed Python is missing: $python"
}
if (-not (Test-Path $installer -PathType Leaf)) {
    throw "Agent installer is missing: $installer"
}

$machineBinding = (& $python -c "from ordax_dev_agent.identity import machine_id; print(machine_id())").Trim().ToLowerInvariant()
if ($LASTEXITCODE -ne 0 -or $machineBinding -notmatch '^[0-9a-f]{64}$') {
    throw "Could not resolve the local machine binding."
}
if ($machineBinding -ne $ExpectedMachineBindingSha256.ToLowerInvariant()) {
    throw "Machine binding mismatch. Enrollment was refused."
}

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

function Write-PrivateToken([string]$Path, [string]$Token) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Token + [Environment]::NewLine, $utf8NoBom)
    try {
        $principal = $env:USERNAME + ":F"
        & icacls.exe $Path /inheritance:r /grant:r $principal | Out-Null
    } catch {
        Write-Warning "Could not tighten token ACL with icacls; token remains under the user-local state directory."
    }
}

function Read-PendingToken {
    if (-not (Test-Path $pendingPath -PathType Leaf)) { return $null }
    try {
        $value = (Get-Content $pendingPath -Raw -Encoding UTF8).Trim()
    } catch {
        return $null
    }
    if ($value -match '^[0-9a-f]{64}$') { return $value }
    return $null
}

$token = Read-PendingToken
if (-not $token) {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $token = -join ($bytes | ForEach-Object { $_.ToString("x2") })
    Write-PrivateToken -Path $pendingPath -Token $token
}

$sha = [System.Security.Cryptography.SHA256]::Create()
try {
    $tokenHash = -join (
        $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($token)) |
        ForEach-Object { $_.ToString("x2") }
    )
} finally {
    $sha.Dispose()
}

$body = @{
    grant_code = $GrantCode
    device_id = $DeviceId
    device_binding_sha256 = $machineBinding
    token_sha256 = $tokenHash
} | ConvertTo-Json -Compress

try {
    $response = Invoke-RestMethod -Method Post -Uri $endpoint -ContentType "application/json" -Body $body -TimeoutSec 20
} catch {
    throw "Device enrollment transport failed. Pending token was preserved for safe replay."
}

if (-not $response -or $response.ok -ne $true -or $response.enrollment -ne "COMMITTED") {
    throw "Device enrollment was not committed. Pending token was preserved for safe replay."
}

Move-Item -Force $pendingPath $tokenPath

$settings = [pscustomobject]@{}
if (Test-Path $settingsPath -PathType Leaf) {
    try {
        $settings = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        throw "Existing agent-settings.json is invalid."
    }
    if (-not $settings) { $settings = [pscustomobject]@{} }
}

$settings | Add-Member -NotePropertyName supabase_url -NotePropertyValue $ControlPlaneUrl.TrimEnd("/") -Force
$settings | Add-Member -NotePropertyName control_plane_protocol -NotePropertyValue "development-v2" -Force
$settings | Add-Member -NotePropertyName development_device_id -NotePropertyValue $DeviceId -Force

if (-not $settings.PSObject.Properties["projects"] -or -not $settings.projects) {
    $settings | Add-Member -NotePropertyName projects -NotePropertyValue ([pscustomobject]@{}) -Force
}

$cercoRoot = Join-Path $env:USERPROFILE "Documents\github\cerco-no-interior-mvp"
if (Test-Path $cercoRoot -PathType Container) {
    $project = [pscustomobject]@{
        path = $cercoRoot
        apps = @("blender")
        blender = [pscustomobject]@{ scripts_dir = "automation/blender" }
    }
    $settings.projects | Add-Member -NotePropertyName "cerco-no-interior-mvp" -NotePropertyValue $project -Force
}

$tempSettings = "$settingsPath.next"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($tempSettings, ($settings | ConvertTo-Json -Depth 12), $utf8NoBom)
Move-Item -Force $tempSettings $settingsPath

$taskName = "OrdaX Dev Agent"
Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer -StartNow
if ($LASTEXITCODE -ne 0) {
    throw "Device enrolled, but Scheduled Task installation/start failed."
}

Write-Host "ORDAX_DEVICE_ENROLLMENT=PASS"
Write-Host "DEVICE_ID=$DeviceId"
Write-Host "COMPUTER=$env:COMPUTERNAME"
Write-Host "CONTROL_PLANE=ordax-control-plane"
Write-Host "PROTOCOL=development-v2"
Write-Host "MACHINE_BINDING_MATCH=YES"
Write-Host "TOKEN_VALUE=REDACTED"
