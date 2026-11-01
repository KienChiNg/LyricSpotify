"""Phần AI cài thêm (tải sau khi cài app) để bản app gốc nhẹ.

Bản exe chỉ chứa phần hiển thị lời. Khi người dùng bấm "Tải phần AI", app tải `uv`
(trình cài gói Python, ~15 MB) rồi cài faster-whisper, CUDA, (tuỳ chọn) PyTorch + Demucs
vào thư mục riêng, đúng phiên bản Python của app. Lần chạy sau, thư mục đó được thêm vào
sys.path nên `import faster_whisper` / `import torch` hoạt động như bình thường.
"""

import glob
import io
import os
import subprocess
import sys
import urllib.request
import zipfile

BASE = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "LyricSpotify")
LIBS = os.environ.get("LYRICSPOTIFY_AI_LIBS") or os.path.join(BASE, "ai-libs")
TOOLS = os.path.join(BASE, "tools")
UV_URL = "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"
PY_VER = f"{sys.version_info.major}.{sys.version_info.minor}"

AI_PACKAGES = ["faster-whisper", "soundcard", "numpy", "pycaw", "psutil",
               "nvidia-cublas-cu12", "nvidia-cudnn-cu12==9.*"]
DEMUCS_PACKAGES = ["torch==2.6.0+cu124", "torchaudio==2.6.0+cu124", "demucs"]
TORCH_INDEX = "https://download.pytorch.org/whl/cu124"


def activate():
    """Thêm thư mục AI đã cài vào đường dẫn import và DLL (gọi trước khi import thư viện AI)."""
    if not os.path.isdir(LIBS):
        return
    if LIBS not in sys.path:
        sys.path.append(LIBS)
    for d in glob.glob(os.path.join(LIBS, "nvidia", "*", "bin")) + [os.path.join(LIBS, "torch", "lib")]:
        if os.path.isdir(d):
            try:
                os.add_dll_directory(d)
            except OSError:
                pass
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")


def installed():
    return os.path.isdir(os.path.join(LIBS, "faster_whisper"))


def demucs_installed():
    return os.path.isdir(os.path.join(LIBS, "demucs")) and os.path.isdir(os.path.join(LIBS, "torch"))


def _uv(progress):
    exe = os.path.join(TOOLS, "uv.exe")
    if not os.path.exists(exe):
        progress("uv: downloading…")
        os.makedirs(TOOLS, exist_ok=True)
        with urllib.request.urlopen(UV_URL, timeout=60) as r:
            data = r.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                if name.endswith("uv.exe"):
                    with open(exe, "wb") as f:
                        f.write(z.read(name))
    return exe


def install(with_demucs, progress):
    """Cài phần AI. progress(str) nhận từng dòng tiến trình. Trả về True nếu thành công."""
    exe = _uv(progress)
    pkgs = AI_PACKAGES + (DEMUCS_PACKAGES if with_demucs else [])
    cmd = [exe, "pip", "install", "--target", LIBS, "--python", PY_VER,
           "--index-url", "https://pypi.org/simple"]
    if with_demucs:
        cmd += ["--extra-index-url", TORCH_INDEX, "--index-strategy", "unsafe-best-match"]
    cmd += pkgs
    env = dict(os.environ, UV_PYTHON_DOWNLOADS="automatic", UV_LINK_MODE="copy")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                            text=True, encoding="utf-8", errors="replace",
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for line in proc.stdout:
        if line.strip():
            progress(line.strip())
    return proc.wait() == 0
