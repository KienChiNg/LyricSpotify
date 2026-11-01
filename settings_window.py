"""Cửa sổ Cài đặt: ngôn ngữ, giao diện chữ, lời đã lưu, AI chép lời."""

import os
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

import transcriber
from i18n import UI_LANGS, t

BG, PANEL, FG, FG_DIM, FG_OFF, ACCENT = "#121212", "#1e1e1e", "#ffffff", "#a7a7a7", "#5a5a5a", "#1ed760"
FONT = "Segoe UI"
FONT_CHOICES = ["Segoe UI", "Arial", "Tahoma", "Verdana", "Calibri", "Cambria", "Georgia",
                "Times New Roman", "Trebuchet MS", "Roboto", "Montserrat", "Be Vietnam Pro",
                "Inter", "Nunito", "Quicksand"]


class SettingsWindow:
    def __init__(self, app):
        self.app = app
        cfg = app.cfg
        w = self.win = tk.Toplevel(app.root, bg=BG)
        w.title(t("settings_title"))
        w.geometry("460x720")
        w.minsize(420, 420)
        w.attributes("-topmost", True)
        w.bind("<Escape>", lambda e: self.close())
        w.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(w)
        style.theme_use("clam")
        style.configure("Dark.Horizontal.TScale", background=ACCENT, troughcolor=PANEL,
                        bordercolor=BG, lightcolor=ACCENT, darkcolor=ACCENT, gripcount=0)

        # thanh nút ghim ở đáy, phần trên cuộn được
        bar = tk.Frame(w, bg=BG, pady=12)
        bar.pack(side="bottom", fill="x", padx=20)
        tk.Frame(w, bg="#2a2a2a", height=1).pack(side="bottom", fill="x")
        self.button(bar, t("done"), self.close, primary=True).pack(side="right")
        self.button(bar, t("reset_defaults"), self.reset).pack(side="left")

        canvas = tk.Canvas(w, bg=BG, highlightthickness=0)
        body = tk.Frame(canvas, bg=BG)
        canvas.create_window((0, 0), window=body, anchor="nw", tags="body")
        canvas.pack(fill="both", expand=True)
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure("body", width=e.width))
        w.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-e.delta // 120, "units"))
        self.body = body

        # ---- Ngôn ngữ: một ô duy nhất, đổi toàn bộ chữ của app ----
        self.section("Ngôn ngữ / Language")
        names = list(UI_LANGS.values())
        self.ui_lang = tk.StringVar(value=UI_LANGS.get(cfg["ui_lang"], names[0]))
        self.choice("", self.ui_lang, names, self.on_ui_lang)

        # ---- Giao diện ----
        self.section(t("sec_ui"))
        self.font_size = tk.IntVar(value=cfg["font"])
        self.slider(t("font_size"), self.font_size, 10, 40, self.on_font)
        installed = set(tkfont.families())
        fonts = [f for f in FONT_CHOICES if f in installed] or ["Segoe UI"]
        self.family = tk.StringVar(value=cfg["font_family"] if cfg["font_family"] in fonts else fonts[0])
        self.choice(t("font_family"), self.family, fonts, self.on_font)
        self.bold = tk.BooleanVar(value=cfg["bold"])
        self.check(t("bold"), self.bold, self.on_font)
        self.alpha = tk.IntVar(value=round(cfg["alpha"] * 100))
        self.slider(t("alpha"), self.alpha, 15, 100, lambda: app.set_alpha(self.alpha.get() / 100))
        self.glass = tk.BooleanVar(value=cfg["glass"])
        self.check(t("glass"), self.glass, lambda: app.toggle_glass(self.glass.get()))

        # ---- Lời bài hát đã lưu ----
        self.section(t("sec_lyrics"))
        self.note(t("lyrics_note"))
        row = tk.Frame(body, bg=BG)
        row.pack(fill="x", padx=24, pady=(6, 0))
        self.button(row, t("open_folder"), app.open_lyrics_dir).pack(side="left")
        row2 = tk.Frame(body, bg=BG)
        row2.pack(fill="x", padx=24, pady=(6, 0))
        self.clear_ai_btn = self.button(row2, "", self.clear_ai_lyrics)
        self.clear_ai_btn.pack(side="left")
        self.button(row2, t("clear_cache"), self.clear_cache).pack(side="left", padx=8)
        self.update_counts()

        # ---- AI chép lời ----
        self.section(t("sec_ai"))
        if not transcriber.available():
            self.note(t("ai_missing"))
        self.ai_on = tk.BooleanVar(value=cfg["ai_enabled"])
        self.check(t("ai_enable"), self.ai_on, self.on_ai)
        self.ai_widgets = []   # làm mờ khi tắt AI
        self.label(t("ai_model"), group=self.ai_widgets)
        self.model = tk.StringVar(value=cfg["ai_model"])
        for key in transcriber.MODELS:
            mark = "  ✓ " + t("downloaded") if transcriber.model_downloaded(key) else ""
            self.radio(t(f"model_{key}") + mark, self.model, key, self.on_ai)
        self.separate = tk.BooleanVar(value=cfg["ai_separate"])
        self.check(t("ai_separate"), self.separate, self.on_ai, group=self.ai_widgets)
        if not transcriber.separation_available():
            self.note(t("separate_missing"))

        # nguồn âm thanh AI nghe
        self.label(t("ai_device"), group=self.ai_widgets)
        devices = [t("default_device")] + transcriber.output_devices()
        self.device = tk.StringVar(value=cfg["ai_device"] or t("default_device"))
        self.device_menu = self.choice("", self.device, devices, self.on_ai)
        self.ai_widgets.append(self.device_menu)
        self.only_spotify = tk.BooleanVar(value=cfg["ai_only_spotify"])
        self.only_spotify_box = self.check(t("only_spotify"), self.only_spotify, self.on_ai)
        self.note(t("cable_note"))
        tk.Frame(body, bg=BG, height=12).pack()
        self.refresh_states()

    # ---- widget helpers --------------------------------------------------- #

    def section(self, text):
        tk.Label(self.body, text=text, bg=BG, fg=FG, font=(FONT, 13, "bold"),
                 anchor="w").pack(fill="x", padx=20, pady=(18, 6))

    def label(self, text, group=None):
        lb = tk.Label(self.body, text=text, bg=BG, fg=FG_DIM, font=(FONT, 9, "bold"), anchor="w")
        lb.pack(fill="x", padx=24, pady=(10, 2))
        if group is not None:
            group.append(lb)
        return lb

    def note(self, text):
        tk.Label(self.body, text=text, bg=BG, fg=FG_DIM, font=(FONT, 9), anchor="w", justify="left",
                 wraplength=390).pack(fill="x", padx=24, pady=(4, 2))

    def button(self, parent, text, command, primary=False):
        if primary:
            colors = dict(bg=ACCENT, fg="#000000", activebackground="#3be477", activeforeground="#000000")
        else:
            colors = dict(bg=PANEL, fg=FG, activebackground="#2a2a2a", activeforeground=FG)
        return tk.Button(parent, text=text, command=command, relief="flat", bd=0, cursor="hand2",
                         font=(FONT, 10, "bold" if primary else "normal"), padx=14, pady=5, **colors)

    def slider(self, text, var, lo, hi, command):
        self.label(text)
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="x", padx=24, pady=2)
        value = tk.Label(row, text=str(var.get()), bg=BG, fg=FG, font=(FONT, 10), width=4, anchor="e")
        value.pack(side="right")

        def changed(_v):
            var.set(round(float(_v)))
            value.configure(text=str(var.get()))
            command()

        scale = ttk.Scale(row, from_=lo, to=hi, orient="horizontal", style="Dark.Horizontal.TScale",
                          value=var.get(), command=changed)
        scale.pack(side="left", fill="x", expand=True)

    def check(self, text, var, command, group=None):
        cb = tk.Checkbutton(self.body, text=text, variable=var, command=lambda: (command(), self.refresh_states()),
                            bg=BG, fg=FG, selectcolor=PANEL, activebackground=BG, activeforeground=FG,
                            disabledforeground=FG_OFF, font=(FONT, 10), anchor="w", bd=0,
                            highlightthickness=0, wraplength=380, justify="left")
        cb.pack(fill="x", padx=22, pady=3)
        if group is not None:
            group.append(cb)
        return cb

    def radio(self, text, var, value, command):
        rb = tk.Radiobutton(self.body, text=text, variable=var, value=value, command=command, bg=BG, fg=FG,
                            selectcolor=PANEL, activebackground=BG, activeforeground=FG,
                            disabledforeground=FG_OFF, font=(FONT, 10), anchor="w", bd=0,
                            highlightthickness=0, wraplength=380, justify="left")
        rb.pack(fill="x", padx=22)
        self.ai_widgets.append(rb)
        return rb

    def choice(self, text, var, values, command):
        if text:
            self.label(text)
        om = tk.OptionMenu(self.body, var, *values,
                           command=lambda _v: (command(), self.refresh_states()))
        om.configure(bg=PANEL, fg=FG, activebackground="#2a2a2a", activeforeground=FG,
                     disabledforeground=FG_OFF, highlightthickness=0, relief="flat", bd=0,
                     font=(FONT, 10), anchor="w")
        om["menu"].configure(bg=PANEL, fg=FG, activebackground=ACCENT, activeforeground="#000000",
                             font=(FONT, 10))
        om.pack(fill="x", padx=24, pady=2)
        return om

    def refresh_states(self):
        """Làm mờ tuỳ chọn không còn tác dụng."""
        ai = self.ai_on.get()
        for wdg in self.ai_widgets:
            if isinstance(wdg, tk.Label):
                wdg.configure(fg=FG_DIM if ai else FG_OFF)
            else:
                wdg.configure(state="normal" if ai else "disabled")
        default_dev = self.device.get() == t("default_device")
        self.only_spotify_box.configure(state="normal" if ai and default_dev else "disabled")

    # ---- lời đã lưu --------------------------------------------------------- #

    @staticmethod
    def _files(folder, exts):
        try:
            return [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(exts)]
        except OSError:
            return []

    def update_counts(self):
        n = len(self._files(self.app.ai_dir(), (".lrc",)))
        self.clear_ai_btn.configure(text=t("clear_ai", n=n), state="normal" if n else "disabled")

    def clear_ai_lyrics(self):
        files = self._files(self.app.ai_dir(), (".lrc",))
        if files and messagebox.askyesno(t("clear_ai", n=len(files)), t("confirm_clear_ai"), parent=self.win):
            for f in files:
                os.remove(f)
            self.update_counts()
            self.app.refetch()

    def clear_cache(self):
        files = self._files(self.app.cache_dir(), (".json",))
        if messagebox.askyesno(t("clear_cache"), t("confirm_clear_cache", n=len(files)), parent=self.win):
            for f in files:
                os.remove(f)
            self.app.refetch()

    # ---- áp dụng ---------------------------------------------------------- #

    def on_font(self):
        self.app.set_text_style(self.font_size.get(), self.family.get(), self.bold.get())

    def on_ai(self):
        device = self.device.get()
        self.app.set_ai(enabled=self.ai_on.get(), model=self.model.get(),
                        device="" if device == t("default_device") else device,
                        only_spotify=self.only_spotify.get(), separate=self.separate.get())

    def on_ui_lang(self):
        code = next(k for k, v in UI_LANGS.items() if v == self.ui_lang.get())
        if code != self.app.cfg["ui_lang"]:
            self.app.root.after(10, lambda: self.app.set_ui_lang(code))

    def reset(self):
        if messagebox.askyesno(t("reset_defaults"), t("confirm_reset"), parent=self.win):
            self.app.root.after(10, self.app.reset_settings)

    def close(self):
        self.app.settings_win = None
        self.app.save_config()
        self.win.destroy()
