"""Cửa sổ tải phần AI, chạy bởi trình cài đặt: LyricSpotify.exe --install-ai [--demucs]

Dùng chung cơ chế với nút "Tải phần AI" trong Cài đặt (ai_runtime.install), rồi tải sẵn
mô hình nhận dạng để lần đầu mở app là dùng AI được ngay.
"""

import importlib
import sys
import threading
import tkinter as tk
from tkinter import ttk

import ai_runtime
import theme
from i18n import set_lang, t

MODEL_REPO = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"


def model_cached():
    """Mô hình mặc định đã có trong bộ nhớ đệm Hugging Face chưa (không cần import thư viện)."""
    import glob
    import os
    hub = (os.environ.get("HF_HUB_CACHE")
           or os.path.join(os.environ.get("HF_HOME") or os.path.join(os.path.expanduser("~"), ".cache",
                                                                      "huggingface"), "hub"))
    folder = os.path.join(hub, "models--" + MODEL_REPO.replace("/", "--"), "snapshots", "*", "model.bin")
    return bool(glob.glob(folder))


def prefetch_model(progress):
    """Tải sẵn mô hình Whisper mặc định (~1.6 GB) vào bộ nhớ đệm Hugging Face."""
    ai_runtime.activate()
    importlib.invalidate_caches()
    from huggingface_hub import snapshot_download
    progress(t("setup_model"))
    snapshot_download(MODEL_REPO)


def run(cfg, with_demucs):
    # máy đã có phần nào thì bỏ qua phần đó; đủ hết thì không cần mở cửa sổ tải
    need_libs = not ai_runtime.installed() or (with_demucs and not ai_runtime.demucs_installed())
    need_model = not model_cached()
    if not need_libs and not need_model:
        return 0
    set_lang(cfg.get("ui_lang", "vi"))
    c = theme.colors(cfg.get("theme", "dark"))
    root = tk.Tk()
    root.title(t("setup_title"))
    root.geometry("520x210")
    root.resizable(False, False)
    root.configure(bg=c["BG"])
    root.attributes("-topmost", True)
    try:
        root.iconbitmap(default=_icon())
    except tk.TclError:
        pass

    tk.Label(root, text=t("setup_title"), bg=c["BG"], fg=c["FG"], font=("Segoe UI", 13, "bold"),
             anchor="w").pack(fill="x", padx=20, pady=(18, 2))
    tk.Label(root, text=t("setup_note_demucs") if with_demucs else t("setup_note"), bg=c["BG"],
             fg=c["FG_DIM"], font=("Segoe UI", 9), anchor="w", justify="left",
             wraplength=480).pack(fill="x", padx=20)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("AI.Horizontal.TProgressbar", background=c["ACCENT"], troughcolor=c["PANEL"],
                    bordercolor=c["BG"], lightcolor=c["ACCENT"], darkcolor=c["ACCENT"])
    bar = ttk.Progressbar(root, mode="indeterminate", style="AI.Horizontal.TProgressbar")
    bar.pack(fill="x", padx=20, pady=(14, 6))
    bar.start(12)
    status = tk.Label(root, text="", bg=c["BG"], fg=c["FG_DIM"], font=("Segoe UI", 8), anchor="w")
    status.pack(fill="x", padx=20)
    btn = tk.Button(root, text=t("cancel"), relief="flat", bd=0, padx=16, pady=4, cursor="hand2",
                    bg=c["PANEL"], fg=c["FG"], activebackground=c["HOVER"], activeforeground=c["FG"],
                    font=("Segoe UI", 10))
    btn.pack(anchor="e", padx=20, pady=10)
    result = {"code": 1}

    def progress(line):
        root.after(0, lambda: status.winfo_exists() and status.configure(text=line[-90:]))

    def finish(ok, msg):
        bar.stop()
        bar.configure(mode="determinate", value=100 if ok else 0)
        status.configure(text=msg, fg=c["ACCENT"] if ok else c["FG"])
        btn.configure(text=t("done"), command=root.destroy, bg=c["ACCENT"], fg=c["ON_ACCENT"])
        result["code"] = 0 if ok else 1
        if ok:
            root.after(2500, root.destroy)

    def work():
        try:
            ok = ai_runtime.install(with_demucs, progress) if need_libs else True
            if ok and need_model:
                try:
                    prefetch_model(progress)
                except Exception:  # noqa: BLE001 - mô hình sẽ tự tải khi dùng lần đầu
                    pass
            msg = t("setup_ok") if ok else t("setup_fail")
        except Exception as e:  # noqa: BLE001
            ok, msg = False, f"{t('setup_fail')} ({e})"
        root.after(0, lambda: finish(ok, msg))

    def cancel():
        ai_runtime.cancel()
        root.destroy()

    btn.configure(command=cancel)
    root.protocol("WM_DELETE_WINDOW", cancel)
    threading.Thread(target=work, daemon=True).start()
    root.mainloop()
    return result["code"]


def _icon():
    import os
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "icon.ico")
