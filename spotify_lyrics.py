"""Spotify Lyrics Desktop - cửa sổ nổi hiển thị lời bài hát đồng bộ với Spotify.

Lấy bài đang phát qua Windows Media Controls (không cần đăng nhập hay API key),
tải lời đồng bộ từ NetEase / LRCLIB, hoặc từ thư mục lyrics/ do người dùng tự thêm.

Điều khiển:
  Rê chuột vào cửa sổ     hiện thanh nút (độ đậm, nền trong suốt, sửa lời, menu, đóng)
  Kéo chuột trái          di chuyển cửa sổ (kéo góc phải-dưới để đổi kích thước)
  Nhấp đúp / phím T       bật/tắt nền trong suốt (chỉ hiện chữ)
  Lăn chuột               cuộn xem lời (tự quay về dòng đang hát sau 3 giây)
  ↑ ↓                     đổi độ đậm cửa sổ
  Chuột phải              menu đầy đủ
  Esc                     thoát
"""

import asyncio
import bisect
import ctypes
import ctypes.wintypes
import hashlib
import json
import os
import queue
import re
import sys
import threading
import time
import tkinter as tk
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import theme
import transcriber
from i18n import set_lang, t
from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as SessionManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
)

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".spotify_lyrics.json")
DEFAULTS = {"x": 120, "y": 120, "w": 520, "h": 400, "font": 17,
            "alpha": 0.92, "glass": False,
            "font_family": "Segoe UI", "bold": False,
            "ai_enabled": True, "ai_model": "large-v3-turbo",
            "ai_device": "", "ai_only_spotify": True, "ai_separate": True, "ui_lang": "vi",
            "theme": "dark", "taskbar_mode": False, "taskbar_hide_main": True,
            "taskbar_w": 460, "taskbar_offset": 0}
APP_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))  # tài nguyên (icon)
# dữ liệu của người dùng (thư mục lời): cạnh file exe khi chạy bản đóng gói
DATA_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
if not os.access(DATA_DIR, os.W_OK):  # cài vào thư mục không ghi được (vd: Program Files)
    DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "LyricSpotify")

FONT = "Segoe UI"
ICON_FONT = "Segoe MDL2 Assets"
THEME_KEYS = ("BG", "PANEL", "HOVER", "TRACK_BAR", "FG", "FG_DIM", "ACCENT", "ACCENT_HOVER", "ON_ACCENT",
              "SELECT", "GRIP", "KEY", "LINE_SOLID", "LINE_GLASS", "LINE_FADED")


def load_theme(choice):
    """Nạp bảng màu (tối / sáng / theo Windows) vào các hằng màu của module."""
    globals().update({k: theme.colors(choice)[k] for k in THEME_KEYS})


BG = PANEL = HOVER = TRACK_BAR = FG = FG_DIM = ACCENT = ACCENT_HOVER = ON_ACCENT = SELECT = GRIP = KEY = ""
LINE_SOLID = LINE_GLASS = LINE_FADED = []
load_theme("dark")
HEADER_H = 64
GRIP_SIZE = 18             # tay nắm góc phải dưới (px); màu tay nắm là GRIP trong theme.py
EDGE = 10                   # bề rộng vùng mép để kéo đổi kích thước
MIN_W, MIN_H = 300, 180


# --------------------------------------------------------------------------- #
# Trạng thái trình phát (đọc từ Windows Media Controls)
# --------------------------------------------------------------------------- #

class PlayerState:
    def __init__(self):
        self.lock = threading.Lock()
        self.track = None      # dict(title, artist, album, duration) hoặc None
        self.pos = 0.0         # giây, tại thời điểm self.stamp
        self.stamp = time.monotonic()
        self.playing = False
        self.error = None

    def update(self, track, pos, playing, fresh=True):
        """pos: vị trí Spotify báo (đã cộng thời gian kể từ lần cập nhật);
        fresh: Spotify vừa gửi mốc vị trí mới (khoảng mỗi 4.5 giây, khi tua, dừng/phát)."""
        with self.lock:
            now = time.monotonic()
            current = self.pos + (now - self.stamp if self.playing else 0.0)
            same_song = (track and self.track and
                         (track["title"], track["artist"]) == (self.track["title"], self.track["artist"]))
            if not same_song:
                # Đổi bài: Spotify thường báo tên bài mới trước, vị trí vẫn của bài cũ ->
                # chỉ tin vị trí nếu là mốc mới vừa gửi, không thì đếm từ 0
                pos = pos if fresh else 0.0
            elif fresh:
                pass  # mốc mới -> khớp lại hoàn toàn, không giữ sai lệch cũ
            else:
                pos = current  # giữa 2 mốc: đồng hồ của app chạy liền mạch
            self.track, self.pos, self.playing = track, pos, playing
            self.stamp = now
            self.error = None

    def snapshot(self):
        with self.lock:
            pos = self.pos
            if self.playing:
                pos += time.monotonic() - self.stamp
            return self.track, pos, self.playing, self.error


def pick_session(manager):
    for s in manager.get_sessions():
        if "spotify" in (s.source_app_user_model_id or "").lower():
            return s
    return None  # chỉ nhận app Spotify, bỏ qua trình duyệt và app khác


async def poll_player(state: PlayerState):
    while True:  # Windows Media chưa sẵn sàng -> thử lại thay vì dừng luồng
        try:
            manager = await SessionManager.request_async()
            break
        except Exception as e:  # noqa: BLE001
            with state.lock:
                state.error = str(e)
            await asyncio.sleep(2)
    last_sample = None
    while True:
        try:
            session = pick_session(manager)
            if session is None:
                state.update(None, 0.0, False)
            else:
                props = await session.try_get_media_properties_async()
                tl = session.get_timeline_properties()
                info = session.get_playback_info()
                playing = info.playback_status == PlaybackStatus.PLAYING
                duration = tl.end_time.total_seconds()
                pos = tl.position.total_seconds()
                upd = tl.last_updated_time
                sample = (pos, upd)  # dừng/phát không tính là mốc mới (vị trí có thể chưa cập nhật)
                fresh, last_sample = sample != last_sample, sample
                if playing and upd is not None and upd.year > 2000:
                    if upd.tzinfo is None:
                        upd = upd.replace(tzinfo=timezone.utc)
                    pos += (datetime.now(timezone.utc) - upd).total_seconds()
                if duration > 0:
                    pos = min(max(pos, 0.0), duration)
                track = None
                if props and props.title:
                    track = {"title": props.title, "artist": props.artist or "",
                             "album": props.album_title or "", "duration": duration}
                state.update(track, pos, playing, fresh)
        except Exception as e:  # noqa: BLE001 - giữ vòng lặp sống
            with state.lock:
                state.error = str(e)
        await asyncio.sleep(0.4)


# --------------------------------------------------------------------------- #
# Lời bài hát (thư mục lời, NetEase, LRCLIB)
# --------------------------------------------------------------------------- #

LRC_TIME = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")


def parse_lrc(text):
    lines = []
    for raw in text.splitlines():
        stamps = LRC_TIME.findall(raw)
        if not stamps:
            continue
        lyric = LRC_TIME.sub("", raw).strip()
        for m, s in stamps:
            lines.append((int(m) * 60 + float(s), lyric))
    lines.sort(key=lambda x: x[0])
    return lines


