"""Chữ hiển thị của app theo ngôn ngữ giao diện (vi / en)."""

LANG = {"code": "vi"}

STRINGS = {
    "vi": {
        # menu + thanh nút
        "menu_settings": "Cài đặt…",
        "menu_glass": "Nền trong suốt (chỉ hiện chữ)    T",
        "menu_edit": "Thêm / sửa lời bài này…",
        "menu_reload": "Tải lại lời",
        "menu_folder": "Mở thư mục lời",
        "menu_taskbar": "Lời trên thanh taskbar",
        "btn_min": "Thu nhỏ",
        "btn_max": "Phóng to",
        "btn_restore": "Khôi phục kích thước",
        "taskbar_mode": "Hiện lời chạy trên thanh taskbar",
        "taskbar_hide_main": "Ẩn cửa sổ lời lớn khi đang hiện lời trên taskbar "
                             "(bấm vào chữ trên taskbar để mở lại)",
        "taskbar_width": "Độ rộng dải lời trên taskbar (px)",
        "menu_quit": "Thoát    Esc",
        "btn_close": "Đóng",
        "btn_more": "Thêm tuỳ chọn",
        "btn_edit": "Thêm / sửa lời",
        "btn_glass": "Nền trong suốt",
        "btn_settings": "Cài đặt",
        # thông báo
        "toast_glass_on": "Nền trong suốt: bật (rê chuột vào để hiện nút)",
        "toast_glass_off": "Nền trong suốt: tắt",
        "toast_alpha": "Độ đậm: {pct}%",
        "toast_no_track": "Chưa có bài nào đang phát",
        "toast_saved": "Đã lưu lời",
        # trạng thái lời
        "waiting": "Đang chờ Spotify…",
        "open_spotify": "Mở app Spotify và phát một bài hát.",
        "searching": "Đang tìm lời bài hát…",
        "ad": "Quảng cáo…",
        "not_found": "Không tìm thấy lời cho bài này.\nChuột phải → Thêm / sửa lời để tự thêm.",
        "instrumental": "Nhạc không lời",
        "busy": "Nguồn lời đang bận, tự thử lại sau 15 giây… ({n}/5)",
        "ai_fallback": "Không tìm thấy lời trên mạng.\nAI đang nghe bài hát và chép lời…",
        # AI
        "ai_preparing": "AI đang chuẩn bị…",
        "ai_loading": "Đang tải mô hình AI {name}… (lần đầu sẽ lâu)",
        "ai_listening": "AI đang nghe và chép lời…",
        "ai_paused": "AI tạm dừng: {app} đang phát tiếng",
        "ai_no_device": "Không thấy thiết bị \"{name}\" – kiểm tra Cài đặt",
        "ai_capture_err": "Không thu được âm thanh máy: {err}",
        "ai_model_err": "Không tải được mô hình AI: {err}",
        # cửa sổ sửa lời
        "edit_title": "Lời bài hát · {title}",
        "edit_hint": "Dán lời vào ô dưới. Dòng bắt đầu bằng [mm:ss.xx] sẽ chạy theo nhạc,\n"
                     "không có thời gian thì hiện lời thường và tự cuộn theo bài.",
        "save": "Lưu",
        "cancel": "Huỷ",
        "open_folder": "Mở thư mục lời",
        # cài đặt
        "settings_title": "Cài đặt · Lyric Spotify",
        "sec_ui": "Giao diện",
        "theme": "Giao diện màu",
        "theme_system": "Theo Windows",
        "theme_dark": "Tối",
        "theme_light": "Sáng",
        "font_size": "Cỡ chữ lời",
        "font_family": "Font chữ",
        "bold": "Chữ đậm",
        "alpha": "Độ đậm cửa sổ (%)",
        "glass": "Nền trong suốt (chỉ hiện chữ)",
        "sec_ai": "AI chép lời (khi không tìm thấy lời)",
        "ai_install_title": "Chưa cài phần AI",
        "ai_install_note": "Phần AI không có trong bản cài gốc để app nhẹ. Bấm nút để tải "
                           "(~3 GB, cần card NVIDIA). Mô hình nhận dạng (~1.6 GB) tải thêm ở lần dùng đầu.",
        "ai_install_demucs": "Kèm tách giọng hát (Demucs, thêm ~2.5 GB, chép chính xác hơn)",
        "ai_extra_title": "Chưa cài tách giọng hát",
        "ai_extra_note": "Tải thêm Demucs + PyTorch (~2.5 GB) để AI chép lời chính xác hơn.",
        "ai_install_btn": "Tải phần AI",
        "ai_installing": "Đang tải… (có thể mất vài phút)",
        "ai_install_ok": "Đã cài xong. Khởi động lại app để dùng.",
        "ai_install_retry": "Lỗi – thử lại",
        "restart_app": "Khởi động lại app",
        "setup_title": "Đang tải phần AI chép lời",
        "setup_note": "Tải thư viện AI (~3 GB) và mô hình nhận dạng (~1.6 GB). Có thể mất 5–30 phút tuỳ mạng.",
        "setup_note_demucs": "Tải thư viện AI + tách giọng hát (~5.5 GB) và mô hình nhận dạng (~1.6 GB). "
                             "Có thể mất 10–40 phút tuỳ mạng.",
        "setup_model": "Đang tải mô hình nhận dạng (~1.6 GB)…",
        "setup_ok": "Đã cài xong phần AI.",
        "setup_fail": "Chưa tải được phần AI. Bạn có thể thử lại trong app: Cài đặt → AI chép lời.",
        "ai_enable": "Bật AI nghe nhạc và tự chép lời",
        "ai_model": "Mô hình",
        "model_small": "Nhẹ – small (~0.5 GB, kém chính xác)",
        "model_medium": "Vừa – medium (~1.5 GB)",
        "model_large-v3-turbo": "Chính xác – large-v3-turbo (~1.6 GB, khuyên dùng)",
        "ai_separate": "Tách giọng hát khỏi nhạc nền trước khi chép (chính xác hơn)",
        "downloaded": "đã tải",
        "sec_lyrics": "Lời bài hát đã lưu",
        "lyrics_note": "Lời bạn tự thêm nằm trong thư mục lời và luôn được ưu tiên. "
                       "Lời AI chép trọn bài nằm trong thư mục con \"ai\".",
        "clear_ai": "Xoá lời AI đã lưu ({n})",
        "confirm_clear_ai": "Xoá tất cả lời do AI chép? Lời bạn tự thêm không bị xoá.",
        "clear_cache": "Xoá bộ nhớ đệm lời",
        "confirm_clear_cache": "Xoá {n} lời đã tải từ mạng? App sẽ tải lại khi cần "
                               "(hữu ích khi bị hiện nhầm lời bài khác).",
        "reset_defaults": "Khôi phục mặc định",
        "confirm_reset": "Đưa mọi cài đặt về mặc định? (Vị trí cửa sổ được giữ nguyên.)",
        "ai_device": "Thiết bị AI nghe",
        "default_device": "Loa mặc định",
        "only_spotify": "Tạm dừng khi app khác đang phát tiếng (với loa mặc định)",
        "cable_note": "Thu riêng tiếng Spotify: cài cáp âm thanh ảo (vd: VB-CABLE), vào Windows Settings → "
                      "Sound → App volume and device preferences → đặt Output của Spotify là "
                      "\"CABLE Input\", rồi chọn \"CABLE Input\" ở ô Thiết bị AI nghe. Muốn vẫn nghe được "
                      "nhạc: Control Panel → Sound → Recording → CABLE Output → Properties → Listen → "
                      "tick \"Listen to this device\" và chọn loa của bạn.",
        "done": "Xong",
    },
    "en": {
        "menu_settings": "Settings…",
        "menu_glass": "Transparent background (text only)    T",
        "menu_edit": "Add / edit lyrics for this song…",
        "menu_reload": "Reload lyrics",
        "menu_folder": "Open lyrics folder",
        "menu_taskbar": "Lyrics on the taskbar",
        "btn_min": "Minimize",
        "btn_max": "Maximize",
        "btn_restore": "Restore size",
        "taskbar_mode": "Show lyrics on the taskbar",
        "taskbar_hide_main": "Hide the big lyrics window while lyrics are on the taskbar "
                             "(click the taskbar lyrics to reopen it)",
        "taskbar_width": "Taskbar lyrics width (px)",
        "menu_quit": "Quit    Esc",
        "btn_close": "Close",
        "btn_more": "More options",
        "btn_edit": "Add / edit lyrics",
        "btn_glass": "Transparent background",
        "btn_settings": "Settings",
        "toast_glass_on": "Transparent background: on (hover to show buttons)",
        "toast_glass_off": "Transparent background: off",
        "toast_alpha": "Opacity: {pct}%",
        "toast_no_track": "Nothing is playing",
        "toast_saved": "Lyrics saved",
        "waiting": "Waiting for Spotify…",
        "open_spotify": "Open the Spotify app and play a song.",
        "searching": "Looking for lyrics…",
        "ad": "Advertisement…",
        "not_found": "No lyrics found for this song.\nRight-click → Add / edit lyrics to add your own.",
        "instrumental": "Instrumental",
        "busy": "Lyrics servers are busy, retrying in 15 seconds… ({n}/5)",
        "ai_fallback": "No lyrics found online.\nAI is listening and transcribing…",
        "ai_preparing": "AI is getting ready…",
        "ai_loading": "Loading AI model {name}… (first time takes a while)",
        "ai_listening": "AI is listening and transcribing…",
        "ai_paused": "AI paused: {app} is playing sound",
        "ai_no_device": "Device \"{name}\" not found – check Settings",
        "ai_capture_err": "Cannot capture system audio: {err}",
        "ai_model_err": "Cannot load AI model: {err}",
        "edit_title": "Lyrics · {title}",
        "edit_hint": "Paste lyrics below. Lines starting with [mm:ss.xx] follow the music;\n"
                     "without timestamps they show as plain lyrics that scroll with the song.",
        "save": "Save",
        "cancel": "Cancel",
        "open_folder": "Open lyrics folder",
        "settings_title": "Settings · Lyric Spotify",
        "sec_ui": "Appearance",
        "theme": "Color theme",
        "theme_system": "Follow Windows",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "font_size": "Lyrics font size",
        "font_family": "Font",
        "bold": "Bold text",
        "alpha": "Window opacity (%)",
        "glass": "Transparent background (text only)",
        "sec_ai": "AI transcription (when no lyrics are found)",
        "ai_install_title": "AI add-on not installed",
        "ai_install_note": "The AI part is not in the base install to keep the app small. Click to download it "
                           "(~3 GB, needs an NVIDIA GPU). The speech model (~1.6 GB) downloads on first use.",
        "ai_install_demucs": "Include vocal separation (Demucs, +~2.5 GB, more accurate)",
        "ai_extra_title": "Vocal separation not installed",
        "ai_extra_note": "Download Demucs + PyTorch (~2.5 GB) for more accurate AI lyrics.",
        "ai_install_btn": "Download AI add-on",
        "ai_installing": "Downloading… (may take a few minutes)",
        "ai_install_ok": "Installed. Restart the app to use it.",
        "ai_install_retry": "Failed – try again",
        "restart_app": "Restart app",
        "setup_title": "Downloading the AI transcription add-on",
        "setup_note": "Downloading AI libraries (~3 GB) and the speech model (~1.6 GB). This may take 5–30 minutes.",
        "setup_note_demucs": "Downloading AI libraries + vocal separation (~5.5 GB) and the speech model "
                             "(~1.6 GB). This may take 10–40 minutes.",
        "setup_model": "Downloading the speech model (~1.6 GB)…",
        "setup_ok": "AI add-on installed.",
        "setup_fail": "Could not download the AI add-on. You can retry in the app: Settings → AI transcription.",
        "ai_enable": "Let AI listen and transcribe lyrics",
        "ai_model": "Model",
        "model_small": "Light – small (~0.5 GB, less accurate)",
        "model_medium": "Medium – medium (~1.5 GB)",
        "model_large-v3-turbo": "Accurate – large-v3-turbo (~1.6 GB, recommended)",
        "ai_separate": "Separate vocals from the music before transcribing (more accurate)",
        "downloaded": "downloaded",
        "sec_lyrics": "Saved lyrics",
        "lyrics_note": "Lyrics you add live in the lyrics folder and always take priority. "
                       "Full-song AI transcriptions are kept in its \"ai\" subfolder.",
        "clear_ai": "Delete saved AI lyrics ({n})",
        "confirm_clear_ai": "Delete all AI-transcribed lyrics? Lyrics you added are kept.",
        "clear_cache": "Clear lyrics cache",
        "confirm_clear_cache": "Delete {n} lyrics downloaded from the internet? They are fetched again "
                               "when needed (useful if the wrong song's lyrics were shown).",
        "reset_defaults": "Reset to defaults",
        "confirm_reset": "Reset every setting to its default? (Window position is kept.)",
        "ai_device": "Device the AI listens to",
        "default_device": "Default speakers",
        "only_spotify": "Pause while other apps are playing sound (default speakers)",
        "cable_note": "Capture Spotify only: install a virtual audio cable (e.g. VB-CABLE), open Windows "
                      "Settings → Sound → App volume and device preferences → set Spotify's Output to "
                      "\"CABLE Input\", then pick \"CABLE Input\" as the device above. To keep hearing the "
                      "music: Control Panel → Sound → Recording → CABLE Output → Properties → Listen → "
                      "tick \"Listen to this device\" and choose your speakers.",
        "done": "Done",
    },
}

UI_LANGS = {"vi": "Tiếng Việt", "en": "English"}


def set_lang(code):
    LANG["code"] = code if code in STRINGS else "vi"


def t(key, **kw):
    text = STRINGS[LANG["code"]].get(key) or STRINGS["vi"].get(key, key)
    return text.format(**kw) if kw else text
