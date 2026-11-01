# Lyric Spotify 🎶

<img width="418" height="418" alt="Neon Spotify Lyrics Icon" src="https://github.com/user-attachments/assets/7437bd02-8591-4c95-a9a0-690ddf8e3878" />

Cửa sổ nổi trên màn hình Windows hiển thị **lời bài hát chạy theo nhạc** của bài đang phát trên app Spotify.
Không cần đăng nhập hay API key. Khi không tìm thấy lời, **AI có thể tự nghe và chép lời** (tuỳ chọn, cần card NVIDIA).

*A floating Windows overlay that shows time-synced lyrics for the song playing in the Spotify desktop app. Interface in Vietnamese and English.*

## Tính năng

- Lấy bài đang phát từ Windows Media Controls: không cần tài khoản lập trình viên Spotify.
- Tìm lời chạy theo nhạc từ **NetEase Cloud Music** (nhiều nhạc Việt / châu Á) và **LRCLIB**, có lưu đệm trên máy.
- Tự thêm hoặc sửa lời: chuột phải → *Thêm / sửa lời*, lưu thành file `.lrc` / `.txt` trong thư mục `lyrics/`.
- **AI chép lời** (tuỳ chọn): Whisper large-v3-turbo chạy trên GPU, tách giọng hát bằng Demucs, lời hiện dần theo bài và được lưu lại khi nghe trọn bài.
- Giao diện: dòng đang hát nằm giữa và cuộn mượt; nền trong suốt chỉ hiện chữ; chỉnh độ đậm, font, cỡ chữ; tiếng Việt / English.

## Yêu cầu

- Windows 10 / 11, app **Spotify** bản desktop
- [Python 3.11+](https://www.python.org/downloads/) (khi cài, tick *Add python.exe to PATH*)
- Cho AI chép lời: card **NVIDIA** (khuyên dùng từ 6 GB VRAM), dung lượng trống khoảng 6 GB

## Cài đặt

```bash
git clone <địa chỉ repo này>
cd LyricSpotify
install.bat
```

`install.bat` cài thư viện bắt buộc, rồi hỏi bạn có muốn cài phần AI (khoảng 3 GB) và tách giọng hát Demucs (khoảng 2.5 GB) không.
Cài tay cũng được:

```bash
pip install -r requirements.txt          # bắt buộc
pip install -r requirements-ai.txt       # tuỳ chọn: AI chép lời
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install demucs                       # tuỳ chọn: tách giọng hát
```

Mô hình AI (khoảng 1.6 GB) được tải tự động ở lần đầu dùng.

## Chạy

Bấm đúp `run.bat`, hoặc chạy `pythonw spotify_lyrics.py`.

| Thao tác | Tác dụng |
|---|---|
| Rê chuột vào cửa sổ | Hiện nút: ⚙ Cài đặt · 👁 nền trong suốt · ✎ sửa lời · ⋯ menu · ✕ đóng |
| Kéo chuột trái | Di chuyển cửa sổ (kéo góc phải dưới để đổi kích thước) |
| Lăn chuột | Cuộn xem lời; 3 giây sau tự quay về dòng đang hát |
| Nhấp đúp / phím `T` | Bật / tắt nền trong suốt |
| Phím `↑` `↓` | Độ đậm cửa sổ |
| Chuột phải | Menu |
| `Esc` | Thoát |

## Ghi chú về AI chép lời

- Windows 10 không thu riêng được âm thanh của một app, nên AI **tạm dừng khi app khác đang phát tiếng**.
  Để chỉ thu tiếng Spotify: cài cáp âm thanh ảo (vd: VB-CABLE), đặt Output của Spotify là *CABLE Input*,
  rồi chọn thiết bị đó trong *Cài đặt → Thiết bị AI nghe*.
- Lời do AI chép có thể sai một số chữ; bạn sửa qua *Thêm / sửa lời* và bản bạn lưu luôn được ưu tiên.

## Dữ liệu trên máy

| Đường dẫn | Nội dung |
|---|---|
| `~/.spotify_lyrics.json` | Cài đặt |
| `~/.spotify_lyrics_cache/` | Lời đã tải từ mạng |
| `lyrics/` , `lyrics/ai/` | Lời bạn tự thêm / lời AI chép |
| `~/.spotify_lyrics.log` | Nhật ký lỗi |

## Nguồn lời & giấy phép

Lời bài hát lấy từ NetEase Cloud Music và [LRCLIB](https://lrclib.net) qua API công khai, không chính thức của NetEase.
Lời bài hát thuộc bản quyền của tác giả; app chỉ hiển thị để dùng cá nhân.
