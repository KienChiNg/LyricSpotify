"""Chế độ lời trên thanh taskbar: một dải chữ nền trong suốt nằm đè lên taskbar,
ngay bên trái khu đồng hồ / biểu tượng hệ thống. Hiện dòng đang hát (+ dòng kế tiếp nếu đủ cao).

Windows không cho nhúng cửa sổ vào taskbar một cách chính thức, nên dải chữ là cửa sổ
"luôn trên cùng" được đặt đúng vị trí taskbar và tự đẩy lên trên taskbar mỗi nửa giây.
"""

import ctypes
import ctypes.wintypes as W
import time
import tkinter as tk
from tkinter import font as tkfont

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
gdi32.GetPixel.restype = ctypes.c_uint32
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongPtrW.argtypes = [W.HWND, ctypes.c_int]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [W.HWND, ctypes.c_int, ctypes.c_ssize_t]
KEY = "#010203"
PAD = 6
HWND_TOPMOST = -1
SWP_FLAGS = 0x0001 | 0x0002 | 0x0010  # NOSIZE | NOMOVE | NOACTIVATE


def _rect(hwnd):
    r = W.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [("cbSize", W.DWORD), ("rcMonitor", W.RECT), ("rcWork", W.RECT),
                ("dwFlags", W.DWORD), ("szDevice", W.WCHAR * 32)]


def monitor_at(x, y):
    """-> (tên màn hình, rect màn hình) tại điểm (x, y)."""
    hmon = user32.MonitorFromPoint(W.POINT(int(x), int(y)), 2)  # MONITOR_DEFAULTTONEAREST
    mi = MONITORINFOEX()
    mi.cbSize = ctypes.sizeof(MONITORINFOEX)
    user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
    m = mi.rcMonitor
    return mi.szDevice, (m.left, m.top, m.right, m.bottom)