def clean_title(title):
    t = re.sub(r"\s*[\(\[](feat\.?|ft\.?|with)\s[^\)\]]*[\)\]]", "", title, flags=re.I)
    t = re.sub(r"\s+[-–]\s+.*(remaster|version|live|mono|stereo|edit|mix).*$", "", t, flags=re.I)
    return t.strip()


CACHE_DIR = os.path.join(os.path.expanduser("~"), ".spotify_lyrics_cache")
CREDIT_LINE = re.compile(r"^[一-鿿\s/]+\s*[:：]")


SOURCE_FAILS, SOURCE_DOWN = {}, {}


class SourceError(Exception):
    pass


def http_json(url, headers=None, tries=3):
    """GET JSON, tự thử lại khi máy chủ quá tải (429/5xx) hoặc mất mạng. 404 -> None."""
    headers = {"User-Agent": "SpotifyLyricsDesktop/1.1", **(headers or {})}
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=10) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code != 429 and e.code < 500:
                return None  # yêu cầu không hợp lệ với nguồn này -> coi như không có lời
            last = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = str(getattr(e, "reason", e))
        if attempt < tries - 1:
            time.sleep(1.5 * (attempt + 1))
    raise SourceError(last or "không kết nối được")


def lrclib(path, params):
    return http_json("https://lrclib.net" + path + "?" + urllib.parse.urlencode(params), tries=4)


def choose_best(results, duration):
    if not results:
        return None
    if duration > 0:
        close = [r for r in results if abs((r.get("duration") or 0) - duration) <= 4]
        results = close or results
    synced = [r for r in results if r.get("syncedLyrics")]
    pool = synced or [r for r in results if r.get("plainLyrics") or r.get("instrumental")]
    if not pool:
        return None
    return min(pool, key=lambda r: abs((r.get("duration") or 0) - duration))


def first_artist_of(artist):
    return re.split(r",|&| feat\.? | x ", artist)[0].strip() or artist


def from_lrclib(track):
    # Ít yêu cầu nhất có thể vì LRCLIB hay báo 503 ngẫu nhiên.
    duration = track["duration"]
    title, first_artist = clean_title(track["title"]), first_artist_of(track["artist"])
    hit = choose_best(lrclib("/api/search", {"track_name": title, "artist_name": first_artist}), duration)
    if not hit:
        hit = choose_best(lrclib("/api/search", {"q": f"{title} {first_artist}"}), duration)
    if not hit:
        return None
    if hit.get("syncedLyrics"):
        lines = parse_lrc(hit["syncedLyrics"])
        if lines:
            return {"kind": "synced", "lines": lines}
    if hit.get("plainLyrics"):
        return {"kind": "plain", "lines": [(0.0, l.strip()) for l in hit["plainLyrics"].splitlines()]}
    return {"kind": "instrumental"}


def plain(s):
    """Chuẩn hoá để so khớp: thường, bỏ dấu, bỏ ký tự đặc biệt."""
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[\W_]+", " ", s).strip()


def from_netease(track):
    """Nguồn chính (giống Spotify-Lyrics): NetEase Cloud Music, nhiều nhạc châu Á/Việt Nam."""
    headers = {"Referer": "https://music.163.com/", "User-Agent": "Mozilla/5.0"}
    title = clean_title(track["title"])
    artists = [plain(a) for a in re.split(r",|&", track["artist"]) if a.strip()]
    q = urllib.parse.quote(f"{first_artist_of(track['artist'])} {title}")
    data = http_json(f"https://music.163.com/api/search/get?s={q}&type=1&limit=30", headers)
    songs = ((data or {}).get("result") or {}).get("songs") or []
    duration = track["duration"]
    want = plain(title)

    def score(s):
        pts = 0
        name = plain(s.get("name", ""))
        if name == want:
            pts += 10
        elif name and (want in name or name in want):
            pts += 6
        song_artists = [plain(a.get("name", "")) for a in s.get("artists") or []]
        if any(a in song_artists for a in artists):
            pts += 5
        if duration > 0 and s.get("duration"):
            diff = abs(s["duration"] / 1000 - duration)
            pts += 10 if diff < 2 else 5 if diff < 5 else 0
        return pts

    ranked = sorted(((score(s), s) for s in songs), key=lambda x: -x[0])
    for pts, s in ranked[:6]:
        if pts < 15:  # tối thiểu: khớp tên + (nghệ sĩ hoặc thời lượng)
            break
        lyr = http_json(f"https://music.163.com/api/song/lyric?id={s['id']}&lv=1", headers)
        text = ((lyr or {}).get("lrc") or {}).get("lyric") or ""
        lines = [(t, l) for t, l in parse_lrc(text) if not CREDIT_LINE.match(l)]
        if any(l for _, l in lines):
            return {"kind": "synced", "lines": lines}
    return None


LYRICS_DIR = os.path.join(DATA_DIR, "lyrics")
AI_DIR = os.path.join(LYRICS_DIR, "ai")  # lời do AI chép (ưu tiên thấp nhất)
BAD_FILENAME = re.compile(r'[\\/:*?"<>|]')


def local_filename(track, synced):
    name = BAD_FILENAME.sub("", f"{first_artist_of(track['artist'])} - {clean_title(track['title'])}")
    return os.path.join(LYRICS_DIR, name.strip() + (".lrc" if synced else ".txt"))


def from_local(track, folder=None):
    """Lời do người dùng tự thêm: lyrics/<Ca sĩ> - <Tên bài>.lrc hoặc .txt (hoặc chỉ <Tên bài>)."""
    folder = folder or LYRICS_DIR
    if not os.path.isdir(folder):
        return None
    title, artist = clean_title(track["title"]), first_artist_of(track["artist"])
    exact = {plain(f"{artist} {title}"), plain(f"{title} {artist}")}
    title_only = plain(title)
    best = None
    for fn in os.listdir(folder):
        stem, ext = os.path.splitext(fn)
        if ext.lower() not in (".lrc", ".txt"):
            continue
        key = plain(stem)
        if key in exact:
            best = fn
            break
        if key == title_only and best is None:
            best = fn
    if not best:
        return None
    with open(os.path.join(folder, best), encoding="utf-8-sig", errors="replace") as f:
        text = f.read()
    lines = parse_lrc(text)
    if lines:
        return {"kind": "synced", "lines": lines}
    return {"kind": "plain", "lines": [(0.0, l.strip()) for l in text.splitlines()]}


def save_local(track, text, folder=None):
    folder = folder or LYRICS_DIR
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, os.path.basename(local_filename(track, synced=bool(parse_lrc(text)))))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")
    return path


