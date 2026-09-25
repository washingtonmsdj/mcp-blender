param(
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot,
    [string]$Branch = "main",
    [int]$InitialRetrySeconds = 10,
    [int]$MaxRetrySeconds = 300
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path (Join-Path $RepoRoot ".git"))) {
    throw "Managed OrdaX repository not found: $RepoRoot"
}

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$stateDir = Join-Path $env:LOCALAPPDATA "OrdaX\DevAgent"
$bootstrapDir = Join-Path $stateDir "bootstrap"
$policyScript = Join-Path $bootstrapDir "update_policy.py"
$logPath = Join-Path $bootstrapDir "bootstrap.log"
$python = Join-Path $repoRootResolved ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $bootstrapDir | Out-Null

function Write-BootstrapLog([string]$Message) {
    $stamp = [DateTime]::UtcNow.ToString("o")
    Add-Content -Path $logPath -Value "$stamp $Message" -Encoding UTF8
}

function Ensure-DevelopmentV2Settings {
    $tokenPath = Join-Path $stateDir "device-token.txt"
    $settingsPath = Join-Path $stateDir "agent-settings.json"
    $controlPlaneUrl = "https://eobcxuyvhkvdmkbaihwh.supabase.co"
    $identifyUrl = "$controlPlaneUrl/functions/v1/ordax-development-device-identify"

    if (-not (Test-Path $tokenPath -PathType Leaf)) {
        Write-BootstrapLog "V2_IDENTITY_SKIP device token missing"
        return $false
    }

    try {
        $token = (Get-Content $tokenPath -Raw -Encoding UTF8).Trim()
    } catch {
        Write-BootstrapLog "V2_IDENTITY_SKIP device token unreadable"
        return $false
    }
    if ($token.Length -lt 32 -or $token.Length -gt 512) {
        Write-BootstrapLog "V2_IDENTITY_SKIP device token length invalid"
        return $false
    }

    $settings = [pscustomobject]@{}
    if (Test-Path $settingsPath -PathType Leaf) {
        try {
            $settings = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
        } catch {
            Write-BootstrapLog "V2_IDENTITY_SKIP existing settings invalid"
            return $false
        }
        if (-not $settings) {
            $settings = [pscustomobject]@{}
        }
    }

    $protocol = if ($settings.PSObject.Properties["control_plane_protocol"]) {
        [string]$settings.control_plane_protocol
    } else { "" }
    $deviceId = if ($settings.PSObject.Properties["development_device_id"]) {
        [string]$settings.development_device_id
    } else { "" }
    $supabaseUrl = if ($settings.PSObject.Properties["supabase_url"]) {
        [string]$settings.supabase_url
    } else { "" }

    $needsIdentity = (
        $protocol -ne "development-v2" -or
        $deviceId -notmatch '^[0-9a-fA-F-]{36}
    $bootstrapSource = Join-Path $repoRootResolved "scripts\windows\ordax-agent-bootstrap.ps1"
    $policySource = Join-Path $repoRootResolved "ordax_dev_agent\update_policy.py"

    if (-not (Test-Path $bootstrapSource) -or -not (Test-Path $policySource)) {
        Write-BootstrapLog "SELF_REFRESH_SKIP candidate bootstrap source missing"
        return $false
    }

    try {
        $bootstrapText = Get-Content $bootstrapSource -Raw -Encoding UTF8
        [void][ScriptBlock]::Create($bootstrapText)
    } catch {
        Write-BootstrapLog "SELF_REFRESH_SKIP candidate bootstrap PowerShell does not parse: $($_.Exception.Message)"
        return $false
    }

    & $python -c "import ast,sys; ast.parse(open(sys.argv[1], encoding='utf-8').read())" $policySource
    if ($LASTEXITCODE -ne 0) {
        Write-BootstrapLog "SELF_REFRESH_SKIP candidate update policy does not parse"
        return $false
    }

    $bootstrapDestination = Join-Path $bootstrapDir "ordax-agent-bootstrap.ps1"
    $policyDestination = Join-Path $bootstrapDir "update_policy.py"
    $bootstrapTemp = "$bootstrapDestination.next"
    $policyTemp = "$policyDestination.next"

    Copy-Item -Force $bootstrapSource $bootstrapTemp
    Copy-Item -Force $policySource $policyTemp
    Move-Item -Force $bootstrapTemp $bootstrapDestination
    Move-Item -Force $policyTemp $policyDestination

    Write-BootstrapLog "SELF_REFRESH_OK"
    return $true
}

function Read-GitValue([string[]]$CommandArgs) {
    $value = (& git -c core.fsmonitor=false -C $repoRootResolved @CommandArgs 2>$null)
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    return (($value | Out-String).Trim())
}

function Restore-ManagedCheckout(
    [string]$BeforeHead,
    [string]$BeforeBranch,
    [bool]$RefreshInstall
) {
    Write-BootstrapLog "ROLLBACK head=$BeforeHead branch=$BeforeBranch"

    if ($BeforeBranch -and $BeforeBranch -ne "HEAD") {
        & git -c core.fsmonitor=false -C $repoRootResolved checkout -B $BeforeBranch $BeforeHead | Out-Null
    } else {
        & git -c core.fsmonitor=false -C $repoRootResolved checkout --detach $BeforeHead | Out-Null
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Could not restore managed checkout to $BeforeHead"
    }

    if ($RefreshInstall -and (Test-Path $python)) {
        & $python -m pip install -e $repoRootResolved | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Rollback restored Git but failed to restore editable install"
        }
    }
}