def taskbars():
    """Tất cả thanh taskbar đang hiện: taskbar chính và taskbar của các màn hình phụ.
    -> list dict(hwnd, rect, right_ref, device, monitor, primary)."""
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, W.HWND, W.LPARAM)
    def cb(hwnd, _):
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, cls, 64)
        if cls.value in ("Shell_TrayWnd", "Shell_SecondaryTrayWnd") and user32.IsWindowVisible(hwnd):
            found.append((hwnd, cls.value == "Shell_TrayWnd"))
        return True

    user32.EnumWindows(cb, 0)
    bars = []
    for hwnd, primary in found:
        l, t, r, b = _rect(hwnd)
        # mép phải để canh dải chữ: khu đồng hồ/khay hệ thống (taskbar chính), đồng hồ (nếu có) hoặc mép taskbar
        ref = r
        for child in ("TrayNotifyWnd", "ClockButton"):
            c = user32.FindWindowExW(hwnd, None, child, None)
            if c:
                ref = _rect(c)[0]
                break
        device, mon = monitor_at((l + r) // 2, (t + b) // 2)
        bars.append({"hwnd": hwnd, "rect": (l, t, r, b), "right_ref": ref, "device": device,
                     "monitor": mon, "primary": primary})
    return bars


def taskbar_info():
    """-> (rect taskbar, rect khu đồng hồ/khay hệ thống) hoặc None."""
    tray = user32.FindWindowW("Shell_TrayWnd", None)
    if not tray:
        return None
    notify = user32.FindWindowExW(tray, None, "TrayNotifyWnd", None)
    return _rect(tray), (_rect(notify) if notify else None)


def covered_by(hwnd, other):
    """`other` đang nằm phía trên `hwnd` trong thứ tự cửa sổ (che nó)?"""
    h, n = user32.GetWindow(hwnd, 3), 0  # GW_HWNDPREV: cửa sổ ngay phía trên
    while h and n < 1000:
        if h == other:
            return True
        h, n = user32.GetWindow(h, 3), n + 1
    return False


def exclude_from_peek(hwnd):
    """Giữ cửa sổ hiện khi Aero Peek (rê/giữ chuột trên ảnh xem trước của app khác ở taskbar
    làm mờ mọi cửa sổ khác, kể cả cửa sổ luôn trên cùng)."""
    if not hwnd:
        return
    try:
        on = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(W.HWND(hwnd), 12, ctypes.byref(on), 4)  # DWMWA_EXCLUDED_FROM_PEEK
    except Exception:  # noqa: BLE001
        pass


def taskbar_is_light():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return bool(winreg.QueryValueEx(k, "SystemUsesLightTheme")[0])
    except OSError:
        return False


def fullscreen_app_active(monitor=None):
    """Có app toàn màn hình (phim, game) đang ở phía trước TRÊN màn hình của dải chữ -> ẩn dải chữ."""
    fg = user32.GetForegroundWindow()
    if not fg or fg in (user32.GetDesktopWindow(), user32.GetShellWindow()):
        return False
    cls = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(fg, cls, 64)
    if cls.value in ("Progman", "WorkerW", "Shell_TrayWnd"):
        return False
    l, t, r, b = _rect(fg)
    ml, mt, mr, mb = monitor or (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
    return l <= ml and t <= mt and r >= mr and b >= mb


class TaskbarLyrics:
    def __init__(self, app):
        self.app = app
        self.win = tk.Toplevel(app.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=KEY)
        self.win.attributes("-transparentcolor", KEY)
        self.canvas = tk.Canvas(self.win, bg=KEY, highlightthickness=0, cursor="hand2")
        self.canvas.pack(fill="both", expand=True)
        self.lines = ("", "")
        self.marquee = None
        self.content_w = None
        self.bar = None         # taskbar đang đặt dải chữ (màn hình chính hoặc phụ)
        self.peek_hwnd = None
        self.bars_cache = None  # (thời điểm, danh sách taskbar)   # bề rộng vừa đủ cho chữ đang hiện
        self.drawing = False
        self.geom = None
        self.hidden = False
        self.drag = None
        self.moved = False
        self.bg = KEY
        self.ticks = 0
        c = self.canvas
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_drag)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Button-3>", lambda e: app.menu.tk_popup(e.x_root, e.y_root))
        self.place()
        self.keep_on_top()

    # ---- vị trí -------------------------------------------------------- #

    def current_bar(self):
        """Taskbar của màn hình đã chọn (kéo dải chữ sang màn hình khác để đổi); không có thì taskbar chính.
        Danh sách taskbar chỉ tìm lại mỗi giây (liệt kê cửa sổ là bước tốn nhất trong vòng 0,1 giây)."""
        now = time.monotonic()
        if self.bars_cache is None or now - self.bars_cache[0] > 1.0 or self.drag:
            self.bars_cache = (now, taskbars())
        bars = self.bars_cache[1]
        if not bars:
            return None
        want = self.app.cfg.get("taskbar_monitor") or ""
        return (next((b for b in bars if b["device"] == want), None)
                or next((b for b in bars if b["primary"]), bars[0]))

    def place(self):
        bar = self.current_bar()
        if not bar:
            return
        self.bar = bar
        (l, t, r, b), notify = bar["rect"], (bar["right_ref"], 0, 0, 0)
        cfg = self.app.cfg
        horizontal = (r - l) >= (b - t)
        if not horizontal:  # taskbar dựng đứng: đặt dải chữ sát cạnh taskbar, gần đáy màn hình
            w, h = 360, 48
            x = r + 8 if l <= 0 else l - w - 8
            y = b - h - 60
        else:
            h = b - t
            # chỉ rộng vừa phần chữ (tối đa = độ rộng trong Cài đặt): phần taskbar còn lại vẫn bấm được
            w = min(cfg["taskbar_w"], self.content_w or cfg["taskbar_w"])
            right = (notify[0] if notify else r) - 8 - cfg["taskbar_offset"]
            x, y = max(l, right - w), t
        geom = (w, h, x, y)
        if geom != self.geom:
            resized = self.geom is None or self.geom[:2] != geom[:2]
            self.geom = geom
            self.win.geometry(f"{w}x{h}+{x}+{y}")
            if resized and not self.drawing:
                self.lines = None  # vẽ lại theo kích thước mới

    def on_press(self, e):
        self.drag = (e.x_root, self.app.cfg["taskbar_offset"])
        self.moved = False
        self.raise_now()

    def on_release(self, _e):
        # bấm vào dải lời không đổi chế độ (về cửa sổ lời: chuột phải -> bỏ chọn "Lời trên thanh taskbar")
        if self.drag and self.moved:
            self.app.save_config()
        self.drag = None
        self.raise_now()

    def on_drag(self, e):
        if self.drag:
            x0, off0 = self.drag
            if abs(e.x_root - x0) > 4:
                self.moved = True
            if not self.moved:
                return
            # kéo sang màn hình khác -> nhảy sang taskbar của màn hình đó, nằm ngay dưới con trỏ
            device, _mon = monitor_at(e.x_root, e.y_root)
            if self.bar and device != self.bar["device"]:
                target = next((b for b in taskbars() if b["device"] == device), None)
                if target:
                    w = self.geom[0] if self.geom else 200
                    off = max(0, target["right_ref"] - 8 - (e.x_root + w // 2))
                    self.app.cfg["taskbar_monitor"] = device
                    self.app.cfg["taskbar_offset"] = off
                    self.drag = (e.x_root, off)
                    self.place()
                    self.match_taskbar_color()
                    return
            self.app.cfg["taskbar_offset"] = max(0, off0 - (e.x_root - x0))
            self.place()

    def keep_on_top(self):
        """Mỗi 0,1 giây: giữ dải chữ trên taskbar, tự hiện lại nếu bị ẩn ngoài ý muốn,
        ẩn khi có app toàn màn hình trên cùng màn hình. Lỗi bất ngờ không làm dừng vòng lặp."""
        if not self.win.winfo_exists():
            return
        try:
            full = fullscreen_app_active(self.bar["monitor"] if self.bar else None)
            hwnd = user32.GetParent(self.win.winfo_id())
            if full and not self.hidden:
                self.win.withdraw()
                self.hidden = True
            elif not full:
                if self.hidden:
                    self.win.deiconify()
                    self.hidden = False
                elif hwnd and not user32.IsWindowVisible(hwnd):
                    user32.ShowWindow(hwnd, 8)  # bị ẩn ngoài ý muốn (Windows/app khác) -> hiện lại (SW_SHOWNA)
                self.raise_now()
                self.place()
                self.ticks += 1
                if self.ticks % 10 == 1:  # mỗi giây: nền theo màu taskbar
                    self.match_taskbar_color()
        except Exception:  # noqa: BLE001
            try:
                from spotify_lyrics import log_exception
                log_exception()
            except Exception:  # noqa: BLE001
                pass
        finally:
            # bấm vào taskbar (hoặc khe giữa các chữ) đưa taskbar lên trên -> đẩy dải chữ lên lại thật nhanh
            self.win.after(100, self.keep_on_top)

    def match_taskbar_color(self):
        """Tô nền dải chữ đúng màu taskbar (đọc ở khe giữa dải chữ và khu đồng hồ).
        Nền đặc (không trong suốt) nên bấm/kéo được ở mọi chỗ, nhìn vẫn như chữ nằm trên taskbar."""
        if not self.geom or self.geom[0] == 360:  # taskbar dựng đứng: giữ nền trong suốt
            return
        w, h, x, y = self.geom
        gx = x + w + 3
        dc = user32.GetDC(0)
        try:
            vals = [gdi32.GetPixel(dc, gx, y + int(h * f)) for f in (0.15, 0.5, 0.85)]
        finally:
            user32.ReleaseDC(0, dc)
        vals = [v for v in vals if v != 0xFFFFFFFF]
        if not vals:
            return
        r = sum(v & 0xFF for v in vals) // len(vals)
        g = sum((v >> 8) & 0xFF for v in vals) // len(vals)
        b = sum((v >> 16) & 0xFF for v in vals) // len(vals)
        color = f"#{r:02x}{g:02x}{b:02x}"
        if color == KEY:
            color = "#020304"
        if color != self.bg:
            self.bg = color
            self.canvas.configure(bg=color)
            self.win.configure(bg=color)

    def raise_now(self):
        hwnd = user32.GetParent(self.win.winfo_id())
        if hwnd != self.peek_hwnd:  # cửa sổ mới (Tk có thể tạo lại) -> gắn lại cờ chống Aero Peek
            exclude_from_peek(hwnd)
            self.peek_hwnd = hwnd
        self.own_by_taskbar(hwnd)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)
        # Sau khi rê/giữ chuột trên biểu tượng app (ảnh xem trước), Explorer đẩy taskbar lên lớp cao hơn
        # và lệnh trên không còn tác dụng -> đặt taskbar xuống ngay dưới dải chữ.
        bar = self.bar["hwnd"] if self.bar else None
        if bar and covered_by(hwnd, bar):
            user32.SetWindowPos(bar, hwnd, 0, 0, 0, 0, SWP_FLAGS)

    def own_by_taskbar(self, hwnd):
        """Cho dải lời "thuộc về" thanh taskbar: Windows luôn đặt cửa sổ con phía trên cửa sổ cha,
        nên bấm vào taskbar (taskbar trồi lên) thì dải lời vẫn nằm trên ngay, không bị che."""
        tray = self.bar["hwnd"] if self.bar else user32.FindWindowW("Shell_TrayWnd", None)
        if tray and user32.GetWindowLongPtrW(hwnd, -8) != tray:  # GWLP_HWNDPARENT = cửa sổ sở hữu
            user32.SetWindowLongPtrW(hwnd, -8, tray)

    # ---- vẽ ------------------------------------------------------------ #

    def ellipsis(self, text, font, width):
        """Cắt bớt '…' cho vừa bề ngang (giữ nguyên cỡ chữ)."""
        if font.measure(text) <= width:
            return text
        while text and font.measure(text + "…") > width:
            text = text[:-1]
        return text.rstrip() + "…"

    def update(self, current, upcoming):
        """Gọi mỗi khung hình. Cỡ chữ luôn cố định; câu dài thì chạy chữ ngang thay vì thu nhỏ."""
        if not self.geom:
            return
        if (current, upcoming) != self.lines:
            self.redraw(current, upcoming)
        if self.marquee:  # câu dài: đứng yên 1 giây ở đầu câu rồi trượt dần sang trái tới hết câu
            item, y, overflow, t0 = self.marquee
            offset = min(max(time.monotonic() - t0 - 1.0, 0.0) * 45, overflow)
            self.canvas.coords(item, PAD - round(offset), y)

    def redraw(self, current, upcoming):
        self.lines = (current, upcoming)
        self.marquee = None
        h = self.geom[1]
        c = self.canvas
        c.delete("all")
        light = taskbar_is_light()
        fg, dim = ("#000000", "#4a4a4a") if light else ("#ffffff", "#b4b4b4")
        family = self.app.cfg["font_family"]
        # cỡ chữ cố định theo chiều cao taskbar, không đổi theo độ dài câu
        f1 = tkfont.Font(family=family, size=-max(11, int(h * 0.40)), weight="bold")
        f2 = tkfont.Font(family=family, size=-max(9, int(h * 0.29)), weight="normal")
        two = bool(upcoming) and h >= 36
        # thu hẹp dải vừa đúng phần chữ rồi mới vẽ
        need = max(f1.measure(current), f2.measure(upcoming) if two else 0) + 2 * PAD + 2
        self.content_w = max(40, need)
        self.drawing = True
        try:
            self.place()
        finally:
            self.drawing = False
        w = self.geom[0]
        avail = w - 2 * PAD
        y1 = h * 0.31 if two else h / 2
        if f1.measure(current) > avail:
            item = c.create_text(PAD, y1, text=current, font=f1, fill=fg, anchor="w")
            self.marquee = (item, y1, f1.measure(current) - avail, time.monotonic())
        else:
            c.create_text(w - PAD, y1, text=current, font=f1, fill=fg, anchor="e")
        if two:
            c.create_text(w - PAD, h * 0.75, text=self.ellipsis(upcoming, f2, avail), font=f2,
                          fill=dim, anchor="e")

    def destroy(self):
        if self.win.winfo_exists():
            self.win.destroy()
