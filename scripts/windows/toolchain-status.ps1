param(
    [switch]$RequireBlender,
    [switch]$RequireUnity,
    [string]$ProjectPath = ""
)

$ErrorActionPreference = "Stop"

function Get-RequiredUnityVersion {
    param([string]$Root)

    if (-not $Root) { return $null }

    $versionFile = Join-Path $Root "ProjectSettings\ProjectVersion.txt"
    if (-not (Test-Path $versionFile)) { return $null }

    $match = Select-String -Path $versionFile -Pattern '^m_EditorVersion:\s*(\S+)\s*$' | Select-Object -First 1
    if ($match) {
        return $match.Matches[0].Groups[1].Value
    }

    return $null
}

function Find-Blender {
    if ($env:BLENDER_EXE -and (Test-Path $env:BLENDER_EXE)) {
        return $env:BLENDER_EXE
    }

    $items = Get-ChildItem "C:\Program Files\Blender Foundation\Blender *\blender.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending

    if ($items) { return $items[0].FullName }
    return $null
}

function Find-Unity {
    param([string]$Root)

    if ($env:UNITY_EXE -and (Test-Path $env:UNITY_EXE)) {
        return $env:UNITY_EXE
    }

    $requiredVersion = Get-RequiredUnityVersion -Root $Root
    if ($requiredVersion) {
        $exact = "C:\Program Files\Unity\Hub\Editor\$requiredVersion\Editor\Unity.exe"
        if (Test-Path $exact) { return $exact }
        return $null
    }

    $items = Get-ChildItem "C:\Program Files\Unity\Hub\Editor\*\Editor\Unity.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending

    if ($items) { return $items[0].FullName }
    return $null
}

if ($ProjectPath) {
    $ProjectPath = (Resolve-Path $ProjectPath).Path
}

$requiredVersion = Get-RequiredUnityVersion -Root $ProjectPath
$blender = Find-Blender
$unity = Find-Unity -Root $ProjectPath
$python = Get-Command python -ErrorAction SilentlyContinue
$git = Get-Command git -ErrorAction SilentlyContinue

$unityReferenceAssemblies = $null
$unityReferenceAssembliesOk = $null
if ($unity) {
    $unityEditorDir = Split-Path -Parent $unity
    $unityReferenceAssemblies = Join-Path $unityEditorDir "Data\UnityReferenceAssemblies\unity-4.8-api\Facades"
    $unityReferenceAssembliesOk = Test-Path $unityReferenceAssemblies
}

Write-Host "Blender:          $blender"
Write-Host "Unity:            $unity"
Write-Host "Required Unity:   $requiredVersion"
if ($unity) {
    Write-Host "Unity refs:       $unityReferenceAssembliesOk"
    if (-not $unityReferenceAssembliesOk) {
        Write-Host "Missing refs:     $unityReferenceAssemblies"
    }
}
Write-Host "Python:           $($python.Source)"
Write-Host "Git:              $($git.Source)"

$failed = $false

if (-not $blender) {
    Write-Warning "Blender was not found."
    if ($RequireBlender) { $failed = $true }
}

if (-not $unity) {
    if ($requiredVersion) {
        Write-Warning "Unity $requiredVersion required by project was not found."
    }
    else {
        Write-Warning "Unity was not found."
    }

    if ($RequireUnity) { $failed = $true }
}
elseif ($unityReferenceAssembliesOk -eq $false) {
    Write-Warning "Unity Editor installation is incomplete: required reference assemblies are missing."
    if ($RequireUnity) { $failed = $true }
}

if (-not $python) {
    Write-Warning "Python was not found."
}

if (-not $git) {
    Write-Warning "Git was not found."
}

if ($failed) {
    exit 1
}

exit 0
