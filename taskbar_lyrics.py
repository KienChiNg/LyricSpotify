"""Chế độ lời trên thanh taskbar: một dải chữ nền trong suốt nằm đè lên taskbar,
ngay bên trái khu đồng hồ / biểu tượng hệ thống. Hiện dòng đang hát (+ dòng kế tiếp nếu đủ cao).

Windows không cho nhúng cửa sổ vào taskbar một cách chính thức, nên dải chữ là cửa sổ
"luôn trên cùng" được đặt đúng vị trí taskbar và tự đẩy lên trên taskbar mỗi nửa giây.
"""

import ctypes
import ctypes.wintypes as W
import tkinter as tk
from tkinter import font as tkfont

user32 = ctypes.windll.user32
KEY = "#010203"
HWND_TOPMOST = -1
SWP_FLAGS = 0x0001 | 0x0002 | 0x0010  # NOSIZE | NOMOVE | NOACTIVATE


def _rect(hwnd):
    r = W.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def taskbar_info():
    """-> (rect taskbar, rect khu đồng hồ/khay hệ thống) hoặc None."""
    tray = user32.FindWindowW("Shell_TrayWnd", None)
    if not tray:
        return None
    notify = user32.FindWindowExW(tray, None, "TrayNotifyWnd", None)
    return _rect(tray), (_rect(notify) if notify else None)


def taskbar_is_light():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return bool(winreg.QueryValueEx(k, "SystemUsesLightTheme")[0])
    except OSError:
        return False


def fullscreen_app_active():
    """Có app toàn màn hình (phim, game) đang ở phía trước -> taskbar bị che, ẩn dải chữ."""
    fg = user32.GetForegroundWindow()
    if not fg or fg in (user32.GetDesktopWindow(), user32.GetShellWindow()):
        return False
    cls = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(fg, cls, 64)
    if cls.value in ("Progman", "WorkerW", "Shell_TrayWnd"):
        return False
    l, t, r, b = _rect(fg)
    return l <= 0 and t <= 0 and r >= user32.GetSystemMetrics(0) and b >= user32.GetSystemMetrics(1)


class TaskbarLyrics:
    def __init__(self, app):
        self.app = app
        self.win = tk.Toplevel(app.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=KEY)
        self.win.attributes("-transparentcolor", KEY)
        self.canvas = tk.Canvas(self.win, bg=KEY, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.lines = ("", "")
        self.geom = None
        self.hidden = False
        self.drag = None
        c = self.canvas
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_drag)
        c.bind("<ButtonRelease-1>", lambda e: app.save_config())
        c.bind("<Double-Button-1>", lambda e: app.show_main_window())
        c.bind("<Button-3>", lambda e: app.menu.tk_popup(e.x_root, e.y_root))
        self.place()
        self.keep_on_top()

    # ---- vị trí -------------------------------------------------------- #

    def place(self):
        info = taskbar_info()
        if not info:
            return
        (l, t, r, b), notify = info
        cfg = self.app.cfg
        horizontal = (r - l) >= (b - t)
        if not horizontal:  # taskbar dựng đứng: đặt dải chữ sát cạnh taskbar, gần đáy màn hình
            w, h = 360, 48
            x = r + 8 if l <= 0 else l - w - 8
            y = b - h - 60
        else:
            h = b - t
            w = cfg["taskbar_w"]
            right = (notify[0] if notify else r) - 8 - cfg["taskbar_offset"]
            x, y = max(l, right - w), t
        geom = (w, h, x, y)
        if geom != self.geom:
            self.geom = geom
            self.win.geometry(f"{w}x{h}+{x}+{y}")
            self.lines = None  # vẽ lại theo kích thước mới

    def on_press(self, e):
        self.drag = (e.x_root, self.app.cfg["taskbar_offset"])

    def on_drag(self, e):
        if self.drag:
            x0, off0 = self.drag
            self.app.cfg["taskbar_offset"] = max(0, off0 - (e.x_root - x0))
            self.place()

    def keep_on_top(self):
        """Bấm vào taskbar sẽ đưa taskbar lên trên -> đẩy dải chữ lên lại; ẩn khi có app toàn màn hình."""
        if not self.win.winfo_exists():
            return
        full = fullscreen_app_active()
        if full and not self.hidden:
            self.win.withdraw()
            self.hidden = True
        elif not full:
            if self.hidden:
                self.win.deiconify()
                self.hidden = False
            hwnd = user32.GetParent(self.win.winfo_id())
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)
            self.place()
        self.win.after(500, self.keep_on_top)

    # ---- vẽ ------------------------------------------------------------ #

    def fit(self, text, family, px, weight, width, min_px):
        """Thu nhỏ chữ cho vừa bề ngang; nhỏ nhất vẫn dài thì cắt bớt '…'."""
        while px > min_px and tkfont.Font(family=family, size=-px, weight=weight).measure(text) > width:
            px -= 1
        f = tkfont.Font(family=family, size=-px, weight=weight)
        if f.measure(text) > width:
            while text and f.measure(text + "…") > width:
                text = text[:-1]
            text = text.rstrip() + "…"
        return text, (family, -px, weight)

    def update(self, current, upcoming):
        if (current, upcoming) == self.lines or not self.geom:
            return
        self.lines = (current, upcoming)
        w, h = self.geom[0], self.geom[1]
        c = self.canvas
        c.delete("all")
        light = taskbar_is_light()
        fg, dim = ("#000000", "#4a4a4a") if light else ("#ffffff", "#b4b4b4")
        family = self.app.cfg["font_family"]
        pad = 6
        two = bool(upcoming) and h >= 36
        if two:
            t1, f1 = self.fit(current, family, int(h * 0.40), "bold", w - 2 * pad, 10)
            t2, f2 = self.fit(upcoming, family, int(h * 0.30), "normal", w - 2 * pad, 9)
            c.create_text(w - pad, h * 0.30, text=t1, font=f1, fill=fg, anchor="e")
            c.create_text(w - pad, h * 0.74, text=t2, font=f2, fill=dim, anchor="e")
        else:
            t1, f1 = self.fit(current, family, int(h * 0.42), "bold", w - 2 * pad, 10)
            c.create_text(w - pad, h / 2, text=t1, font=f1, fill=fg, anchor="e")

    def destroy(self):
        if self.win.winfo_exists():
            self.win.destroy()
