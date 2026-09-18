# Shared Unity discovery and installation diagnostics for Windows PowerShell 5.1+.

function Get-RequiredUnityVersion {
    param([string]$Root)

    if (-not $Root) { return $null }

    $versionFile = Join-Path $Root "ProjectSettings\ProjectVersion.txt"
    if (-not (Test-Path -LiteralPath $versionFile)) { return $null }

    $match = Select-String -LiteralPath $versionFile -Pattern '^m_EditorVersion:\s*(\S+)\s*$' |
        Select-Object -First 1
    if ($match) { return $match.Matches[0].Groups[1].Value }
    return $null
}

function Get-UnityEditorRoots {
    $roots = @()

    if ($env:UNITY_EDITOR_ROOTS) {
        $roots += $env:UNITY_EDITOR_ROOTS -split [IO.Path]::PathSeparator
    }

    $roots += "C:\Program Files\Unity\Hub\Editor"
    if ($env:LOCALAPPDATA) { $roots += (Join-Path $env:LOCALAPPDATA "Unity\Hub\Editor") }
    if ($env:USERPROFILE) { $roots += (Join-Path $env:USERPROFILE "Unity\Hub\Editor") }

    $seen = @{}
    foreach ($root in $roots) {
        if ([string]::IsNullOrWhiteSpace($root)) { continue }
        $key = $root.ToLowerInvariant()
        if (-not $seen.ContainsKey($key)) {
            $seen[$key] = $true
            $root
        }
    }
}

function Find-Unity {
    param([string]$Root)

    if ($env:UNITY_EXE -and (Test-Path -LiteralPath $env:UNITY_EXE) -and
        ((Get-Item -LiteralPath $env:UNITY_EXE).PSIsContainer -eq $false)) {
        return $env:UNITY_EXE
    }

    $requiredVersion = Get-RequiredUnityVersion -Root $Root
    $candidates = @()
    foreach ($editorRoot in (Get-UnityEditorRoots)) {
        if ($requiredVersion) {
            $exact = Join-Path $editorRoot "$requiredVersion\Editor\Unity.exe"
            if (Test-Path -LiteralPath $exact) { return $exact }
        }
        elseif (Test-Path -LiteralPath $editorRoot) {
            $candidates += Get-ChildItem -LiteralPath $editorRoot -Directory -ErrorAction SilentlyContinue |
                ForEach-Object { Join-Path $_.FullName "Editor\Unity.exe" } |
                Where-Object { Test-Path -LiteralPath $_ }
        }
    }

    if ($requiredVersion) { return $null }
    return ($candidates | Sort-Object -Descending | Select-Object -First 1)
}

function Get-UnityApiCompatibilityLevel {
    param([string]$Root)

    if (-not $Root) { return $null }
    $settingsFile = Join-Path $Root "ProjectSettings\ProjectSettings.asset"
    if (-not (Test-Path -LiteralPath $settingsFile)) { return $null }

    $match = Select-String -LiteralPath $settingsFile -Pattern '^\s*apiCompatibilityLevel:\s*(\d+)\s*$' |
        Select-Object -First 1
    if ($match) { return [int]$match.Matches[0].Groups[1].Value }
    return $null
}

function Get-UnityInstallationDiagnostics {
    param(
        [string]$Unity,
        [string]$ProjectRoot
    )

    if (-not $Unity) {
        return [PSCustomObject]@{
            EditorAvailable = $false
            ApiCompatibilityLevel = Get-UnityApiCompatibilityLevel -Root $ProjectRoot
            ReferenceAssembliesRequired = $null
            ReferenceAssembliesAvailable = $null
            ReferenceAssembliesPath = $null
            PackageManagerAvailable = $false
            PackageManagerPath = $null
            MissingComponents = @("Unity.exe")
            InstallationHealthy = $false
        }
    }

    $editorDir = Split-Path -Parent $Unity
    $dataDir = Join-Path $editorDir "Data"
    $apiLevel = Get-UnityApiCompatibilityLevel -Root $ProjectRoot
    $references = Join-Path $dataDir "UnityReferenceAssemblies\unity-4.8-api\Facades"
    $upm = Join-Path $dataDir "Resources\PackageManager\Server\UnityPackageManager.exe"
    $required = if ($null -ne $apiLevel) { $apiLevel -eq 6 } else { $null }
    $referencesAvailable = if ($required -eq $false) { $null } else { Test-Path -LiteralPath $references }
    $missing = @()

    if (-not (Test-Path -LiteralPath $Unity)) { $missing += $Unity }
    if (-not (Test-Path -LiteralPath $dataDir)) { $missing += $dataDir }
    if ($required -and -not $referencesAvailable) { $missing += $references }
    if (-not (Test-Path -LiteralPath $upm)) { $missing += $upm }

    [PSCustomObject]@{
        EditorAvailable = Test-Path -LiteralPath $Unity
        ApiCompatibilityLevel = $apiLevel
        ReferenceAssembliesRequired = $required
        ReferenceAssembliesAvailable = $referencesAvailable
        ReferenceAssembliesPath = $references
        PackageManagerAvailable = Test-Path -LiteralPath $upm
        PackageManagerPath = $upm
        MissingComponents = $missing
        InstallationHealthy = ($missing.Count -eq 0)
    }
}
