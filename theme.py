"""Bảng màu giao diện tối / sáng (và theo cài đặt sáng/tối của Windows)."""

THEMES = {
    "dark": {
        "BG": "#121212", "PANEL": "#262626", "PANEL2": "#1e1e1e", "HOVER": "#2a2a2a",
        "TRACK_BAR": "#2a2a2a", "FG": "#ffffff", "FG_DIM": "#a7a7a7", "FG_OFF": "#5a5a5a",
        "ACCENT": "#1ed760", "ACCENT_HOVER": "#3be477", "ON_ACCENT": "#000000",
        "SELECT": "#3a3a3a", "GRIP": "#4a4a4a",
        "KEY": "#010203",  # màu được làm trong suốt ở chế độ nền trong suốt (gần màu nền)
        # màu dòng lời theo khoảng cách tới dòng đang hát (0 = đang hát)
        "LINE_SOLID": ["#ffffff", "#b3b3b3", "#7c7c7c", "#5c5c5c", "#454545"],
        "LINE_GLASS": ["#ffffff", "#a6a6a6", "#8f8f8f", "#7d7d7d", "#6e6e6e"],
        "LINE_FADED": ["#ffffff", "#8c8c8c", "#696969", "#525252", "#424242"],
    },
    "light": {
        "BG": "#f7f7f7", "PANEL": "#e6e6e6", "PANEL2": "#ececec", "HOVER": "#d9d9d9",
        "TRACK_BAR": "#dcdcdc", "FG": "#111111", "FG_DIM": "#5c5c5c", "FG_OFF": "#b3b3b3",
        "ACCENT": "#15994a", "ACCENT_HOVER": "#11843f", "ON_ACCENT": "#ffffff",
        "SELECT": "#c9e6d3", "GRIP": "#b0b0b0",
        # nền trong suốt dùng chữ trắng như giao diện tối (đọc được trên hình nền tối lẫn sáng,
        # không bị viền trắng quanh chữ đen)
        "KEY": "#010203",
        "LINE_SOLID": ["#000000", "#4d4d4d", "#7f7f7f", "#a3a3a3", "#bfbfbf"],
        "LINE_GLASS": ["#ffffff", "#a6a6a6", "#8f8f8f", "#7d7d7d", "#6e6e6e"],
        "LINE_FADED": ["#000000", "#666666", "#8f8f8f", "#adadad", "#c4c4c4"],
    },
}
CHOICES = ["system", "dark", "light"]


def windows_theme():
    """'light' hoặc 'dark' theo Settings → Personalization → Colors của Windows."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return "light" if winreg.QueryValueEx(k, "AppsUseLightTheme")[0] else "dark"
    except OSError:
        return "dark"


def resolve(choice):
    return windows_theme() if choice == "system" else (choice if choice in THEMES else "dark")


def colors(choice):
    return THEMES[resolve(choice)]
