; Values must match core/identity.py (enforced by tests/test_v8_identity.py).
#define MyAppName "JARVIS V8"
#define MyAppVersion "8.0.0"
#define MyAppPublisher "Reda Benyassek"
#define MyAppExeName "JARVIS V8.exe"

[Setup]
AppId={{8E5A1C47-3D2B-4F60-9A8E-0C8D2F7B8008}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=JARVIS V8 Personal Intelligence
VersionInfoCopyright=Copyright (C) 2026 Reda Benyassek
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=release
OutputBaseFilename=JARVIS-V8-Setup
SetupIconFile=jarvis.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "dist\JARVIS V8\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\JARVIS V8"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\JARVIS V8"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{userstartup}\JARVIS V8"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--background"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch JARVIS V8"; Flags: nowait postinstall skipifsilent