function Invoke-SafeUpdate {
    if (-not (Test-Path $python)) {
        Write-BootstrapLog "UPDATE_SKIP venv missing path=$python"
        return $false
    }
    if (-not (Test-Path $policyScript)) {
        Write-BootstrapLog "UPDATE_SKIP external update policy missing path=$policyScript"
        return $false
    }

    & $python $policyScript --check-clean $repoRootResolved | ForEach-Object {
        Write-BootstrapLog "PREFLIGHT $_"
    }
    $preflightCode = $LASTEXITCODE
    if ($preflightCode -eq 1) {
        Write-BootstrapLog "UPDATE_SKIP managed checkout has tracked changes"
        return $false
    }
    if ($preflightCode -ne 0) {
        Write-BootstrapLog "UPDATE_SKIP managed checkout preflight failed code=$preflightCode"
        return $false
    }

    $beforeHead = Read-GitValue -CommandArgs @("rev-parse", "HEAD")
    $beforeBranch = Read-GitValue -CommandArgs @("rev-parse", "--abbrev-ref", "HEAD")
    if (-not $beforeHead -or -not $beforeBranch) {
        Write-BootstrapLog "UPDATE_SKIP could not resolve current HEAD/branch"
        return $false
    }

    $remoteRef = "refs/remotes/origin/$Branch"
    $fetchRefspec = "refs/heads/${Branch}:$remoteRef"
    & git -c core.fsmonitor=false -C $repoRootResolved fetch --quiet origin $fetchRefspec
    if ($LASTEXITCODE -ne 0) {
        Write-BootstrapLog "UPDATE_SKIP fetch failed branch=$Branch"
        return $false
    }

    $remoteHead = Read-GitValue -CommandArgs @("rev-parse", $remoteRef)
    if (-not $remoteHead) {
        Write-BootstrapLog "UPDATE_SKIP remote head unavailable ref=$remoteRef"
        return $false
    }
    if ($remoteHead -eq $beforeHead) {
        return $false
    }

    & git -c core.fsmonitor=false -C $repoRootResolved merge-base --is-ancestor $beforeHead $remoteHead
    if ($LASTEXITCODE -ne 0) {
        Write-BootstrapLog "UPDATE_SKIP non-fast-forward before=$beforeHead remote=$remoteHead"
        return $false
    }

    & $python $policyScript --compare-install-contract $repoRootResolved --before-ref $beforeHead --after-ref $remoteRef |
        ForEach-Object { Write-BootstrapLog "INSTALL_CONTRACT $_" }
    $contractCode = $LASTEXITCODE
    if ($contractCode -gt 1) {
        Write-BootstrapLog "UPDATE_SKIP install contract comparison failed code=$contractCode"
        return $false
    }
    $refreshInstall = $contractCode -eq 1

    $switched = $false
    if ($beforeBranch -eq $Branch) {
        & git -c core.fsmonitor=false -C $repoRootResolved merge --ff-only --quiet $remoteRef
    } else {
        & git -c core.fsmonitor=false -C $repoRootResolved checkout -B $Branch $remoteRef
        $switched = $true
    }
    if ($LASTEXITCODE -ne 0) {
        Write-BootstrapLog "UPDATE_FAIL fast-forward/checkout failed"
        return $false
    }

    try {
        if ($refreshInstall) {
            & $python -m pip install -e $repoRootResolved
            if ($LASTEXITCODE -ne 0) {
                throw "editable install refresh failed"
            }
        }

        & $python -m compileall -q (Join-Path $repoRootResolved "mcp_blender_unity") (Join-Path $repoRootResolved "ordax_dev_agent") (Join-Path $repoRootResolved "ordax_device_agent")
        if ($LASTEXITCODE -ne 0) {
            throw "compile gate failed"
        }
    } catch {
        Restore-ManagedCheckout -BeforeHead $beforeHead -BeforeBranch $beforeBranch -RefreshInstall $refreshInstall
        Write-BootstrapLog "UPDATE_ROLLED_BACK reason=$($_.Exception.Message)"
        return $false
    }

    [void](Sync-ExternalBootstrapFromRepo)
    Write-BootstrapLog "UPDATE_OK before=$beforeHead after=$remoteHead install_refresh=$refreshInstall switched=$switched"
    return $true
}

