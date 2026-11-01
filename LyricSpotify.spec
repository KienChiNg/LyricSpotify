# PyInstaller: đóng gói bản nhẹ LyricSpotify.exe (không kèm thư viện AI).
# Build:  build.bat   (hoặc: pyinstaller LyricSpotify.spec --noconfirm)
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Phần AI (tải sau trong app) cần nhiều module chuẩn mà app gốc không dùng -> kèm cả thư viện chuẩn
SKIP = {"test", "idlelib", "lib2to3", "turtledemo", "ensurepip", "venv", "pydoc_data", "turtle",
        "__phello__", "__hello__", "antigravity", "this", "curses", "readline", "tty", "pty", "termios",
        "fcntl", "grp", "pwd", "resource", "posix", "crypt", "spwd", "nis", "syslog", "ossaudiodev"}
hidden = []
for name in sorted(sys.stdlib_module_names):
    if name in SKIP or name.startswith(("_test", "_xx")):
        continue
    try:
        hidden += collect_submodules(name, filter=lambda n: ".test" not in n and "idle_test" not in n)
    except Exception:
        hidden.append(name)

# Thư viện AI nặng: KHÔNG đóng gói (người dùng tải sau qua Cài đặt -> Tải phần AI)
AI_EXCLUDES = ["numpy", "torch", "torchaudio", "torchvision", "demucs", "faster_whisper", "ctranslate2",
               "soundcard", "pycaw", "comtypes", "psutil", "huggingface_hub", "tokenizers", "onnxruntime",
               "av", "PIL", "scipy", "pandas", "matplotlib", "sympy", "networkx", "jinja2", "cffi"]

winrt_datas, winrt_bins, winrt_hidden = collect_all("winrt")
# DLL mà thư viện AI (tải sau) cần nhưng app gốc không dùng nên PyInstaller không tự kèm:
# python3.dll (gói abi3 như av), vcruntime140_1.dll (PyTorch, CTranslate2)
import os
extra_dlls = [(os.path.join(sys.base_prefix, n), ".") for n in ("python3.dll", "vcruntime140_1.dll")
              if os.path.exists(os.path.join(sys.base_prefix, n))]

a = Analysis(
    ["spotify_lyrics.py"],
    datas=[("icon.ico", "."), ("icon-header.png", ".")] + winrt_datas,
    binaries=winrt_bins + extra_dlls,
    hiddenimports=hidden + winrt_hidden + ["ai_runtime", "transcriber", "settings_window", "i18n", "theme", "ai_setup"],
    excludes=AI_EXCLUDES,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="LyricSpotify",
    icon="icon.ico",
    console=False,
    upx=False,
)
