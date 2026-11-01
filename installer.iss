; Inno Setup: tạo bản cài đặt LyricSpotify-Setup.exe cho mục Release trên GitHub.
; Build: build.bat (tự gọi), hoặc: ISCC.exe installer.iss  (cần dist\LyricSpotify.exe đã build)

#define AppName "Lyric Spotify"
#define AppVersion "1.0.1"
#define AppExe "LyricSpotify.exe"
#define AppPublisher "KienChiNg"
#define AppURL "https://github.com/KienChiNg/LyricSpotify"

[Setup]
InfoAfterFile=installer\after-install.txt
#ifdef TestBuild
AppId={{6C1F7F2E-0000-0000-0000-7E57B0117E57}
#else
AppId={{6C1F7F2E-6B7A-4C55-9A0B-3E6E2B8C4D11}
#endif
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
vietnamese.AiGroup=AI chép lời khi không tìm thấy lời (tuỳ chọn, cần card NVIDIA, có thể tải sau trong app):
english.AiGroup=AI lyrics transcription when no lyrics are found (optional, needs an NVIDIA GPU, can be added later in the app):
vietnamese.AiTask=Tải phần AI chép lời (~3 GB + mô hình ~1.6 GB)
english.AiTask=Download the AI transcription add-on (~3 GB + ~1.6 GB model)
vietnamese.DemucsTask=Kèm tách giọng hát Demucs để chép chính xác hơn (thêm ~2.5 GB)
english.DemucsTask=Include Demucs vocal separation for better accuracy (+~2.5 GB)
vietnamese.AiStatus=Đang tải phần AI chép lời (có thể mất vài chục phút)...
english.AiStatus=Downloading the AI transcription add-on (may take a while)...

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startup"; Description: "{cm:StartupTask}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
; chỉ hiện ô tải khi máy chưa có phần đó (vd: cài bản mới đè lên bản cũ thì không tải lại)
Name: "ai"; Description: "{cm:AiTask}"; GroupDescription: "{cm:AiGroup}"; Flags: unchecked; Check: not AiInstalled
Name: "demucs"; Description: "{cm:DemucsTask}"; GroupDescription: "{cm:AiGroup}"; Flags: unchecked; Check: not DemucsInstalled

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
; bản cũ có cài kèm README.md (hiện sau khi cài) -> dọn đi khi cập nhật
Type: files; Name: "{app}\README.md"

[Dirs]
; thư mục lời bài hát nằm cạnh app, người dùng ghi được
Name: "{app}\lyrics"

[Icons]
; AppUserModelID trùng với app -> chuột phải biểu tượng trên taskbar -> "Ghim" ghim đúng app
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "LyricSpotify.App"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "LyricSpotify.App"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "LyricSpotify.App"; Tasks: startup

[Run]
; tải phần AI ngay trong lúc cài (cửa sổ tiến trình riêng của app), nếu người dùng chọn
Filename: "{app}\{#AppExe}"; Parameters: "--install-ai --lang={language}"; StatusMsg: "{cm:AiStatus}"; Tasks: ai and not demucs; Flags: waituntilterminated
Filename: "{app}\{#AppExe}"; Parameters: "--install-ai --demucs --lang={language}"; StatusMsg: "{cm:AiStatus}"; Tasks: demucs; Flags: waituntilterminated
Filename: "{app}\{#AppExe}"; Parameters: "--lang={language}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

#ifndef TestBuild
; bản thử (TestBuild) không tắt app đang chạy và không xoá dữ liệu dùng chung của bản thật
[UninstallRun]
; tắt app trước khi gỡ (nếu đang chạy)
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#AppExe}"; Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
; phần AI tải thêm (vài GB) và công cụ tải nằm ngoài thư mục cài -> xoá cùng khi gỡ
Type: filesandordirs; Name: "{localappdata}\LyricSpotify"
#endif

[Code]
function AiLibs(): String;
begin
  Result := ExpandConstant('{localappdata}\LyricSpotify\ai-libs');
end;

function AiInstalled(): Boolean;
begin
  Result := DirExists(AiLibs() + '\faster_whisper');
end;

function DemucsInstalled(): Boolean;
begin
  Result := DirExists(AiLibs() + '\demucs') and DirExists(AiLibs() + '\torch');
end;
