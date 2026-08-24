#ifndef MyAppVersion
  #define MyAppVersion "2.6.0"
#endif
#define MyAppName "MKV Muxing Batch GUI"
#define MyAppExeName "MKV Muxing Batch GUI.exe"
#define MyAppPublisher "MKV Muxing Batch GUI contributors"
#define MyAppURL "https://github.com/orphick/mkv-muxing-batch"
#define BuildRoot "..\.."

[Setup]
AppId={{D3E51D25-3990-4C69-A747-C63065995F12}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases/latest
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile={#BuildRoot}\LICENSE
OutputDir={#BuildRoot}\release
OutputBaseFilename=MKV.Muxing.Batch.GUI.x64.v{#MyAppVersion}.Qt6.Windows.Installer
SetupIconFile={#BuildRoot}\Resources\Icons\App.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#BuildRoot}\dist\MKV Muxing Batch GUI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
