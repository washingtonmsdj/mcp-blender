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

function Read-GitValue([string[]]$Args) {
    $value = (& git -c core.fsmonitor=false -C $repoRootResolved @Args 2>$null)
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

    $beforeHead = Read-GitValue @("rev-parse", "HEAD")
    $beforeBranch = Read-GitValue @("rev-parse", "--abbrev-ref", "HEAD")
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

    $remoteHead = Read-GitValue @("rev-parse", $remoteRef)
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

        & $python -m compileall -q (Join-Path $repoRootResolved "mcp_blender_unity") (Join-Path $repoRootResolved "ordax_dev_agent")
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

while ($true) {
    try {
        [void](Invoke-SafeUpdate)
    } catch {
        Write-BootstrapLog "UPDATE_ERROR $($_.Exception.Message)"
    }

    if (-not (Test-Path $python)) {
        Write-BootstrapLog "LAUNCH_WAIT venv missing path=$python retry=$retrySeconds"
        Start-Sleep -Seconds $retrySeconds
        $retrySeconds = [Math]::Min($MaxRetrySeconds, $retrySeconds * 2)
        continue
    }

    & $python -m compileall -q (Join-Path $repoRootResolved "mcp_blender_unity") (Join-Path $repoRootResolved "ordax_dev_agent")
    if ($LASTEXITCODE -ne 0) {
        Write-BootstrapLog "LAUNCH_WAIT local compile failed retry=$retrySeconds"
        Start-Sleep -Seconds $retrySeconds
        $retrySeconds = [Math]::Min($MaxRetrySeconds, $retrySeconds * 2)
        continue
    }

    Write-BootstrapLog "AGENT_START repo=$repoRootResolved"
    & $python -m ordax_dev_agent.main
    $code = $LASTEXITCODE
    Write-BootstrapLog "AGENT_EXIT code=$code"

    if ($code -eq 0) {
        exit 0
    }
    if ($code -eq 42) {
        $retrySeconds = [Math]::Max(1, $InitialRetrySeconds)
        Start-Sleep -Seconds 2
        continue
    }

    Start-Sleep -Seconds $retrySeconds
    $retrySeconds = [Math]::Min($MaxRetrySeconds, $retrySeconds * 2)
}