$retrySeconds = [Math]::Max(1, $InitialRetrySeconds)
$needsSafeUpdate = $false

while ($true) {
    try {
        [void](Ensure-DevelopmentV2Settings)
    } catch {
        Write-BootstrapLog "V2_IDENTITY_ERROR $($_.Exception.GetType().Name)"
    }

    if (-not (Test-Path $python)) {
        Write-BootstrapLog "LAUNCH_WAIT venv missing path=$python retry=$retrySeconds"
        Start-Sleep -Seconds $retrySeconds
        $retrySeconds = [Math]::Min($MaxRetrySeconds, $retrySeconds * 2)
        continue
    }

    # Bring the local health/control plane up first. The previous bootstrap ran
    # repository preflight/update work before starting the agent; on this host
    # that work can stall for minutes and leave the Scheduled Task "Running"
    # while port 8765 is unavailable. Safe update now happens only between
    # agent runs, never in front of initial health.
    Write-BootstrapLog "LAUNCH_READY repo=$repoRootResolved"
    Write-BootstrapLog "AGENT_START repo=$repoRootResolved"
    & $python -m ordax_dev_agent.main
    $code = $LASTEXITCODE
    Write-BootstrapLog "AGENT_EXIT code=$code"

    # Exit code 42 is emitted only after agent.update has already completed
    # the guarded fetch/fast-forward/install-contract check itself. Repeating
    # Invoke-SafeUpdate here causes a second network fetch while the control
    # plane is offline, which unnecessarily stretches restart time.
    $needsSafeUpdate = $code -ne 42
    if ($code -eq 42) {
        $retrySeconds = [Math]::Max(1, $InitialRetrySeconds)
        Write-BootstrapLog "AGENT_RESTART update-complete skip-duplicate-safe-update"
    }

    if ($needsSafeUpdate) {
        try {
            [void](Invoke-SafeUpdate)
        } catch {
            Write-BootstrapLog "UPDATE_ERROR $($_.Exception.Message)"
        }
        $needsSafeUpdate = $false
    }

    if ($code -eq 0) {
        # A genuine task stop terminates this bootstrap process itself. If the
        # child agent returns zero while the bootstrap is still alive, relaunch.
        Write-BootstrapLog "AGENT_RESTART clean-exit code=0 retry=$retrySeconds"
        Start-Sleep -Seconds $retrySeconds
        $retrySeconds = [Math]::Min($MaxRetrySeconds, $retrySeconds * 2)
        continue
    }
    if ($code -eq 42) {
        Start-Sleep -Seconds 2
        continue
    }

    Start-Sleep -Seconds $retrySeconds
    $retrySeconds = [Math]::Min($MaxRetrySeconds, $retrySeconds * 2)
}
 -or
        $supabaseUrl.TrimEnd("/") -ne $controlPlaneUrl
    )

    if ($needsIdentity) {
        try {
            $identity = Invoke-RestMethod -Method Post -Uri $identifyUrl -Headers @{
                "X-Ordax-Device-Token" = $token
            } -ContentType "application/json" -Body "{}" -TimeoutSec 15
        } catch {
            Write-BootstrapLog "V2_IDENTITY_RETRY identify request failed"
            return $false
        }

        $resolvedId = if ($identity -and $identity.device_id) {
            [string]$identity.device_id
        } else { "" }
        if (-not $identity.ok -or $identity.protocol -ne "development-v2" -or
            $resolvedId -notmatch '^[0-9a-fA-F-]{36}
    $bootstrapSource = Join-Path $repoRootResolved "scripts\windows\ordax-agent-bootstrap.ps1"
    $policySource = Join-Path $repoRootResolved "ordax_dev_agent\update_policy.py"

    if (-not (Test-Path $bootstrapSource) -or -not (Test-Path $policySource)) {
        Write-BootstrapLog "SELF_REFRESH_SKIP candidate bootstrap source missing"
        return $false
    }

    try {
        $bootstrapText = Get-Content $bootstrapSource -Raw -Encoding UTF8
        [void][ScriptBlock]::Create($bootstrapText)
    } catch {
        Write-BootstrapLog "SELF_REFRESH_SKIP candidate bootstrap PowerShell does not parse: $($_.Exception.Message)"
        return $false
    }

    & $python -c "import ast,sys; ast.parse(open(sys.argv[1], encoding='utf-8').read())" $policySource
    if ($LASTEXITCODE -ne 0) {
        Write-BootstrapLog "SELF_REFRESH_SKIP candidate update policy does not parse"
        return $false
    }

    $bootstrapDestination = Join-Path $bootstrapDir "ordax-agent-bootstrap.ps1"
    $policyDestination = Join-Path $bootstrapDir "update_policy.py"
    $bootstrapTemp = "$bootstrapDestination.next"
    $policyTemp = "$policyDestination.next"

    Copy-Item -Force $bootstrapSource $bootstrapTemp
    Copy-Item -Force $policySource $policyTemp
    Move-Item -Force $bootstrapTemp $bootstrapDestination
    Move-Item -Force $policyTemp $policyDestination

    Write-BootstrapLog "SELF_REFRESH_OK"
    return $true
}

function Read-GitValue([string[]]$CommandArgs) {
    $value = (& git -c core.fsmonitor=false -C $repoRootResolved @CommandArgs 2>$null)
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    return (($value | Out-String).Trim())
}

function Restore-ManagedCheckout(
    [string]$BeforeHead,
    [string]$BeforeBranch,
    [bool]$RefreshInstall
) {
    Write-BootstrapLog "ROLLBACK head=$BeforeHead branch=$BeforeBranch"

    if ($BeforeBranch -and $BeforeBranch -ne "HEAD") {
        & git -c core.fsmonitor=false -C $repoRootResolved checkout -B $BeforeBranch $BeforeHead | Out-Null
    } else {
        & git -c core.fsmonitor=false -C $repoRootResolved checkout --detach $BeforeHead | Out-Null
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Could not restore managed checkout to $BeforeHead"
    }

    if ($RefreshInstall -and (Test-Path $python)) {
        & $python -m pip install -e $repoRootResolved | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Rollback restored Git but failed to restore editable install"
        }
    }
}

