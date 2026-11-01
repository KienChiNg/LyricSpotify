@echo off
cd /d %~dp0
echo === Build LyricSpotify.exe (ban nhe, khong kem thu vien AI) ===
python -m pip install -r requirements.txt pyinstaller || (pause & exit /b 1)
python -m PyInstaller LyricSpotify.spec --noconfirm --clean || (pause & exit /b 1)
echo.
echo Xong: dist\LyricSpotify.exe
pause
