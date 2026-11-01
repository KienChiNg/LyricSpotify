@echo off
cd /d %~dp0
echo === [1/2] Build LyricSpotify.exe (ban nhe, khong kem thu vien AI) ===
python -m pip install -r requirements.txt pyinstaller || (pause & exit /b 1)
python -m PyInstaller LyricSpotify.spec --noconfirm --clean || (pause & exit /b 1)

echo.
echo === [2/2] Tao ban cai dat (Inno Setup) ===
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo Chua co Inno Setup. Cai bang: winget install --id JRSoftware.InnoSetup -e --scope user
    pause & exit /b 1
)
"%ISCC%" installer.iss || (pause & exit /b 1)
echo.
echo Xong: dist\LyricSpotify-Setup-*.exe  ^(file nay dua len muc Releases^)
pause
