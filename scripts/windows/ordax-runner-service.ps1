param(
    [string]$RunnerPath = ""
)

$ErrorActionPreference = "Stop"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Administrator privileges are required to install or harden the GitHub Actions runner service."
    }
}

function Find-ConfiguredRunnerRoot {
    param([string]$ExplicitPath)

    if ($ExplicitPath) {
        $candidate = (Resolve-Path $ExplicitPath -ErrorAction Stop).Path
        if ((Test-Path (Join-Path $candidate ".runner")) -and (Test-Path (Join-Path $candidate "svc.cmd"))) {
            return $candidate
        }
        throw "RunnerPath is not a configured GitHub Actions runner: $candidate"
    }

    $service = Get-CimInstance Win32_Service |
        Where-Object { $_.Name -like "actions.runner.*" } |
        Select-Object -First 1

    if ($service -and $service.PathName) {
        $pathName = [Environment]::ExpandEnvironmentVariables($service.PathName.Trim())
        $exe = $null
        if ($pathName -match '"([^"]*RunnerService\.exe)"') {
            $exe = $matches[1]
        } else {
            $exe = ($pathName -split '\s+')[0].Trim('"')
        }

        if ($exe) {
            $root = Split-Path -Parent $exe
            if ((Test-Path (Join-Path $root ".runner")) -and (Test-Path (Join-Path $root "svc.cmd"))) {
                return $root
            }
        }
    }

    $candidates = @(
        "C:\actions-runner",
        "C:\github-actions-runner",
        (Join-Path $env:USERPROFILE "actions-runner"),
        (Join-Path $env:USERPROFILE "github-actions-runner"),
        (Join-Path $env:LOCALAPPDATA "actions-runner"),
        (Join-Path $env:LOCALAPPDATA "GitHubActionsRunner")
    ) | Select-Object -Unique

    foreach ($candidate in $candidates) {
        if ((Test-Path (Join-Path $candidate ".runner")) -and (Test-Path (Join-Path $candidate "svc.cmd"))) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw "No configured GitHub Actions runner was found. Pass -RunnerPath with the existing configured runner directory."
}

function Get-RunnerService {
    Get-Service |
        Where-Object { $_.Name -like "actions.runner.*" } |
        Select-Object -First 1
}

Assert-Administrator
$runnerRoot = Find-ConfiguredRunnerRoot -ExplicitPath $RunnerPath
Write-Host "Configured runner: $runnerRoot"

$service = Get-RunnerService
if (-not $service) {
    Write-Host "GitHub Actions runner is configured but is not installed as a Windows service."
    Push-Location $runnerRoot
    try {
        & (Join-Path $runnerRoot "svc.cmd") install
        if ($LASTEXITCODE -ne 0) {
            throw "svc.cmd install failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }

    $service = Get-RunnerService
    if (-not $service) {
        throw "Runner service was not created."
    }
}

$serviceName = $service.Name
Write-Host "Runner service: $serviceName"

Set-Service -Name $serviceName -StartupType Automatic

& sc.exe failure $serviceName reset= 86400 actions= restart/5000/restart/15000/restart/30000 | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Could not configure Service Control Manager recovery for $serviceName"
}
& sc.exe failureflag $serviceName 1 | Out-Null

$service = Get-Service -Name $serviceName
if ($service.Status -ne "Running") {
    Start-Service -Name $serviceName
    $service.WaitForStatus("Running", (New-TimeSpan -Seconds 30))
}

$service = Get-CimInstance Win32_Service -Filter ("Name='" + $serviceName.Replace("'","''") + "'")
Write-Host "GitHub Actions runner service hardened."
Write-Host ("State: " + $service.State)
Write-Host ("StartMode: " + $service.StartMode)
Write-Host "Recovery: restart after 5s / 15s / 30s"
Write-Host "The runner now starts independently of Windows sign-in."
