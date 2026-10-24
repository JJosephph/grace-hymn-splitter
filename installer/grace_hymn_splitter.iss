; 恩典歌谱转换PPT大图 - Windows 安装程序
; 由 build_windows.ps1 调用 Inno Setup 编译。

#define MyAppName "恩典歌谱转换PPT大图"
#define MyAppSubtitle "恩典简谱分段转换"
#define MyAppPublisher "WangYufan"
#define MyAppEmail "yufan14710@gmail.com"
#define MyAppURL "https://github.com/JJosephph/grace-hymn-splitter"
#define MyAppExeName "GraceHymnSplitter.exe"

#ifndef MyAppVersion
  #define MyAppVersion "0.2.4"
#endif

[Setup]
AppId={{B27C5B18-6E5F-4C35-9C4E-58F0E9B4D7A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppContact={#MyAppEmail}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} 安装程序
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCopyright=Copyright (C) 2026 WangYufan
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
AppendDefaultDirName=yes
UsePreviousAppDir=yes
DirExistsWarning=auto
OutputDir=..\release
OutputBaseFilename=GraceHymnSplitter-v{#MyAppVersion}-setup-win64
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\assets\branding\logo.ico
WizardSmallImageFile=..\assets\branding\logo-small.png
LicenseFile=install-info.zh-CN.txt
InfoAfterFile=install-finish.zh-CN.txt

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "install-info.zh-CN.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "install-finish.zh-CN.txt"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\输出"; Flags: uninsneveruninstall

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function NextButtonClick(CurPageID: Integer): Boolean;
var
  SelectedDir: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    SelectedDir := RemoveBackslashUnlessRoot(WizardForm.DirEdit.Text);
    // 用户直接选择磁盘根目录时，自动建立独立产品目录。
    if (Length(SelectedDir) = 3) and (SelectedDir[2] = ':') and (SelectedDir[3] = '\') then
      WizardForm.DirEdit.Text := AddBackslash(SelectedDir) + ExpandConstant('{#MyAppName}');
  end;
end;