function Invoke-SafeUpdate {
    if (-not (Test-Path $python)) {
        Write-BootstrapLog "UPDATE_SKIP venv missing path=$python"
        return $false
    }
    if (-not (Test-Path $policyScript)) {
        Write-BootstrapLog "UPDATE_SKIP external update policy missing path=$policyScript"
        return $false
    }

    & $python $policyScript --check-clean $repoRootResolved | ForEach-Object {
        Write-BootstrapLog "PREFLIGHT $_"
    }
    $preflightCode = $LASTEXITCODE
    if ($preflightCode -eq 1) {
        Write-BootstrapLog "UPDATE_SKIP managed checkout has tracked changes"
        return $false
    }
    if ($preflightCode -ne 0) {
        Write-BootstrapLog "UPDATE_SKIP managed checkout preflight failed code=$preflightCode"
        return $false
    }

    $beforeHead = Read-GitValue -CommandArgs @("rev-parse", "HEAD")
    $beforeBranch = Read-GitValue -CommandArgs @("rev-parse", "--abbrev-ref", "HEAD")
    if (-not $beforeHead -or -not $beforeBranch) {
        Write-BootstrapLog "UPDATE_SKIP could not resolve current HEAD/branch"
        return $false
    }

    $remoteRef = "refs/remotes/origin/$Branch"
    $fetchRefspec = "refs/heads/${Branch}:$remoteRef"
    & git -c core.fsmonitor=false -C $repoRootResolved fetch --quiet origin $fetchRefspec
    if ($LASTEXITCODE -ne 0) {
        Write-BootstrapLog "UPDATE_SKIP fetch failed branch=$Branch"
        return $false
    }

    $remoteHead = Read-GitValue -CommandArgs @("rev-parse", $remoteRef)
    if (-not $remoteHead) {
        Write-BootstrapLog "UPDATE_SKIP remote head unavailable ref=$remoteRef"
        return $false
    }
    if ($remoteHead -eq $beforeHead) {
        return $false
    }

    & git -c core.fsmonitor=false -C $repoRootResolved merge-base --is-ancestor $beforeHead $remoteHead
    if ($LASTEXITCODE -ne 0) {
        Write-BootstrapLog "UPDATE_SKIP non-fast-forward before=$beforeHead remote=$remoteHead"
        return $false
    }

    & $python $policyScript --compare-install-contract $repoRootResolved --before-ref $beforeHead --after-ref $remoteRef |
        ForEach-Object { Write-BootstrapLog "INSTALL_CONTRACT $_" }
    $contractCode = $LASTEXITCODE
    if ($contractCode -gt 1) {
        Write-BootstrapLog "UPDATE_SKIP install contract comparison failed code=$contractCode"
        return $false
    }
    $refreshInstall = $contractCode -eq 1

    $switched = $false
    if ($beforeBranch -eq $Branch) {
        & git -c core.fsmonitor=false -C $repoRootResolved merge --ff-only --quiet $remoteRef
    } else {
        & git -c core.fsmonitor=false -C $repoRootResolved checkout -B $Branch $remoteRef
        $switched = $true
    }
    if ($LASTEXITCODE -ne 0) {
        Write-BootstrapLog "UPDATE_FAIL fast-forward/checkout failed"
        return $false
    }

    try {
        if ($refreshInstall) {
            & $python -m pip install -e $repoRootResolved
            if ($LASTEXITCODE -ne 0) {
                throw "editable install refresh failed"
            }
        }

        & $python -m compileall -q (Join-Path $repoRootResolved "mcp_blender_unity") (Join-Path $repoRootResolved "ordax_dev_agent") (Join-Path $repoRootResolved "ordax_device_agent")
        if ($LASTEXITCODE -ne 0) {
            throw "compile gate failed"
        }
    } catch {
        Restore-ManagedCheckout -BeforeHead $beforeHead -BeforeBranch $beforeBranch -RefreshInstall $refreshInstall
        Write-BootstrapLog "UPDATE_ROLLED_BACK reason=$($_.Exception.Message)"
        return $false
    }

    [void](Sync-ExternalBootstrapFromRepo)
    Write-BootstrapLog "UPDATE_OK before=$beforeHead after=$remoteHead install_refresh=$refreshInstall switched=$switched"
    return $true
}

