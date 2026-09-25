param(
    [Parameter(Mandatory = $true)]
    [ValidateLength(40, 128)]
    [string]$GrantCode,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F-]{36}$')]
    [string]$DeviceId,

    [string]$ControlPlaneUrl = "https://eobcxuyvhkvdmkbaihwh.supabase.co"
)

$ErrorActionPreference = "Stop"
$stateDir = Join-Path $env:LOCALAPPDATA "OrdaX\DevAgent"
$tokenPath = Join-Path $stateDir "device-token.txt"
$pendingPath = Join-Path $stateDir "device-token.txt.pending-recovery"
$recoveryUrl = $ControlPlaneUrl.TrimEnd("/") + "/functions/v1/ordax-development-recovery"

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

function Write-PrivateTokenFile([string]$Path, [string]$Token) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Token + [Environment]::NewLine, $utf8NoBom)
    try {
        & icacls.exe $Path /inheritance:r /grant:r "${env:USERNAME}:F" | Out-Null
    } catch {
        Write-Warning "Could not tighten token ACL with icacls; continuing with user-local state path."
    }
}

function Read-UsableToken([string]$Path) {
    if (-not (Test-Path $Path -PathType Leaf)) { return $null }
    try {
        $value = (Get-Content $Path -Raw -Encoding UTF8).Trim()
    } catch {
        return $null
    }
    if ($value -match '^[0-9a-f]{64}$') { return $value }
    return $null
}

$token = Read-UsableToken $pendingPath
if (-not $token) {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    } finally {
        $rng.Dispose()
    }
    $token = -join ($bytes | ForEach-Object { $_.ToString("x2") })
    Write-PrivateTokenFile -Path $pendingPath -Token $token
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
    action = "development-credential-recovery"
    grant_code = $GrantCode
    device_id = $DeviceId
    token_sha256 = $tokenHash
} | ConvertTo-Json -Compress

try {
    $response = Invoke-RestMethod -Method Post -Uri $recoveryUrl -ContentType "application/json" -Body $body -TimeoutSec 20
} catch {
    throw "Development credential recovery transport failed. Pending token was preserved for safe replay."
}

if (-not $response -or $response.ok -ne $true -or $response.recovery -ne "COMMITTED") {
    throw "Development credential recovery was not committed. Pending token was preserved for safe replay."
}

Move-Item -Force $pendingPath $tokenPath
Write-Host "ORDAX_DEVELOPMENT_V2_RECOVERY=PASS"
Write-Host "DEVICE_ID=$DeviceId"
Write-Host "CONTROL_PLANE=ordax-control-plane"
Write-Host "TOKEN_ROTATED=YES"
Write-Host "TOKEN_VALUE=REDACTED"
