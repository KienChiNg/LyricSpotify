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
        "font_size": "Cỡ chữ lời",
        "font_family": "Font chữ",
        "bold": "Chữ đậm",
        "alpha": "Độ đậm cửa sổ (%)",
        "glass": "Nền trong suốt (chỉ hiện chữ)",
        "sec_ai": "AI chép lời (khi không tìm thấy lời)",
        "ai_missing": "Chưa cài thư viện AI. Chạy: pip install faster-whisper soundcard pycaw",
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
        "separate_missing": "Cần PyTorch (CUDA) + demucs để tách giọng hát.",
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
        "font_size": "Lyrics font size",
        "font_family": "Font",
        "bold": "Bold text",
        "alpha": "Window opacity (%)",
        "glass": "Transparent background (text only)",
        "sec_ai": "AI transcription (when no lyrics are found)",
        "ai_missing": "AI libraries not installed. Run: pip install faster-whisper soundcard pycaw",
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
        "separate_missing": "Vocal separation needs PyTorch (CUDA) + demucs.",
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