$retrySeconds = [Math]::Max(1, $InitialRetrySeconds)
$needsSafeUpdate = $false

while ($true) {
    if (-not (Test-Path $python)) {
        Write-BootstrapLog "LAUNCH_WAIT venv missing path=$python retry=$retrySeconds"
        Start-Sleep -Seconds $retrySeconds
        $retrySeconds = [Math]::Min($MaxRetrySeconds, $retrySeconds * 2)
        continue
    }

    # Bring the local health/control plane up first. The previous bootstrap ran
    # repository preflight/update work before starting the agent; on this host
    # that work can stall for minutes and leave the Scheduled Task "Running"
    # while port 8765 is unavailable. Safe update now happens only between
    # agent runs, never in front of initial health.
    Write-BootstrapLog "LAUNCH_READY repo=$repoRootResolved"
    Write-BootstrapLog "AGENT_START repo=$repoRootResolved"
    & $python -m ordax_dev_agent.main
    $code = $LASTEXITCODE
    Write-BootstrapLog "AGENT_EXIT code=$code"

    # Exit code 42 is emitted only after agent.update has already completed
    # the guarded fetch/fast-forward/install-contract check itself. Repeating
    # Invoke-SafeUpdate here causes a second network fetch while the control
    # plane is offline, which unnecessarily stretches restart time.
    $needsSafeUpdate = $code -ne 42
    if ($code -eq 42) {
        $retrySeconds = [Math]::Max(1, $InitialRetrySeconds)
        Write-BootstrapLog "AGENT_RESTART update-complete skip-duplicate-safe-update"
    }

    if ($needsSafeUpdate) {
        try {
            [void](Invoke-SafeUpdate)
        } catch {
            Write-BootstrapLog "UPDATE_ERROR $($_.Exception.Message)"
        }
        $needsSafeUpdate = $false
    }

    if ($code -eq 0) {
        # A genuine task stop terminates this bootstrap process itself. If the
        # child agent returns zero while the bootstrap is still alive, relaunch.
        Write-BootstrapLog "AGENT_RESTART clean-exit code=0 retry=$retrySeconds"
        Start-Sleep -Seconds $retrySeconds
        $retrySeconds = [Math]::Min($MaxRetrySeconds, $retrySeconds * 2)
        continue
    }
    if ($code -eq 42) {
        Start-Sleep -Seconds 2
        continue
    }

    Start-Sleep -Seconds $retrySeconds
    $retrySeconds = [Math]::Min($MaxRetrySeconds, $retrySeconds * 2)
}
) {
            Write-BootstrapLog "V2_IDENTITY_RETRY identify response invalid"
            return $false
        }

        $settings | Add-Member -NotePropertyName supabase_url -NotePropertyValue $controlPlaneUrl -Force
        $settings | Add-Member -NotePropertyName control_plane_protocol -NotePropertyValue "development-v2" -Force
        $settings | Add-Member -NotePropertyName development_device_id -NotePropertyValue $resolvedId -Force
        $deviceId = $resolvedId
    }

    $projectRoot = Join-Path $env:USERPROFILE "Documents\github\cerco-no-interior-mvp"
    if (Test-Path $projectRoot -PathType Container) {
        if (-not $settings.PSObject.Properties["projects"] -or -not $settings.projects) {
            $settings | Add-Member -NotePropertyName projects -NotePropertyValue ([pscustomobject]@{}) -Force
        }
        $projectConfig = [pscustomobject]@{
            path = $projectRoot
            apps = @("blender")
            blender = [pscustomobject]@{
                scripts_dir = "automation/blender"
            }
        }
        $settings.projects | Add-Member -NotePropertyName "cerco-no-interior-mvp" -NotePropertyValue $projectConfig -Force
    }

    $tempSettings = "$settingsPath.next"
    $settingsJson = $settings | ConvertTo-Json -Depth 12
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($tempSettings, $settingsJson, $utf8NoBom)
    Move-Item -Force $tempSettings $settingsPath

    Write-BootstrapLog "V2_IDENTITY_READY device=$deviceId"
    return $true
}