def cache_path(track):
    # chỉ dùng ca sĩ đầu tiên: Windows Media và Spotify Web API có thể liệt kê ca sĩ khác nhau
    key = f"{track['title']}|{first_artist_of(track['artist'])}".lower()
    return os.path.join(CACHE_DIR, hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json")


def find_lyrics(track):
    local = from_local(track)  # lời người dùng tự thêm luôn được ưu tiên
    if local:
        return local
    path = cache_path(track)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        pass

    errors, best = [], None
    for name, source in (("NetEase", from_netease), ("LRCLIB", from_lrclib)):
        if SOURCE_DOWN.get(name, 0) > time.time():
            errors.append(f"{name}: tạm bỏ qua")
            continue
        try:
            result = source(track)
            SOURCE_FAILS[name] = 0
        except SourceError as e:
            errors.append(f"{name}: {e}")
            SOURCE_FAILS[name] = SOURCE_FAILS.get(name, 0) + 1
            if SOURCE_FAILS[name] >= 3:  # lỗi liên tục -> nghỉ 1 phút
                SOURCE_DOWN[name] = time.time() + 60
                SOURCE_FAILS[name] = 0
            continue
        if result and (best is None or result["kind"] == "synced"):
            best = result
        if best and best["kind"] == "synced":
            break

    if best:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(best, f, ensure_ascii=False)
        except OSError:
            pass
        return best
    ai_saved = from_local(track, AI_DIR)
    if ai_saved and ai_saved["kind"] == "synced":  # lời AI cũ có thể xuống dòng sai -> chia lại
        ai_saved["lines"] = transcriber.resplit_lines(ai_saved["lines"])
    if ai_saved:
        return ai_saved
    if errors:  # có nguồn chưa trả lời được -> chưa kết luận "không có lời", để UI thử lại
        return {"kind": "error", "error": "; ".join(errors)}
    return {"kind": "none"}


# --------------------------------------------------------------------------- #
# Giao diện
# --------------------------------------------------------------------------- #

def make_icon():
    """Tạo icon.ico cho app (nốt nhạc + dòng lời) nếu chưa có."""
    path = os.path.join(APP_DIR, "icon.ico")
    if os.path.exists(path):
        return path
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    s = 256
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    green, white, gray = (30, 215, 96, 255), (255, 255, 255, 255), (110, 110, 110, 255)
    d.rounded_rectangle((8, 8, s - 8, s - 8), radius=60, fill=(24, 24, 24, 255))
    d.ellipse((70, 70, 118, 110), fill=green)              # đầu nốt
    d.rectangle((108, 34, 118, 92), fill=green)            # thân nốt
    d.polygon([(118, 34), (160, 50), (160, 68), (118, 52)], fill=green)  # cờ nốt
    d.rounded_rectangle((52, 138, 204, 156), radius=9, fill=white)       # dòng đang hát
    d.rounded_rectangle((72, 174, 184, 188), radius=7, fill=gray)
    d.rounded_rectangle((88, 204, 168, 216), radius=6, fill=gray)
    img.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)])
    return path


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    cfg.pop("spotify_client_id", None)  # tính năng Liked Songs đã bỏ
    cfg.pop("ai_lang", None)  # gộp vào một ô ngôn ngữ duy nhất
    return cfg


