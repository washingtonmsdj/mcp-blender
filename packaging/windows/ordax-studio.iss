#ifndef StageDir
  #error StageDir must be provided by the build pipeline
#endif
#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif

#define AppName "ORDAX Dev"
#define AppPublisher "ORDAX"
#define AppExeName "ORDAX Dev.exe"
#define RuntimeExeName "ORDAX Runtime.exe"

[Setup]
AppId={{0D31F22D-8451-4CF4-9E34-F0D4D857F55F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\ORDAX Dev
DefaultGroupName=ORDAX
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=ORDAX-Dev-Setup-{#AppVersion}-x64
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=no
RestartApplications=no
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=ORDAX Dev installer
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Files]
Source: "{#StageDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
Type: files; Name: "{app}\ORDAX Studio.exe"
Type: filesandordirs; Name: "{app}\browser_extension"

[Icons]
Name: "{group}\ORDAX Dev"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{userdesktop}\ORDAX Dev"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho do ORDAX Dev na área de trabalho"; GroupDescription: "Atalhos adicionais:"; Flags: unchecked

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ORDAX Runtime"; ValueData: """{app}\{#RuntimeExeName}"""; Flags: uninsdeletevalue

[Run]
Filename: "{app}\redist\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Instalando Microsoft Edge WebView2..."; Flags: waituntilterminated skipifdoesntexist; Check: NeedsWebView2
Filename: "{app}\{#RuntimeExeName}"; Description: "Iniciar ORDAX Runtime"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#AppExeName}"; Description: "Abrir ORDAX Dev"; Flags: nowait postinstall skipifsilent

[Code]
const
  EVENT_MODIFY_STATE = $0002;
  SYNCHRONIZE = $00100000;

function OpenEvent(dwDesiredAccess: LongWord; bInheritHandle: Boolean; lpName: String): THandle;
  external 'OpenEventW@kernel32.dll stdcall';
function SetEvent(hEvent: THandle): Boolean;
  external 'SetEvent@kernel32.dll stdcall';
function CloseHandle(hObject: THandle): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';

function NeedsWebView2(): Boolean;
var
  WebViewPath: String;
begin
  WebViewPath := ExpandConstant('{pf32}\Microsoft\EdgeWebView\Application');
  Result := not DirExists(WebViewPath);
end;

function SignalShutdownEvent(const EventName: String): Boolean;
var
  EventHandle: THandle;
begin
  EventHandle := OpenEvent(EVENT_MODIFY_STATE, False, EventName);
  if EventHandle = 0 then
  begin
    Result := False;
    Exit;
  end;
  Result := SetEvent(EventHandle);
  CloseHandle(EventHandle);
end;

function WaitForShutdownEventGone(const EventName: String): Boolean;
var
  Attempt: Integer;
  EventHandle: THandle;
begin
  for Attempt := 1 to 50 do
  begin
    EventHandle := OpenEvent(SYNCHRONIZE, False, EventName);
    if EventHandle = 0 then
    begin
      Result := True;
      Exit;
    end;
    CloseHandle(EventHandle);
    Sleep(100);
  end;
  Result := False;
end;

function StopOrdaxProcess(const EventName, ExeName: String): Boolean;
var
  ResultCode: Integer;
  Started: Boolean;
begin
  { Current launchers expose a cooperative shutdown event. }
  if SignalShutdownEvent(EventName) then
  begin
    if WaitForShutdownEventGone(EventName) then
    begin
      Result := True;
      Exit;
    end;
  end;

  { Compatibility path for 0.3.0/0.3.1, which predate the shutdown event. }
  Started := Exec(
    ExpandConstant('{sys}\taskkill.exe'),
    '/F /T /IM "' + ExeName + '"',
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  );
  if not Started then
  begin
    Result := False;
    Exit;
  end;

  { taskkill returns 128 when no matching process exists. }
  Result := (ResultCode = 0) or (ResultCode = 128);
  if Result then
    Sleep(500);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  NeedsRestart := False;

  if not StopOrdaxProcess('Local\ORDAXStudioShutdown', '{#AppExeName}') then
  begin
    Result := 'Não foi possível encerrar o ORDAX Dev para atualizar os arquivos.';
    Exit;
  end;

  if not StopOrdaxProcess('Local\ORDAXRuntimeShutdown', '{#RuntimeExeName}') then
  begin
    Result := 'Não foi possível encerrar o ORDAX Runtime para atualizar os arquivos.';
    Exit;
  end;

  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    StopOrdaxProcess('Local\ORDAXStudioShutdown', '{#AppExeName}');
    StopOrdaxProcess('Local\ORDAXRuntimeShutdown', '{#RuntimeExeName}');
  end;
end;
