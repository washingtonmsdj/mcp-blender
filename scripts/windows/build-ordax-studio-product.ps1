param(
    [string]$Version = "",
    [string]$OutputDirectory = "",
    [string]$PythonVersion = "3.12.10"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repoRoot "dist\windows"
}
if (-not $Version) {
    $pyproject = Get-Content (Join-Path $repoRoot "pyproject.toml") -Raw
    if ($pyproject -notmatch '(?m)^version\s*=\s*"([^"]+)"') {
        throw "Unable to read project version from pyproject.toml"
    }
    $Version = $Matches[1]
}

$hostVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$targetMinor = ($PythonVersion -split '\.')[0..1] -join '.'
if ($hostVersion.Trim() -ne $targetMinor) {
    throw "Build Python must be $targetMinor.x to match the embedded runtime; found $hostVersion"
}

$buildRoot = Join-Path $repoRoot "build\windows-product"
$stageRoot = Join-Path $buildRoot "stage"
$runtimeRoot = Join-Path $stageRoot "runtime"
$redistRoot = Join-Path $stageRoot "redist"
$cacheRoot = Join-Path $buildRoot "cache"
Remove-Item $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $runtimeRoot, $redistRoot, $cacheRoot, $OutputDirectory | Out-Null

$pythonZip = Join-Path $cacheRoot "python-$PythonVersion-embed-amd64.zip"
if (-not (Test-Path $pythonZip)) {
    $pythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
    Write-Host "Downloading private CPython runtime: $pythonUrl"
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonZip
}
Expand-Archive -LiteralPath $pythonZip -DestinationPath $runtimeRoot -Force

$stdlibZip = Get-ChildItem $runtimeRoot -Filter "python*.zip" | Select-Object -First 1
$pth = Get-ChildItem $runtimeRoot -Filter "python*._pth" | Select-Object -First 1
if (-not $stdlibZip -or -not $pth) {
    throw "Embedded Python runtime is incomplete"
}
@(
    $stdlibZip.Name,
    ".",
    "Lib",
    "Lib\site-packages",
    "import site"
) | Set-Content -LiteralPath $pth.FullName -Encoding ASCII

$sitePackages = Join-Path $runtimeRoot "Lib\site-packages"
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null
& python -m pip install --disable-pip-version-check --no-compile --upgrade --target $sitePackages $repoRoot
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install ORDAX runtime into the private Python distribution"
}

Copy-Item (Join-Path $repoRoot "scripts") (Join-Path $stageRoot "scripts") -Recurse -Force

$privatePython = Join-Path $runtimeRoot "python.exe"
& $privatePython -c "import ordax_studio, ordax_dev_agent, ordax_device_agent, webview; print('ORDAX_PRIVATE_RUNTIME_OK')"
if ($LASTEXITCODE -ne 0) {
    throw "Private ORDAX Python runtime import smoke failed"
}

$webViewBootstrapper = Join-Path $redistRoot "MicrosoftEdgeWebview2Setup.exe"
Write-Host "Downloading Microsoft Edge WebView2 Evergreen bootstrapper"
Invoke-WebRequest -Uri "https://go.microsoft.com/fwlink/p/?LinkId=2124703" -OutFile $webViewBootstrapper
if ((Get-Item $webViewBootstrapper).Length -lt 100000) {
    throw "WebView2 bootstrapper download is unexpectedly small"
}

$cl = Get-Command cl.exe -ErrorAction SilentlyContinue
if (-not $cl) {
    throw "cl.exe was not found. Run from a Visual Studio developer environment."
}
$launcherSource = Join-Path $repoRoot "packaging\windows\ordax_launcher.c"
$studioExe = Join-Path $stageRoot "ORDAX Dev.exe"
$runtimeExe = Join-Path $stageRoot "ORDAX Runtime.exe"

Push-Location $buildRoot
try {
    & cl.exe /nologo /O2 /W4 /DUNICODE /D_UNICODE /DORDAX_RUNTIME_LAUNCHER=0 "/Fe:$studioExe" $launcherSource /link /SUBSYSTEM:WINDOWS user32.lib
    if ($LASTEXITCODE -ne 0) { throw "ORDAX Studio launcher compilation failed" }
    Remove-Item "ordax_launcher.obj" -Force -ErrorAction SilentlyContinue

    & cl.exe /nologo /O2 /W4 /DUNICODE /D_UNICODE /DORDAX_RUNTIME_LAUNCHER=1 "/Fe:$runtimeExe" $launcherSource /link /SUBSYSTEM:WINDOWS user32.lib
    if ($LASTEXITCODE -ne 0) { throw "ORDAX Runtime launcher compilation failed" }
    Remove-Item "ordax_launcher.obj" -Force -ErrorAction SilentlyContinue
} finally {
    Pop-Location
}

if (-not (Test-Path $studioExe) -or -not (Test-Path $runtimeExe)) {
    throw "Native ORDAX launchers were not produced"
}

$manifest = [ordered]@{
    schema = "ordax.windows-product/1"
    product = "ORDAX Dev"
    version = $Version
    architecture = "x64"
    python = $PythonVersion
    entrypoints = @{
        studio = "ORDAX Dev.exe"
        runtime = "ORDAX Runtime.exe"
    }
    control_plane = "https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev"
    built_at = [DateTimeOffset]::UtcNow.ToString("o")
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $stageRoot "product-manifest.json") -Encoding UTF8

$isccPath = $null
$isccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($isccCommand) {
    $isccPath = $isccCommand.Source
}
if (-not $isccPath) {
    $candidate = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $candidate) {
        $isccPath = $candidate
    }
}
if (-not $isccPath) {
    throw "Inno Setup 6 (ISCC.exe) was not found"
}

$iss = Join-Path $repoRoot "packaging\windows\ordax-studio.iss"
& $isccPath "/DStageDir=$stageRoot" "/DAppVersion=$Version" "/DOutputDir=$OutputDirectory" $iss
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed"
}

$setup = Get-ChildItem $OutputDirectory -Filter "ORDAX-Dev-Setup-*.exe" | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
if (-not $setup) {
    throw "Installer output was not produced"
}
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $setup.FullName).Hash.ToLowerInvariant()
Write-Output "ORDAX_DEV_SETUP=$($setup.FullName)"
Write-Output "ORDAX_DEV_SETUP_SHA256=$hash"