function Sync-ExternalBootstrapFromRepo {
    $bootstrapSource = Join-Path $repoRootResolved "scripts\windows\ordax-agent-bootstrap.ps1"
    $policySource = Join-Path $repoRootResolved "ordax_dev_agent\update_policy.py"

    if (-not (Test-Path $bootstrapSource) -or -not (Test-Path $policySource)) {
        Write-BootstrapLog "SELF_REFRESH_SKIP candidate bootstrap source missing"
        return $false
    }

    try {
        $bootstrapText = Get-Content $bootstrapSource -Raw -Encoding UTF8
        [void][ScriptBlock]::Create($bootstrapText)
    } catch {
        Write-BootstrapLog "SELF_REFRESH_SKIP candidate bootstrap PowerShell does not parse: $($_.Exception.Message)"
        return $false
    }

    & $python -c "import ast,sys; ast.parse(open(sys.argv[1], encoding='utf-8').read())" $policySource
    if ($LASTEXITCODE -ne 0) {
        Write-BootstrapLog "SELF_REFRESH_SKIP candidate update policy does not parse"
        return $false
    }

    $bootstrapDestination = Join-Path $bootstrapDir "ordax-agent-bootstrap.ps1"
    $policyDestination = Join-Path $bootstrapDir "update_policy.py"
    $bootstrapTemp = "$bootstrapDestination.next"
    $policyTemp = "$policyDestination.next"

    Copy-Item -Force $bootstrapSource $bootstrapTemp
    Copy-Item -Force $policySource $policyTemp
    Move-Item -Force $bootstrapTemp $bootstrapDestination
    Move-Item -Force $policyTemp $policyDestination

    Write-BootstrapLog "SELF_REFRESH_OK"
    return $true
}

