param(
    [switch]$StartNow
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$startup = [Environment]::GetFolderPath("Startup")
$linkPath = Join-Path $startup "OrdaX Dev Agent.lnk"
$launcher = Join-Path $repoRoot "scripts\windows\ordax-agent-start.cmd"

if (-not (Test-Path $python)) {
    $basePython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $basePython) {
        throw "Python not found."
    }

    & $basePython.Source -m venv (Join-Path $repoRoot ".venv")
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create .venv."
    }
}

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }

& $python -m pip install -e $repoRoot
if ($LASTEXITCODE -ne 0) { throw "OrdaX Dev Agent install failed." }

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($linkPath)
$shortcut.TargetPath = $launcher
$shortcut.WorkingDirectory = $repoRoot
$shortcut.Description = "OrdaX Dev Agent - Unity, Blender, Git and diagnostics"
$shortcut.WindowStyle = 7
$shortcut.Save()

Write-Host "OrdaX Dev Agent installed."
Write-Host "Startup shortcut: $linkPath"
Write-Host "Local status endpoint: http://127.0.0.1:8765/status"
Write-Host ""
Write-Host "Supabase control plane becomes active after ORDAX_SUPABASE_URL and ORDAX_SUPABASE_KEY are configured."

if ($StartNow) {
    Start-Process -FilePath $launcher -WorkingDirectory $repoRoot -WindowStyle Minimized
}
