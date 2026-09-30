param(
    [switch]$NoLaunch,
    [switch]$DesktopShortcut,
    [switch]$NonInteractive
)
$ErrorActionPreference = 'Stop'
$SourceRepo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$SetupScript = Join-Path $SourceRepo 'scripts\windows\ordax-device-agent-setup.ps1'
$StateDir = Join-Path $env:LOCALAPPDATA 'OrdaX\DevAgent'
$ManagedRepo = Join-Path $StateDir 'src'
$TaskName = 'OrdaX Dev Agent'
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    $setupArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$SetupScript)
    if ($NonInteractive) { $setupArgs += '-NonInteractive' }
    & powershell.exe @setupArgs
    if ($LASTEXITCODE -ne 0) { throw 'ORDAX_DEVICE_AGENT_SETUP_FAILED' }
}
if (-not (Test-Path (Join-Path $ManagedRepo '.git'))) { throw "ORDAX managed runtime is missing: $ManagedRepo" }
$Pythonw = Join-Path $ManagedRepo '.venv\Scripts\pythonw.exe'
if (-not (Test-Path $Pythonw)) { throw "ORDAX Studio runtime is missing: $Pythonw" }
$Programs = [Environment]::GetFolderPath('Programs')
$OrdaxMenu = Join-Path $Programs 'ORDAX'
New-Item -ItemType Directory -Force -Path $OrdaxMenu | Out-Null
$Shell = New-Object -ComObject WScript.Shell
function New-OrdaxShortcut([string]$Path, [string]$Module, [string]$Description) {
    $Shortcut = $Shell.CreateShortcut($Path)
    $Shortcut.TargetPath = $Pythonw
    $Shortcut.Arguments = "-m $Module"
    $Shortcut.WorkingDirectory = $ManagedRepo
    $Shortcut.Description = $Description
    $Shortcut.Save()
}
$StartMenuLink = Join-Path $OrdaxMenu 'ORDAX Studio.lnk'
$ChatGPTLink = Join-Path $OrdaxMenu 'Conectar ChatGPT.lnk'
New-OrdaxShortcut $StartMenuLink 'ordax_studio.web_desktop' 'ORDAX Studio'
New-OrdaxShortcut $ChatGPTLink 'ordax_studio.openai_tunnel_ui' 'Conectar esta estação ORDAX ao ChatGPT'
if ($DesktopShortcut) {
    New-OrdaxShortcut (Join-Path ([Environment]::GetFolderPath('Desktop')) 'ORDAX Studio.lnk') 'ordax_studio.web_desktop' 'ORDAX Studio'
}
$StudioState = Join-Path $env:LOCALAPPDATA 'OrdaX\Studio'
New-Item -ItemType Directory -Force -Path $StudioState | Out-Null
@{
    installed_at=[DateTimeOffset]::UtcNow.ToString('o')
    runtime=$ManagedRepo
    start_menu=$StartMenuLink
    chatgpt_connector=$ChatGPTLink
    background_task=$TaskName
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $StudioState 'installation.json') -Encoding UTF8
if (-not $NoLaunch) {
    Start-Process -FilePath $Pythonw -ArgumentList @('-m','ordax_studio.web_desktop') -WorkingDirectory $ManagedRepo
}
Write-Output 'ORDAX_STUDIO=INSTALLED'
Write-Output ("START_MENU=" + $StartMenuLink)
Write-Output ("CHATGPT_CONNECTOR=" + $ChatGPTLink)
Write-Output ("BACKGROUND_TASK=" + $TaskName)