function Read-GitValue([string[]]$CommandArgs) {
    $value = (& git -c core.fsmonitor=false -C $repoRootResolved @CommandArgs 2>$null)
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    return (($value | Out-String).Trim())
}

function Restore-ManagedCheckout(
    [string]$BeforeHead,
    [string]$BeforeBranch,
    [bool]$RefreshInstall
) {
    Write-BootstrapLog "ROLLBACK head=$BeforeHead branch=$BeforeBranch"

    if ($BeforeBranch -and $BeforeBranch -ne "HEAD") {
        & git -c core.fsmonitor=false -C $repoRootResolved checkout -B $BeforeBranch $BeforeHead | Out-Null
    } else {
        & git -c core.fsmonitor=false -C $repoRootResolved checkout --detach $BeforeHead | Out-Null
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Could not restore managed checkout to $BeforeHead"
    }

    if ($RefreshInstall -and (Test-Path $python)) {
        & $python -m pip install -e $repoRootResolved | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Rollback restored Git but failed to restore editable install"
        }
    }
}

function Invoke-SafeUpdate {
    if (-not (Test-Path $python)) {
        Write-BootstrapLog "UPDATE_SKIP venv missing path=$python"
        return $false
    }
    if (-not (Test-Path $policyScript)) {
        Write-BootstrapLog "UPDATE_SKIP external update policy missing path=$policyScript"
        return $false
    }

    & $python $policyScript --check-clean $repoRootResolved | ForEach-Object {
        Write-BootstrapLog "PREFLIGHT $_"
    }
    $preflightCode = $LASTEXITCODE
    if ($preflightCode -eq 1) {
        Write-BootstrapLog "UPDATE_SKIP managed checkout has tracked changes"
        return $false
    }
    if ($preflightCode -ne 0) {
        Write-BootstrapLog "UPDATE_SKIP managed checkout preflight failed code=$preflightCode"
        return $false
    }

    $beforeHead = Read-GitValue -CommandArgs @("rev-parse", "HEAD")
    $beforeBranch = Read-GitValue -CommandArgs @("rev-parse", "--abbrev-ref", "HEAD")
    if (-not $beforeHead -or -not $beforeBranch) {
        Write-BootstrapLog "UPDATE_SKIP could not resolve current HEAD/branch"
        return $false
    }

    $remoteRef = "refs/remotes/origin/$Branch"
    $fetchRefspec = "refs/heads/${Branch}:$remoteRef"
    & git -c core.fsmonitor=false -C $repoRootResolved fetch --quiet origin $fetchRefspec
    if ($LASTEXITCODE -ne 0) {
        Write-BootstrapLog "UPDATE_SKIP fetch failed branch=$Branch"
        return $false
    }

    $remoteHead = Read-GitValue -CommandArgs @("rev-parse", $remoteRef)
    if (-not $remoteHead) {
        Write-BootstrapLog "UPDATE_SKIP remote head unavailable ref=$remoteRef"
        return $false
    }
    if ($remoteHead -eq $beforeHead) {
        return $false
    }

    & git -c core.fsmonitor=false -C $repoRootResolved merge-base --is-ancestor $beforeHead $remoteHead
    if ($LASTEXITCODE -ne 0) {
        Write-BootstrapLog "UPDATE_SKIP non-fast-forward before=$beforeHead remote=$remoteHead"
        return $false
    }

    & $python $policyScript --compare-install-contract $repoRootResolved --before-ref $beforeHead --after-ref $remoteRef |
        ForEach-Object { Write-BootstrapLog "INSTALL_CONTRACT $_" }
    $contractCode = $LASTEXITCODE
    if ($contractCode -gt 1) {
        Write-BootstrapLog "UPDATE_SKIP install contract comparison failed code=$contractCode"
        return $false
    }
    $refreshInstall = $contractCode -eq 1

    $switched = $false
    if ($beforeBranch -eq $Branch) {
        & git -c core.fsmonitor=false -C $repoRootResolved merge --ff-only --quiet $remoteRef
    } else {
        & git -c core.fsmonitor=false -C $repoRootResolved checkout -B $Branch $remoteRef
        $switched = $true
    }
    if ($LASTEXITCODE -ne 0) {
        Write-BootstrapLog "UPDATE_FAIL fast-forward/checkout failed"
        return $false
    }

    try {
        if ($refreshInstall) {
            & $python -m pip install -e $repoRootResolved
            if ($LASTEXITCODE -ne 0) {
                throw "editable install refresh failed"
            }
        }

        & $python -m compileall -q (Join-Path $repoRootResolved "mcp_blender_unity") (Join-Path $repoRootResolved "ordax_dev_agent") (Join-Path $repoRootResolved "ordax_device_agent")
        if ($LASTEXITCODE -ne 0) {
            throw "compile gate failed"
        }
    } catch {
        Restore-ManagedCheckout -BeforeHead $beforeHead -BeforeBranch $beforeBranch -RefreshInstall $refreshInstall
        Write-BootstrapLog "UPDATE_ROLLED_BACK reason=$($_.Exception.Message)"
        return $false
    }

    [void](Sync-ExternalBootstrapFromRepo)
    Write-BootstrapLog "UPDATE_OK before=$beforeHead after=$remoteHead install_refresh=$refreshInstall switched=$switched"
    return $true
}