class LyricsWindow:
    def __init__(self, state: PlayerState):
        self.state = state
        self.cfg = load_config()
        set_lang(self.cfg["ui_lang"])
        load_theme(self.cfg["theme"])
        self.theme_now = theme.resolve(self.cfg["theme"])
        self.root = tk.Tk()
        self.root.title("Lyric Spotify")
        self.icon = make_icon()
        try:  # icon nhỏ ở thanh tiêu đề cửa sổ lời
            self.header_icon = tk.PhotoImage(master=None, file=os.path.join(APP_DIR, "icon-header.png"))
        except (tk.TclError, RuntimeError):
            self.header_icon = None
        if self.icon:
            self.root.iconbitmap(default=self.icon)
        self.root.overrideredirect(True)
        self.root.configure(bg=BG)
        self.root.geometry(f"{self.cfg['w']}x{self.cfg['h']}+{self.cfg['x']}+{self.cfg['y']}")
        self.root.attributes("-topmost", True)  # luôn nổi trên cùng
        self.root.attributes("-alpha", self.cfg["alpha"])
        if self.cfg["glass"]:
            self.root.attributes("-transparentcolor", KEY)
        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.track_key = None
        self.track = None
        self.lyrics = None          # kết quả find_lyrics
        self.times = []
        self.items, self.ys, self.hs = [], [], []
        self.scroll = 0.0
        self.scroll_px = 0          # vị trí đã vẽ (điểm ảnh nguyên)
        self.anim = None            # (từ, tới, lúc bắt đầu, thời lượng)
        self.cur = None
        self.message = ("", {})     # (key i18n, tham số)
        self.fetch_token = 0
        self.results = queue.Queue()  # (token, kết quả tìm lời)
        self.ai_gen = 0             # thế hệ Transcriber: bỏ sự kiện của phiên AI cũ
        self.resize_job = None
        self.save_job = None
        self.last_time_text = None
        self.retries = {}           # số lần đã tự thử lại theo bài
        self.drag = None
        self.maximized = None       # hình học trước khi phóng to (None = không phóng to)
        self.manual = None          # vị trí cuộn do người dùng lăn chuột
        self.manual_until = 0.0
        self.hover = False
        self.ai = None              # Transcriber đang chạy
        self.ai_events = queue.Queue()
        self.ai_status = None       # (key i18n, tham số)
        self.settings_win = None
        self.taskbar = None         # dải lời trên thanh taskbar
        self.hide_job = None
        self.toast_job = None
        self.size = (self.cfg["w"], self.cfg["h"])
        self.root.report_callback_exception = lambda *exc: log_exception(exc)

        self.build_menu()
        self.bind_events()
        self.relayout()
        self.root.after(80, self.show_in_taskbar)
        self.root.after(3000, self.watch_windows_theme)
        self.root.after(500, self.watch_pointer)
        if self.cfg["taskbar_mode"]:
            self.root.after(300, lambda: self.set_taskbar_mode(True, save=False))
        self.tick()

    # ---- cửa sổ ---------------------------------------------------------- #

    def show_in_taskbar(self):
        """Cửa sổ không viền vẫn có icon trên taskbar để dễ tìm."""
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(self.root.winfo_id())
            style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
            user32.SetWindowLongW(hwnd, -20, (style & ~0x80) | 0x40000)  # bỏ TOOLWINDOW, thêm APPWINDOW
            self.root.withdraw()
            self.root.after(10, self.root.deiconify)
        except Exception:  # noqa: BLE001
            pass

    # ---- sự kiện --------------------------------------------------------- #

    def bind_events(self):
        c = self.canvas
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_drag)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Double-Button-1>", self.on_double)
        c.bind("<Motion>", self.on_motion)
        c.bind("<Button-3>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        c.bind("<MouseWheel>", self.on_wheel)
        c.bind("<Configure>", self.on_resize)
        c.bind("<Enter>", self.on_enter)
        c.bind("<Leave>", self.on_leave)
        self.root.bind("<Escape>", lambda e: self.quit())
        self.root.bind("<Up>", lambda e: self.change_alpha(0.05))
        self.root.bind("<Down>", lambda e: self.change_alpha(-0.05))
        self.root.bind("<t>", lambda e: self.toggle_glass())

    def build_menu(self):
        if getattr(self, "menu", None):
            self.menu.destroy()
        self.glass_var = tk.BooleanVar(value=self.cfg["glass"])
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label=t("menu_settings"), command=self.open_settings)
        self.taskbar_var = tk.BooleanVar(value=self.cfg["taskbar_mode"])
        m.add_checkbutton(label=t("menu_taskbar"), variable=self.taskbar_var,
                          command=lambda: self.set_taskbar_mode(self.taskbar_var.get()))
        m.add_checkbutton(label=t("menu_glass"), variable=self.glass_var,
                          command=lambda: self.toggle_glass(self.glass_var.get()))
        m.add_separator()
        m.add_command(label=t("menu_edit"), command=self.edit_lyrics)
        m.add_command(label=t("menu_reload"), command=self.refetch)
        m.add_command(label=t("menu_folder"), command=self.open_lyrics_dir)
        m.add_separator()
        m.add_command(label=t("menu_quit"), command=self.quit)
        self.menu = m

    def toolbar_buttons(self):
        return [
            ("close", "", t("btn_close"), self.quit),
            ("max", "" if self.maximized else "",
             t("btn_restore") if self.maximized else t("btn_max"), self.toggle_maximize),
            ("min", "", t("btn_min"), self.minimize),
            ("more", "", t("btn_more"), self.menu_from_button),
            ("glass", "", t("btn_glass"), self.toggle_glass),
            ("settings", "", t("btn_settings"), self.open_settings),
        ]

    def menu_from_button(self):
        x = self.root.winfo_rootx() + self.canvas.winfo_width() - 60
        self.menu.tk_popup(x, self.root.winfo_rooty() + 44)

    def edges_at(self, x, y):
        """Cạnh/góc dưới con trỏ: chuỗi gồm 'l','r','t','b' (rỗng = giữa cửa sổ)."""
        if self.maximized:
            return ""
        w, h = self.root.winfo_width(), self.root.winfo_height()
        e = ("l" if x < EDGE else "r" if x >= w - EDGE else "") + ("t" if y < EDGE else "b" if y >= h - EDGE else "")
        if not e and x >= w - GRIP_SIZE and y >= h - GRIP_SIZE:  # tay nắm góc phải dưới (như cũ)
            e = "rb"
        return e

    EDGE_CURSORS = {"l": "size_we", "r": "size_we", "t": "size_ns", "b": "size_ns",
                    "lt": "size_nw_se", "rb": "size_nw_se", "rt": "size_ne_sw", "lb": "size_ne_sw"}

    def set_cursor(self, cursor):
        if self.canvas.cget("cursor") != cursor:
            self.canvas.configure(cursor=cursor)

    def on_motion(self, e):
        """Rê chuột tới mép cửa sổ -> con trỏ mũi tên co giãn."""
        if self.drag or "btn" in self.canvas.gettags("current"):
            return
        self.set_cursor(self.EDGE_CURSORS.get(self.edges_at(e.x, e.y), ""))

    def watch_pointer(self):
        """Chuột ở bất kỳ đâu trong khung cửa sổ (kể cả vùng nền trong suốt vốn không nhận chuột)
        -> hiện nền + nút + nhận kéo ở mép; rời khung -> ẩn như cũ."""
        try:
            if self.root.state() == "normal":
                x, y = self.root.winfo_pointerxy()
                rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
                inside = rx <= x < rx + self.root.winfo_width() and ry <= y < ry + self.root.winfo_height()
                if inside and not self.hover:
                    self.on_enter(None)
                elif not inside and self.hover and not self.hide_job and not self.drag:
                    self.on_leave(None)
        finally:
            self.root.after(80, self.watch_pointer)

    def on_press(self, e):
        self.root.focus_force()
        if "btn" in self.canvas.gettags("current"):
            self.drag = None
            return
        w, h = self.root.winfo_width(), self.root.winfo_height()
        edges = self.edges_at(e.x, e.y)
        if not edges and self.maximized:  # kéo cửa sổ đang phóng to: không dời
            self.drag = None
            return
        self.drag = (edges, e.x_root, e.y_root, self.root.winfo_x(), self.root.winfo_y(), w, h)
        self.set_cursor(self.EDGE_CURSORS.get(edges, ""))  # giữ mũi tên co giãn suốt lúc kéo

    def on_release(self, e):
        if self.drag:
            self.save_config()
        self.drag = None
        self.on_motion(e)  # con trỏ trở lại theo vị trí hiện tại

    def on_drag(self, e):
        if not self.drag:
            return
        edges, x0, y0, wx, wy, w, h = self.drag
        dx, dy = e.x_root - x0, e.y_root - y0
        if not edges:
            self.root.geometry(f"+{wx + dx}+{wy + dy}")
            return
        x, y, nw, nh = wx, wy, w, h
        if "r" in edges:
            nw = max(MIN_W, w + dx)
        if "b" in edges:
            nh = max(MIN_H, h + dy)
        if "l" in edges:
            nw = max(MIN_W, w - dx)
            x = wx + w - nw  # giữ nguyên mép phải
        if "t" in edges:
            nh = max(MIN_H, h - dy)
            y = wy + h - nh  # giữ nguyên mép dưới
        self.root.geometry(f"{nw}x{nh}+{x}+{y}")

    def on_double(self, e):
        if "btn" in self.canvas.gettags("current"):
            return
        if e.y < HEADER_H:
            self.toggle_maximize()
        else:
            self.toggle_glass()

    def toggle_maximize(self):
        """Phóng to bằng vùng làm việc của màn hình (trừ taskbar) / khôi phục kích thước cũ."""
        if self.maximized:
            self.root.geometry(self.maximized)
            self.maximized = None
        else:
            self.maximized = self.root.geometry()
            r = ctypes.wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)  # SPI_GETWORKAREA
            self.root.geometry(f"{r.right - r.left}x{r.bottom - r.top}+{r.left}+{r.top}")
        self.root.after(80, self.relayout)  # đổi biểu tượng nút phóng to / khôi phục

    def minimize(self):
        """Thu nhỏ xuống taskbar (cửa sổ không viền nên dùng Win32); bấm biểu tượng app để mở lại."""
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE

    def on_wheel(self, e):
        """Lăn chuột chỉ cuộn lời; 3 giây sau tự quay về dòng đang hát."""
        if not self.ys:
            return
        base = self.manual if self.manual is not None else self.scroll
        step = (self.cfg["font"] * 3) * (-e.delta / 120)
        lo, hi = self.target_scroll(0), self.target_scroll(len(self.ys) - 1)
        self.manual = min(max(base + step, lo), hi)
        self.manual_until = time.monotonic() + 3.0

    def on_resize(self, e):
        if (e.width, e.height) == self.size:
            return
        (w0, h0), self.size = self.size, (e.width, e.height)
        # 1) dịch ngay lời để dòng đang hát vẫn ở chính giữa (nhẹ, chạy được mỗi khung hình)
        dx, dy = (e.width - w0) / 2, (e.height - h0) / 2
        self.canvas.move("lyric", dx, dy)
        self.canvas.move("msg", dx, dy)
        self.scroll -= dy
        self.scroll_px = round(self.scroll)
        self.anim = None
        if self.manual is not None:
            self.manual -= dy
        # 2) vẽ lại (xuống dòng theo chiều rộng mới) đều đặn trong lúc kéo, không đợi thả chuột
        if not self.resize_job:
            def redraw():
                self.resize_job = None
                self.relayout()
            self.resize_job = self.root.after(40, redraw)

    def on_enter(self, _e):
        if self.hide_job:
            self.root.after_cancel(self.hide_job)
            self.hide_job = None
        if not self.hover:
            self.hover = True
            self.apply_mode()

    def on_leave(self, _e):
        if self.hide_job:
            self.root.after_cancel(self.hide_job)
        self.hide_job = self.root.after(700, self.end_hover)

    def end_hover(self):
        self.hide_job = None
        # chuột vẫn trong cửa sổ (vd: đi qua nút) -> giữ nguyên
        x, y = self.root.winfo_pointerxy()
        rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        if rx <= x < rx + self.root.winfo_width() and ry <= y < ry + self.root.winfo_height():
            return
        self.hover = False
        self.apply_mode()

    # ---- hành động ------------------------------------------------------- #

    def toggle_glass(self, value=None):
        self.cfg["glass"] = (not self.cfg["glass"]) if value is None else value
        self.glass_var.set(self.cfg["glass"])
        self.root.attributes("-transparentcolor", KEY if self.cfg["glass"] else "")
        self.toast(t("toast_glass_on") if self.cfg["glass"] else t("toast_glass_off"))
        self.save_config()
        self.apply_mode()

    def set_alpha(self, a):
        self.cfg["alpha"] = round(min(1.0, max(0.15, a)), 2)
        self.root.attributes("-alpha", self.cfg["alpha"])
        self.cur = None  # tô màu lại theo độ mờ mới
        self.recolor()
        self.toast(t("toast_alpha", pct=round(self.cfg["alpha"] * 100)))
        self.save_soon()

    def change_alpha(self, d):
        self.set_alpha(self.cfg["alpha"] + d)

    def set_ui_lang(self, code):
        self.cfg["ui_lang"] = code
        set_lang(code)
        self.save_config()
        self.build_menu()
        self.relayout()
        self.reopen_settings()

    def reopen_settings(self):
        if self.settings_win:  # vẽ lại cửa sổ cài đặt (ngôn ngữ / giá trị mới), giữ vị trí
            geo = self.settings_win.win.geometry()
            self.settings_win.close()
            self.open_settings()
            self.settings_win.win.geometry(geo)

    def reset_settings(self):
        keep = {k: self.cfg[k] for k in ("x", "y", "w", "h")}
        self.cfg = {**DEFAULTS, **keep}
        set_lang(self.cfg["ui_lang"])
        load_theme(self.cfg["theme"])
        self.root.configure(bg=BG)
        self.root.attributes("-alpha", self.cfg["alpha"])
        self.root.attributes("-transparentcolor", KEY if self.cfg["glass"] else "")
        self.save_config()
        self.build_menu()
        self.stop_ai(save=False)
        self.refetch()
        self.relayout()
        self.reopen_settings()

    @staticmethod
    def ai_dir():
        return AI_DIR

    @staticmethod
    def cache_dir():
        return CACHE_DIR

    def set_theme(self, choice):
        self.cfg["theme"] = choice
        self.save_config()
        self.apply_theme()
        self.reopen_settings()

    def apply_theme(self):
        load_theme(self.cfg["theme"])
        self.theme_now = theme.resolve(self.cfg["theme"])
        self.root.configure(bg=BG)
        self.canvas.configure(bg=BG)
        if self.cfg["glass"]:
            self.root.attributes("-transparentcolor", KEY)
        self.relayout()

    def watch_windows_theme(self):
        """Chế độ "Theo Windows": đổi màu ngay khi người dùng đổi sáng/tối trong Windows."""
        if self.cfg["theme"] == "system" and theme.resolve("system") != self.theme_now:
            self.apply_theme()
            self.reopen_settings()
        self.root.after(3000, self.watch_windows_theme)

    def set_text_style(self, size, family, bold):
        self.cfg.update(font=size, font_family=family, bold=bold)
        self.relayout()

    def open_settings(self):
        if self.settings_win:
            self.settings_win.win.lift()
            return
        from settings_window import SettingsWindow
        self.settings_win = SettingsWindow(self)

    def set_ai(self, **kw):
        self.cfg.update({f"ai_{k}": v for k, v in kw.items()})
        self.save_config()
        # áp dụng ngay cho bài hiện tại nếu AI đang chép (hoặc bài này không có lời)
        if not self.cfg["ai_enabled"] or not self.cfg["ai_separate"]:
            transcriber.release_separator()
        if self.ai or (self.track and not (self.lyrics and self.lyrics.get("lines"))):
            self.stop_ai(save=False)
            if self.cfg["ai_enabled"] and self.track:
                self.start_ai()

    def set_taskbar_mode(self, on, save=True):
        """Bật/tắt lời trên thanh taskbar; khi bật có thể ẩn cửa sổ lời lớn."""
        self.cfg["taskbar_mode"] = on
        self.taskbar_var.set(on)
        if on and not self.taskbar:
            from taskbar_lyrics import TaskbarLyrics
            self.taskbar = TaskbarLyrics(self)
            if self.cfg["taskbar_hide_main"]:
                self.root.withdraw()
        elif not on and self.taskbar:
            self.taskbar.destroy()
            self.taskbar = None
            self.show_main_window()
        if save:
            self.save_config()

    def show_main_window(self):
        self.root.deiconify()
        self.root.lift()

    def taskbar_text(self):
        """(dòng đang hát, dòng kế tiếp) cho dải lời trên taskbar."""
        tr = self.track
        title = f"{tr['title']} — {tr['artist']}" if tr else "Lyric Spotify"
        lines = (self.lyrics or {}).get("lines") or []
        if lines and self.lyrics.get("kind") == "synced":
            i = self.cur if self.cur is not None else -1
            cur = lines[i][1] if i >= 0 else "♪ " + title
            nxt = next((l for _, l in lines[i + 1:] if l.strip()), "")
            return (cur or "♪"), nxt
        if lines:  # lời thường (không có thời gian)
            return "♪ " + title, ""
        return "♪ " + title, self.message_text().splitlines()[0] if self.message_text() else ""

    def open_lyrics_dir(self):
        os.makedirs(LYRICS_DIR, exist_ok=True)
        os.startfile(LYRICS_DIR)

    def edit_lyrics(self):
        track = self.track
        if not track:
            self.toast(t("toast_no_track"))
            return
        win = tk.Toplevel(self.root, bg=BG)
        win.title(t("edit_title", title=track["title"]))
        win.geometry("580x560")
        win.attributes("-topmost", True)
        tk.Label(win, text=track["title"], bg=BG, fg=FG, font=(FONT, 14, "bold"),
                 anchor="w", padx=16, pady=(0)).pack(fill="x", pady=(14, 0))
        tk.Label(win, text=track["artist"], bg=BG, fg=FG_DIM, font=(FONT, 10),
                 anchor="w", padx=16).pack(fill="x")
        tk.Label(win, bg=BG, fg=FG_DIM, font=(FONT, 9), justify="left", anchor="w", padx=16, pady=8,
                 text=t("edit_hint")).pack(fill="x")
        frame = tk.Frame(win, bg=PANEL, padx=1, pady=1)
        frame.pack(fill="both", expand=True, padx=16)
        box = tk.Text(frame, wrap="word", font=(FONT, 11), undo=True, bg=PANEL, fg=FG,
                      insertbackground=FG, selectbackground=SELECT, relief="flat",
                      padx=10, pady=8, highlightthickness=0)
        box.pack(fill="both", expand=True)
        if self.lyrics:  # sửa lời hiện có
            if self.lyrics["kind"] == "synced":
                box.insert("1.0", "\n".join(f"[{int(t // 60):02d}:{t % 60:05.2f}]{l}"
                                            for t, l in self.lyrics["lines"]))
            else:
                box.insert("1.0", "\n".join(l for _, l in self.lyrics["lines"]))
        box.focus_set()

        def save():
            text = box.get("1.0", "end").strip()
            if text:
                save_local(track, text)
                self.refetch()
                self.toast(t("toast_saved"))
            win.destroy()

        bar = tk.Frame(win, bg=BG, pady=12)
        bar.pack(fill="x", padx=16)
        flat = dict(relief="flat", bd=0, font=(FONT, 10, "bold"), padx=18, pady=6, cursor="hand2")
        tk.Button(bar, text=t("save"), command=save, bg=ACCENT, fg=ON_ACCENT,
                  activebackground=ACCENT_HOVER, activeforeground=ON_ACCENT, **flat).pack(side="right")
        tk.Button(bar, text=t("cancel"), command=win.destroy, bg=PANEL, fg=FG,
                  activebackground=HOVER, activeforeground=FG, **flat).pack(side="right", padx=8)
        tk.Button(bar, text=t("open_folder"), command=self.open_lyrics_dir, bg=BG, fg=FG_DIM,
                  activebackground=BG, activeforeground=FG, **flat).pack(side="left")
        win.bind("<Control-s>", lambda e: save())
        win.bind("<Escape>", lambda e: win.destroy())

    def refetch(self):
        self.track_key = None

    def save_soon(self):
        if self.save_job:
            self.root.after_cancel(self.save_job)
        self.save_job = self.root.after(800, self.save_config)

    def save_config(self):
        if self.maximized:  # lưu kích thước bình thường, không lưu kích thước phóng to
            size, x, y = self.maximized.split("+")[:3]
            w, h = size.split("x")
            self.cfg.update(x=int(x), y=int(y), w=int(w), h=int(h))
        else:
            self.cfg.update(x=self.root.winfo_x(), y=self.root.winfo_y(),
                            w=self.root.winfo_width(), h=self.root.winfo_height())
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, indent=2)
        except OSError:
            pass

    def restart(self):
        """Mở lại app (sau khi cài phần AI)."""
        import subprocess
        args = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, os.path.abspath(__file__)]
        self.quit()
        subprocess.Popen(args, close_fds=True)

    def quit(self):
        if self.taskbar:
            self.taskbar.destroy()
        self.stop_ai()
        self.save_config()
        self.root.destroy()

    # ---- tải lời --------------------------------------------------------- #

    def start_fetch(self, track):
        self.fetch_token += 1
        token = self.fetch_token

        def work():
            try:
                result = find_lyrics(track)
            except Exception as e:  # noqa: BLE001
                result = {"kind": "error", "error": str(e)}
            self.results.put((token, result))

        threading.Thread(target=work, daemon=True).start()

    def start_ai(self):
        if not transcriber.ready(self.cfg["ai_model"]):  # chưa tải đủ phần AI -> không tự tải
            return
        self.ai_gen += 1
        key, gen, q = self.track_key, self.ai_gen, self.ai_events
        self.ai = transcriber.Transcriber(
            self.state, key, self.cfg["ai_model"], "auto",  # AI tự nhận ngôn ngữ bài hát
            on_line=lambda t, l: q.put(("line", gen, t, l)),
            on_status=lambda k, **kw: q.put(("status", gen, (k, kw))),
            only_spotify=self.cfg["ai_only_spotify"], device=self.cfg["ai_device"],
            separate=self.cfg["ai_separate"])
        self.ai.start()
        self.lyrics = {"kind": "synced", "lines": [], "ai": True}
        self.times = []
        self.ai_status = ("ai_preparing", {})
        self.message = ("ai_fallback", {})
        self.relayout()

    def stop_ai(self, save=True):
        ai, self.ai = self.ai, None
        if not ai:
            return
        ai.stop()
        track = self.track
        if save and track and ai.covers_whole_song(track.get("duration") or 0):
            def to_lrc(lines):
                lines = transcriber.resplit_lines(lines)
                return "\n".join(f"[{int(t // 60):02d}:{t % 60:05.2f}]{l}" for t, l in lines)

            save_local(track, to_lrc(ai.lines), AI_DIR)  # lưu ngay, kể cả khi app sắp tắt

            def refine_and_save():  # chép lại cả bài (chính xác hơn) rồi ghi đè, chạy nền
                lines = ai.refine_lines()
                if lines is not ai.lines:
                    save_local(track, to_lrc(lines), AI_DIR)
            threading.Thread(target=refine_and_save, daemon=True).start()
        self.ai_status = None

    def drain_ai(self):
        changed = False
        while True:
            try:
                kind, gen, *data = self.ai_events.get_nowait()
            except queue.Empty:
                break
            if not self.ai or gen != self.ai_gen or not self.lyrics or not self.lyrics.get("ai"):
                continue
            if kind == "status":
                st = data[0]
                self.ai_status = st if isinstance(st, tuple) else ("raw", {"text": str(st)})
                if not self.lyrics["lines"]:
                    self.message = self.ai_status
            else:
                t, line = data
                i = bisect.bisect(self.times, t)
                self.times.insert(i, t)
                self.lyrics["lines"].insert(i, (t, line))
            changed = True
        if changed:
            self.relayout()

    # ---- vẽ -------------------------------------------------------------- #

    def glass_idle(self):
        return self.cfg["glass"] and not self.hover

    def palette(self):
        if self.glass_idle():
            return LINE_GLASS
        return LINE_FADED if self.cfg["alpha"] < 0.85 else LINE_SOLID

    def text(self, x, y, tags, **kw):
        return self.canvas.create_text(x, y, tags=tags, **kw)

    def relayout(self):
        c = self.canvas
        c.delete("all")
        w = max(c.winfo_width(), 50)
        h = max(c.winfo_height(), 50)
        self.items, self.ys, self.hs = [], [], []
        keep_idx = self.cur if self.cur is not None else -1  # giữ vị trí khi vẽ lại giữa bài
        self.cur = None

        lines =self.lyrics["lines"] if self.lyrics and self.lyrics.get("lines") else []
        if lines:
            y = 0.0
            gap = self.cfg["font"] * 0.9
            font = (self.cfg["font_family"], self.cfg["font"], "bold" if self.cfg["bold"] else "normal")
            for _, line in lines:
                it = self.text(w / 2, y, ("lyric",), text=line or "♪", width=w - 48,
                               justify="center", anchor="n", font=font, fill=LINE_SOLID[2])
                x1, y1, x2, y2 = c.bbox(it)
                self.items.append(it)
                self.ys.append(y)
                self.hs.append(y2 - y1)
                y += (y2 - y1) + gap
            self.scroll, self.scroll_px, self.anim = 0.0, 0, None
            self.scroll_to(self.target_scroll(min(keep_idx, len(self.ys) - 1)), instant=True)
        else:
            mid = HEADER_H + (h - HEADER_H) / 2
            self.text(w / 2, mid - 16, ("msg",), text="✦" if self.ai else "♪", font=(FONT, 26), fill=ACCENT)
            self.text(w / 2, mid + 22, ("msg",), text=self.message_text(), width=w - 48, justify="center",
                      font=(FONT, 11), fill=FG_DIM, anchor="n")

        # header: icon + tên bài + ca sĩ, vẽ đè lên phần lời đã cuộn qua
        c.create_rectangle(0, 0, w, HEADER_H, fill=BG, outline="", tags=("header", "headerbg"))
        if self.header_icon:
            c.create_image(33, 32, image=self.header_icon, tags="header")
        else:
            c.create_oval(16, 15, 50, 49, fill=PANEL, outline="", tags="header")
            c.create_text(33, 32, text="♫", font=(FONT, 13), fill=ACCENT, tags="header")
        tr = self.track
        c.create_text(62, 16, anchor="nw", text=tr["title"] if tr else "Lyric Spotify",
                      font=(FONT, 12, "bold"), fill=FG, width=w - 80, tags="header")
        c.create_text(62, 37, anchor="nw", text=tr["artist"] if tr else t("waiting"),
                      font=(FONT, 10), fill=FG_DIM, width=w - 80, tags="header")
        if self.ai and self.ai_status:
            c.create_text(w - 14, 16, anchor="ne", text="✦ " + self.i18n_text(self.ai_status), font=(FONT, 9),
                          fill=ACCENT, tags="header")
        c.create_rectangle(0, HEADER_H - 2, w, HEADER_H, fill=TRACK_BAR, outline="", tags="header")
        c.create_rectangle(0, HEADER_H - 2, 0, HEADER_H, fill=ACCENT, outline="", tags=("header", "progress"))

        # thanh công cụ: chỉ hiện khi rê chuột
        btns = self.toolbar_buttons()
        left = w - 12 - len(btns) * 34
        c.create_rectangle(left - 10, 0, w, HEADER_H - 2, fill=BG, outline="", tags="toolbar")
        for i, (name, glyph, tip, action) in enumerate(btns):
            cx = w - 29 - i * 34
            tag = f"btn_{name}"
            c.create_oval(cx - 15, 17, cx + 15, 47, fill=BG, outline="", tags=("toolbar", "btn", tag, tag + "_bg"))
            color = ACCENT if name == "glass" and self.cfg["glass"] else FG_DIM
            c.create_text(cx, 32, text=glyph, font=(ICON_FONT, 11), fill=color,
                          tags=("toolbar", "btn", tag, tag + "_fg"))
            c.tag_bind(tag, "<Button-1>", lambda e, a=action: a())
            c.tag_bind(tag, "<Enter>", lambda e, t=tag, tp=tip: self.btn_hover(t, tp, True))
            c.tag_bind(tag, "<Leave>", lambda e, t=tag: self.btn_hover(t, "", False))
        c.create_text(w - 14, HEADER_H + 10, anchor="ne", text="", font=(FONT, 9), fill=FG_DIM, tags="tip")

        # che dòng lời bị cắt ở mép dưới
        c.create_rectangle(0, h - 22, w, h, fill=BG, outline="", tags="bottommask")
        # góc dưới: thời gian + tay nắm đổi kích thước (chỉ hiện khi rê chuột)
        c.create_text(14, h - 8, anchor="sw", text="", font=(FONT, 9), fill=FG_DIM, tags=("footer", "time"))
        c.create_text(w - 4, h - 3, anchor="se", text="", font=(ICON_FONT, 9),
                      fill=GRIP, tags="footer")
        # thông báo nhanh
        c.create_rectangle(0, 0, 0, 0, fill=PANEL, outline="", tags=("toast", "toastbg"))
        c.create_text(w / 2, HEADER_H + 22, text="", font=(FONT, 10), fill=FG, tags=("toast", "toasttext"))
        self.apply_mode()

    def apply_mode(self):
        c = self.canvas
        idle = self.glass_idle()
        c.configure(bg=KEY if idle else BG)
        c.itemconfigure("header", state="hidden" if idle else "normal")
        c.itemconfigure("bottommask", state="hidden" if idle else "normal")
        ui = "normal" if self.hover else "hidden"
        c.itemconfigure("toolbar", state=ui)
        c.itemconfigure("footer", state=ui)
        c.itemconfigure("tip", state=ui)
        c.itemconfigure("btn_glass_fg", fill=ACCENT if self.cfg["glass"] else FG_DIM)
        self.cur = None  # tô màu lại theo bảng màu mới
        self.recolor()
        self.raise_overlays()

    def raise_overlays(self):
        for tag in ("header", "bottommask", "toolbar", "tip", "footer", "toast"):
            self.canvas.tag_raise(tag)

    def btn_hover(self, tag, tip, on):
        self.canvas.itemconfigure(tag + "_bg", fill=PANEL if on else BG)
        if not ("glass" in tag and self.cfg["glass"]):
            self.canvas.itemconfigure(tag + "_fg", fill=FG if on else FG_DIM)
        self.canvas.itemconfigure("tip", text=tip)
        self.canvas.configure(cursor="hand2" if on else "")

    def toast(self, text):
        c = self.canvas
        c.itemconfigure("toasttext", text=text, state="normal")
        x1, y1, x2, y2 = c.bbox("toasttext")
        c.coords("toastbg", x1 - 12, y1 - 6, x2 + 12, y2 + 6)
        c.itemconfigure("toastbg", state="normal")
        c.tag_raise("toast")
        if self.toast_job:
            self.root.after_cancel(self.toast_job)
        self.toast_job = self.root.after(1500, lambda: c.itemconfigure("toast", state="hidden"))

    def recolor(self):
        if not self.items or not self.lyrics:
            return
        pal = self.palette()
        idx = self.cur if self.cur is not None else -1
        for i, it in enumerate(self.items):
            if self.lyrics["kind"] != "synced":
                d = 1
            else:
                d = min(abs(i - idx), len(pal) - 1) if idx >= 0 else min(i + 1, len(pal) - 1)
            self.canvas.itemconfigure(it, fill=pal[d])

    def center_y(self):
        """Dòng đang hát nằm chính giữa vùng lời (giữa thanh tiêu đề và mép dưới)."""
        h = self.canvas.winfo_height()
        return (HEADER_H + h - 22) / 2

    def target_scroll(self, idx):
        if not self.ys:
            return 0.0
        i = max(idx, 0)
        return self.ys[i] + self.hs[i] / 2 - self.center_y()

    def scroll_to(self, target, instant=False):
        """Cuộn mượt theo thời gian (ease-out), không phụ thuộc tốc độ khung hình."""
        now = time.perf_counter()
        if not instant and self.manual is not None:
            if time.monotonic() < self.manual_until:
                target = self.manual
            else:
                self.manual = None
        if instant:
            self.anim = None
            new = target
        else:
            if self.anim is None or abs(self.anim[1] - target) > 0.5:
                if abs(target - self.scroll) < 3:  # thay đổi rất nhỏ (cuộn liên tục) -> đi thẳng
                    self.anim = None
                    new = target
                else:
                    dur = 0.22 if self.manual is not None else 0.45
                    self.anim = (self.scroll, target, now, dur)
            if self.anim:
                start, end, t0, dur = self.anim
                p = min(1.0, (now - t0) / dur)
                new = start + (end - start) * (1 - (1 - p) ** 3)
                if p >= 1.0:
                    self.anim = None
        self.scroll = new
        px = round(new)
        if px != self.scroll_px:
            self.canvas.move("lyric", 0, self.scroll_px - px)
            self.scroll_px = px

    @staticmethod
    def i18n_text(msg):
        key, kw = msg
        if key == "raw":
            return kw["text"]
        return t(key, **kw) if key else ""

    def message_text(self):
        return self.i18n_text(self.message)

    def set_message(self, key, **kw):
        if (key, kw) != self.message or self.lyrics is not None:
            self.message = (key, kw)
            self.lyrics, self.times = None, []
            self.relayout()

    def tick(self):
        try:
            self.update_frame()
            if self.taskbar:
                self.taskbar.update(*self.taskbar_text())
        except Exception:  # noqa: BLE001 - ghi lỗi ra file thay vì làm treo app (pythonw không có console)
            log_exception()
        finally:
            busy = self.state.snapshot()[2] or self.anim is not None or self.manual is not None
            self.root.after(16 if busy else 120, self.tick)  # ~60 fps khi phát, nhẹ máy khi dừng

    def update_progress(self, track, pos):
        dur = (track or {}).get("duration") or 0
        w = self.canvas.winfo_width()
        frac = min(max(pos / dur, 0.0), 1.0) if dur else 0.0
        self.canvas.coords("progress", 0, HEADER_H - 2, w * frac, HEADER_H)
        if dur:
            p, d = int(pos), int(dur)
            text = f"{p // 60}:{p % 60:02d} / {d // 60}:{d % 60:02d}"
            if text != self.last_time_text:
                self.last_time_text = text
                self.canvas.itemconfigure("time", text=text)

    def update_frame(self):
        track, pos, playing, error = self.state.snapshot()

        key = (track["title"], track["artist"]) if track else None
        if key != self.track_key:
            self.stop_ai()
            self.track_key, self.track = key, track
            is_ad = bool(track) and (not track["artist"] or track["title"].lower() in ("advertisement", "spotify"))
            self.message = (("ad", {}) if is_ad else ("searching", {}) if track else
                            ("raw", {"text": error}) if error else ("open_spotify", {}))
            self.lyrics, self.times = None, []
            self.fetch_token += 1
            self.retries.pop(key, None)
            if track and not is_ad:
                self.start_fetch(track)
            self.relayout()
            return

        self.update_progress(track, pos)

        result = None
        while True:
            try:
                token, res = self.results.get_nowait()
            except queue.Empty:
                break
            if token == self.fetch_token:
                result = res
        if result is not None:
            kind = result["kind"]
            if kind in ("synced", "plain"):
                self.stop_ai(save=False)
                self.message = ("", {})
                self.lyrics = result
                self.times = [t for t, _ in result["lines"]]
                self.relayout()
            else:
                tries = self.retries.get(self.track_key, 0)
                if kind == "error" and tries >= 5:
                    kind = "none"
                if kind == "error":  # thử lại nguồn lời sau 15 giây, không xoá lời AI đang chép
                    self.retries[self.track_key] = tries + 1
                    token = self.fetch_token
                    self.root.after(15000, lambda: self.start_fetch(self.track)
                                    if token == self.fetch_token and self.track else None)
                if kind != "instrumental" and self.cfg["ai_enabled"] and transcriber.ready(self.cfg["ai_model"]):
                    if not self.ai:
                        self.start_ai()
                    return
                if kind == "none" and self.cfg["ai_enabled"] and transcriber.available():
                    # có thư viện AI nhưng thiếu mô hình: báo để người dùng tự tải, không tải ngầm
                    self.set_message("not_found_ai_partial")
                    return
                if kind == "error":
                    self.set_message("busy", n=tries + 1)
                else:
                    self.set_message("not_found" if kind == "none" else "instrumental")

        self.drain_ai()
        if not self.lyrics or not self.items:
            return

        if self.lyrics["kind"] == "synced":
            idx = bisect.bisect_right(self.times, pos) - 1
            if idx != self.cur:
                self.cur = idx
                self.recolor()
            self.scroll_to(self.target_scroll(idx))
        else:
            # lời không đồng bộ: cuộn theo tỉ lệ thời lượng bài
            dur = (track or {}).get("duration") or 0
            frac = min(max(pos / dur, 0.0), 1.0) if dur else 0.0
            total = self.ys[-1] + self.hs[-1]
            visible = self.canvas.winfo_height() - HEADER_H
            self.scroll_to(frac * max(total - visible * 0.5, 0) - HEADER_H - 10)

    def run(self):
        self.root.mainloop()


