#ifndef StageDir
  #error StageDir must be provided by the build pipeline
#endif
#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif

#define AppName "ORDAX Studio"
#define AppPublisher "ORDAX"
#define AppExeName "ORDAX Studio.exe"
#define RuntimeExeName "ORDAX Runtime.exe"

[Setup]
AppId={{0D31F22D-8451-4CF4-9E34-F0D4D857F55F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\ORDAX Studio
DefaultGroupName=ORDAX
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=ORDAX-Studio-Setup-{#AppVersion}-x64
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=ORDAX Studio installer
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Files]
Source: "{#StageDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ORDAX Studio"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{userdesktop}\ORDAX Studio"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho do ORDAX Studio na área de trabalho"; GroupDescription: "Atalhos adicionais:"; Flags: unchecked

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ORDAX Runtime"; ValueData: """{app}\{#RuntimeExeName}"""; Flags: uninsdeletevalue

[Run]
Filename: "{app}\redist\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Validando Microsoft Edge WebView2..."; Flags: waituntilterminated skipifdoesntexist
Filename: "{app}\{#RuntimeExeName}"; Description: "Iniciar ORDAX Runtime"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#AppExeName}"; Description: "Abrir ORDAX Studio"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM ""{#RuntimeExeName}"""; Flags: runhidden waituntilterminated; RunOnceId: "StopOrdaxRuntime"
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM ""{#AppExeName}"""; Flags: runhidden waituntilterminated; RunOnceId: "StopOrdaxStudio"
