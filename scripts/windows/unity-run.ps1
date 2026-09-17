param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectPath,

    [Parameter(Mandatory=$true)]
    [string]$ExecuteMethod,

    [string]$LogFile = ""
)

$ErrorActionPreference = "Stop"

$unity = $env:UNITY_EXE
if (-not $unity -or -not (Test-Path $unity)) {
    $candidate = Get-ChildItem "C:\Program Files\Unity\Hub\Editor\*\Editor\Unity.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        Select-Object -First 1

    if ($candidate) { $unity = $candidate.FullName }
}

if (-not $unity -or -not (Test-Path $unity)) {
    throw "Unity executable not found. Set UNITY_EXE."
}

if (-not (Test-Path $ProjectPath)) {
    throw "Unity project not found: $ProjectPath"
}

if (-not (Test-Path (Join-Path $ProjectPath "Assets"))) {
    throw "ProjectPath does not contain Assets/: $ProjectPath"
}

if (-not $LogFile) {
    $logs = Join-Path $ProjectPath "Logs"
    New-Item -ItemType Directory -Force -Path $logs | Out-Null
    $LogFile = Join-Path $logs "unity-cli.log"
}

& $unity -batchmode -quit -projectPath $ProjectPath -executeMethod $ExecuteMethod -logFile $LogFile
$exitCode = $LASTEXITCODE

Write-Host "Unity exit code: $exitCode"
Write-Host "Unity log: $LogFile"

if (Test-Path $LogFile) {
    Get-Content $LogFile -Tail 200
}

exit $exitCode