$retrySeconds = [Math]::Max(1, $InitialRetrySeconds)
$needsSafeUpdate = $false

while ($true) {
    if (-not (Test-Path $python)) {
        Write-BootstrapLog "LAUNCH_WAIT venv missing path=$python retry=$retrySeconds"
        Start-Sleep -Seconds $retrySeconds
        $retrySeconds = [Math]::Min($MaxRetrySeconds, $retrySeconds * 2)
        continue
    }

    # Bring the local health/control plane up first. The previous bootstrap ran
    # repository preflight/update work before starting the agent; on this host
    # that work can stall for minutes and leave the Scheduled Task "Running"
    # while port 8765 is unavailable. Safe update now happens only between
    # agent runs, never in front of initial health.
    Write-BootstrapLog "LAUNCH_READY repo=$repoRootResolved"
    Write-BootstrapLog "AGENT_START repo=$repoRootResolved"
    & $python -m ordax_dev_agent.main
    $code = $LASTEXITCODE
    Write-BootstrapLog "AGENT_EXIT code=$code"

    # Exit code 42 is emitted only after agent.update has already completed
    # the guarded fetch/fast-forward/install-contract check itself. Repeating
    # Invoke-SafeUpdate here causes a second network fetch while the control
    # plane is offline, which unnecessarily stretches restart time.
    $needsSafeUpdate = $code -ne 42
    if ($code -eq 42) {
        $retrySeconds = [Math]::Max(1, $InitialRetrySeconds)
        Write-BootstrapLog "AGENT_RESTART update-complete skip-duplicate-safe-update"
    }

    if ($needsSafeUpdate) {
        try {
            [void](Invoke-SafeUpdate)
        } catch {
            Write-BootstrapLog "UPDATE_ERROR $($_.Exception.Message)"
        }
        $needsSafeUpdate = $false
    }

    if ($code -eq 0) {
        # A genuine task stop terminates this bootstrap process itself. If the
        # child agent returns zero while the bootstrap is still alive, relaunch.
        Write-BootstrapLog "AGENT_RESTART clean-exit code=0 retry=$retrySeconds"
        Start-Sleep -Seconds $retrySeconds
        $retrySeconds = [Math]::Min($MaxRetrySeconds, $retrySeconds * 2)
        continue
    }
    if ($code -eq 42) {
        Start-Sleep -Seconds 2
        continue
    }

    Start-Sleep -Seconds $retrySeconds
    $retrySeconds = [Math]::Min($MaxRetrySeconds, $retrySeconds * 2)
}
