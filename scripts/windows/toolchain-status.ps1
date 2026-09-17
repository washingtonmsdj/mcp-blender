param()

$ErrorActionPreference = "Stop"

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
    if ($env:UNITY_EXE -and (Test-Path $env:UNITY_EXE)) {
        return $env:UNITY_EXE
    }

    $items = Get-ChildItem "C:\Program Files\Unity\Hub\Editor\*\Editor\Unity.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending

    if ($items) { return $items[0].FullName }
    return $null
}

$blender = Find-Blender
$unity = Find-Unity

Write-Host "Blender: $blender"
Write-Host "Unity:   $unity"

if (-not $blender) { Write-Warning "Blender was not found." }
if (-not $unity) { Write-Warning "Unity was not found." }

if (-not $blender -or -not $unity) {
    exit 1
}

exit 0
