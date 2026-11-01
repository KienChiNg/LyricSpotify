; Inno Setup: tạo bản cài đặt LyricSpotify-Setup.exe cho mục Release trên GitHub.
; Build: build.bat (tự gọi), hoặc: ISCC.exe installer.iss  (cần dist\LyricSpotify.exe đã build)

#define AppName "Lyric Spotify"
#define AppVersion "1.0.0"
#define AppExe "LyricSpotify.exe"
#define AppPublisher "KienChiNg"
#define AppURL "https://github.com/KienChiNg/LyricSpotify"

[Setup]
InfoAfterFile=installer\after-install.txt
AppId={{6C1F7F2E-6B7A-4C55-9A0B-3E6E2B8C4D11}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
DefaultDirName={localappdata}\Programs\LyricSpotify
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; cài cho người dùng hiện tại: không cần quyền Admin
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=LyricSpotify-Setup-{#AppVersion}
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; đóng app đang chạy khi cài bản mới / gỡ cài đặt
CloseApplications=yes

[Languages]
Name: "vietnamese"; MessagesFile: "installer\Vietnamese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
vietnamese.StartupTask=Tự mở {#AppName} khi khởi động Windows
english.StartupTask=Start {#AppName} when Windows starts

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startup"; Description: "{cm:StartupTask}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Dirs]
; thư mục lời bài hát nằm cạnh app, người dùng ghi được
Name: "{app}\lyrics"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; tắt app trước khi gỡ (nếu đang chạy)
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#AppExe}"; Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
; phần AI tải thêm (vài GB) và công cụ tải nằm ngoài thư mục cài -> xoá cùng khi gỡ
Type: filesandordirs; Name: "{localappdata}\LyricSpotify"