LOG_PATH = os.path.join(os.path.expanduser("~"), ".spotify_lyrics.log")


def log_exception(exc=None):
    import traceback
    try:
        text = "".join(traceback.format_exception(*exc)) if exc else traceback.format_exc()
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + text + "\n")
    except OSError:
        pass


def selftest_ai():
    """LyricSpotify.exe --selftest-ai : kiểm tra phần AI (ghi kết quả vào file log)."""
    out = []
    try:
        import numpy as np
        out.append(f"AI available={transcriber.available()} separation={transcriber.separation_available()}")
        model = transcriber.get_model("small")
        segs, info = model.transcribe(np.zeros(16000, np.float32), language="vi")
        list(segs)
        out.append("whisper OK")
        sep = transcriber.get_separator()
        out.append(f"demucs OK, vocals shape={sep(np.zeros(16000 * 3, np.float32)).shape}" if sep else "demucs: not available")
        transcriber.release_separator()
    except Exception:  # noqa: BLE001
        import traceback
        out.append(traceback.format_exc())
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write("[selftest-ai] " + " | ".join(out) + "\n")


def main():
    # bản exe không có console: thư viện in ra stdout/stderr (thanh tiến trình tải mô hình) không bị lỗi
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    # trình cài đặt truyền ngôn ngữ đã chọn: dùng làm ngôn ngữ app ở lần chạy đầu tiên
    lang = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--lang=")), None)
    if lang and not os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({"ui_lang": "en" if lang.startswith("en") else "vi"}, f)
        except OSError:
            pass
    if "--selftest-ai" in sys.argv:
        selftest_ai()
        return
    if "--install-ai" in sys.argv:  # gọi từ trình cài đặt: tải phần AI có cửa sổ tiến trình
        import ai_setup
        sys.exit(ai_setup.run(load_config(), with_demucs="--demucs" in sys.argv))
    try:  # icon riêng trên taskbar thay vì icon Python
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LyricSpotify.App")
    except Exception:  # noqa: BLE001
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001
        pass
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:  # noqa: BLE001
        pass
    state = PlayerState()
    threading.Thread(target=lambda: asyncio.run(poll_player(state)), daemon=True).start()
    try:
        LyricsWindow(state).run()
    finally:
        try:
            ctypes.windll.winmm.timeEndPeriod(1)
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()  # bản exe: tiến trình con (Demucs) chạy đúng
    main()
