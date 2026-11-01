@echo off
cd /d %~dp0
echo === Lyric Spotify - cai dat thu vien ===
where python >nul 2>nul || (echo Chua co Python. Tai Python 3.11+ tai https://www.python.org/downloads/ va tick "Add python.exe to PATH" & pause & exit /b 1)

echo.
echo [1/3] Thu vien bat buoc...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || (echo Loi cai dat & pause & exit /b 1)

echo.
set /p AI="[2/3] Cai AI chep loi khi khong tim thay loi? Can card NVIDIA, tai ~3 GB (y/N): "
if /i not "%AI%"=="y" goto done
python -m pip install -r requirements-ai.txt

echo.
set /p SEP="[3/3] Cai them tach giong hat (Demucs) de AI chep chinh xac hon? Tai ~2.5 GB (y/N): "
if /i not "%SEP%"=="y" goto done
python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
python -m pip install demucs

:done
echo.
echo Xong! Chay run.bat de mo app.
pause
