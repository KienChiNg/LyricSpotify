"""AI nghe âm thanh máy đang phát (WASAPI loopback) và chép lời bằng Whisper (faster-whisper).

Cách làm (theo các dự án chép lời bài hát như singingwhisper, stable-ts, whisper_streaming):
  1. Tách giọng hát khỏi nhạc nền bằng Demucs (GPU) trước khi nhận dạng.
  2. Gợi ý cho Whisper tên bài + ca sĩ; chỉ chốt một từ khi 2 lần nhận dạng liên tiếp
     cho cùng kết quả (LocalAgreement) để lời ổn định, không nhảy chữ.
  3. Nghe trọn bài -> chép lại cả bài một lượt (đủ ngữ cảnh) rồi lưu .lrc.
"""

import glob
import os
import queue
import re
import site
import threading
import time
import unicodedata

import ai_runtime

ai_runtime.activate()  # thư viện AI tải thêm sau khi cài app (bản exe)

try:  # chỉ cần cho AI; app vẫn chạy khi chưa cài phần AI
    import numpy as np
except ImportError:
    np = None

SR = 16000
MODELS = ["small", "medium", "large-v3-turbo"]  # chữ hiển thị nằm trong i18n.py
MODEL_REPOS = {"small": "Systran/faster-whisper-small", "medium": "Systran/faster-whisper-medium",
               "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo"}

# Câu Whisper hay "bịa" khi gặp đoạn nhạc không lời
HALLUCINATION = re.compile(
    r"subscribe|đăng ký kênh|like và share|cảm ơn các bạn đã|hẹn gặp lại|ghiền mì gõ|"
    r"thanks for watching|thank you for watching|amara\.org|vietsub|lời bài hát|♪+$", re.I)

_model_lock = threading.Lock()
_model = {"name": None, "obj": None}
_sep_lock = threading.Lock()
_sep = {"obj": None, "failed": False}


def _setup_cuda():
    for sp in site.getsitepackages():
        for d in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
            try:
                os.add_dll_directory(d)
            except OSError:
                pass
            os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]


def output_devices():
    """Tên các thiết bị phát âm thanh (để thu lại tiếng của thiết bị đó)."""
    try:
        import soundcard as sc
        return [d.name for d in sc.all_speakers()]
    except Exception:  # noqa: BLE001
        return []


def available():
    import importlib.util
    try:
        return np is not None and all(importlib.util.find_spec(m) for m in ("faster_whisper", "soundcard"))
    except (ImportError, ValueError):
        return False


def separation_available():
    # không import torch ở tiến trình chính (xung đột cuDNN với faster-whisper)
    import importlib.util
    try:
        return all(importlib.util.find_spec(m) for m in ("demucs", "torch", "torchaudio"))
    except (ImportError, ValueError):
        return False


def model_downloaded(name):
    """Mô hình đã có sẵn trên máy (không cần tải)?"""
    try:
        from huggingface_hub import try_to_load_from_cache
        repo = MODEL_REPOS.get(name)
        return bool(repo) and isinstance(try_to_load_from_cache(repo, "model.bin"), str)
    except Exception:  # noqa: BLE001
        return False


def get_model(name, status=None):
    with _model_lock:
        if _model["name"] != name:
            _setup_cuda()
            from faster_whisper import WhisperModel
            if status:
                status("ai_loading", name=name)
            try:
                obj = WhisperModel(name, device="cuda", compute_type="float16")
            except Exception:  # noqa: BLE001 - không có GPU -> CPU
                obj = WhisperModel(name, device="cpu", compute_type="int8")
            _model.update(name=name, obj=obj)
        return _model["obj"]


class Separator:
    """Tách giọng hát (Demucs htdemucs) trên GPU. Vào/ra: mono 16 kHz float32."""

    def __init__(self):
        import torch
        import torchaudio.functional as AF
        from demucs.apply import apply_model
        from demucs.pretrained import get_model as demucs_model
        self.torch, self.AF, self.apply = torch, AF, apply_model
        self.model = demucs_model("htdemucs").cuda().eval()
        self.vocals = self.model.sources.index("vocals")

    def __call__(self, audio):
        torch, AF, m = self.torch, self.AF, self.model
        with torch.no_grad():
            x = AF.resample(torch.from_numpy(audio).cuda(), SR, m.samplerate)
            wav = x[None].repeat(2, 1)
            mean, std = wav.mean(), wav.std() + 1e-8
            out = self.apply(m, ((wav - mean) / std)[None], split=True, overlap=0.1,
                             device="cuda", progress=False)[0]
            voc = (out[self.vocals] * std + mean).mean(0)
            return AF.resample(voc, m.samplerate, SR).float().cpu().numpy()


def _sep_worker(conn):
    """Tiến trình riêng cho Demucs: PyTorch mang cuDNN khác với faster-whisper nên không
    nạp chung một tiến trình được; tách ra còn giúp giao diện không bị giật."""
    try:
        sep = Separator()
    except Exception as e:  # noqa: BLE001
        conn.send(("err", str(e)))
        return
    conn.send(("ok", None))
    while True:
        audio = conn.recv()
        if audio is None:
            break
        try:
            conn.send(("ok", sep(audio)))
        except Exception as e:  # noqa: BLE001
            conn.send(("err", str(e)))


class SeparatorProcess:
    def __init__(self):
        import multiprocessing as mp
        ctx = mp.get_context("spawn")
        self.conn, child = ctx.Pipe()
        self.proc = ctx.Process(target=_sep_worker, args=(child,), daemon=True)
        self.proc.start()
        self.lock = threading.Lock()
        kind, err = self.conn.recv()  # chờ nạp mô hình
        if kind != "ok":
            raise RuntimeError(err)

    def __call__(self, audio):
        with self.lock:
            self.conn.send(audio)
            kind, result = self.conn.recv()
        if kind != "ok":
            raise RuntimeError(result)
        return result


def release_separator():
    with _sep_lock:
        sep, _sep["obj"] = _sep["obj"], None
    if sep:
        try:
            with sep.lock:
                sep.conn.send(None)
            sep.proc.join(timeout=3)
        except Exception:  # noqa: BLE001
            pass
        if sep.proc.is_alive():
            sep.proc.terminate()


def get_separator(status=None):
    with _sep_lock:
        if _sep["obj"] is None and not _sep["failed"]:
            if status:
                status("ai_loading", name="Demucs")
            try:
                _sep["obj"] = SeparatorProcess()
            except Exception:  # noqa: BLE001 - không tách được thì nhận dạng thẳng
                _sep["failed"] = True
        return _sep["obj"]


class AppMeters:
    """Đọc mức âm lượng hiện tại của từng app (Windows Core Audio)."""

    def __init__(self):
        try:
            import comtypes
            comtypes.CoInitialize()
            from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
            self.utils, self.iface = AudioUtilities, IAudioMeterInformation
            self.listed_at, self.meters = 0.0, []
        except Exception:  # noqa: BLE001 - thiếu pycaw -> không lọc
            self.utils = None

    def others_playing(self, threshold=0.02):
        if not self.utils:
            return []
        now = time.monotonic()
        try:
            if now - self.listed_at > 5:  # liệt kê lại các app có âm thanh (tốn hơn đọc mức âm lượng)
                self.listed_at, self.meters = now, []
                for sess in self.utils.GetAllSessions():
                    if not sess.Process or sess.ProcessId == os.getpid():  # bỏ qua chính app này
                        continue
                    name = sess.Process.name()
                    if "spotify" not in name.lower():
                        self.meters.append((name.removesuffix(".exe"), sess._ctl.QueryInterface(self.iface)))
            return [name for name, meter in self.meters if meter.GetPeakValue() > threshold]
        except Exception:  # noqa: BLE001
            self.listed_at = 0
            return []


def _norm(word):
    w = unicodedata.normalize("NFC", word.lower())
    return re.sub(r"[^\w]", "", w)


def _starts_upper(word):
    w = word.strip()
    return w[:1].isupper() and not (w == "I" or w.startswith("I'"))


def group_lines(words):
    """[(start, end, word)] -> các dòng lời: xuống dòng khi gặp chữ viết hoa (Whisper viết hoa
    đầu mỗi câu hát), ngắt hơi, dấu câu, hoặc dòng quá dài."""
    lines, cur = [], []
    for w in words:
        gap = w[0] - cur[-1][1] if cur else 0
        # chữ hoa đầu câu -> dòng mới; nhưng giữ tên riêng nhiều chữ (Hà Nội, Sơn Tùng) trên một dòng
        # (Whisper thường báo các từ liền nhau, không có khoảng ngắt giữa 2 câu, nên không dựa vào gap)
        new_sentence = len(cur) >= 2 and _starts_upper(w[2]) and not _starts_upper(cur[-1][2])
        if cur and (new_sentence or gap > 1.5 or len(cur) >= 14 or (len(cur) >= 3 and (
                gap > 0.45 or cur[-1][2].strip()[-1:] in ",.?!"))):
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def resplit_lines(lines, max_words=14):
    """Chia lại dòng cho lời đã có [(t, câu)] (vd: lời AI lưu từ trước): ghép thành chuỗi từ,
    ước lượng thời điểm từng từ, rồi xuống dòng ở chữ viết hoa đầu câu."""
    words = []  # (thời điểm, từ, đầu_dòng_cũ_cách_xa)
    for i, (t, text) in enumerate(lines):
        toks = text.split()
        if not toks:
            continue
        nxt = lines[i + 1][0] if i + 1 < len(lines) else t + 0.4 * len(toks)
        step = min(max(nxt - t, 0.1) / len(toks), 0.45)  # nhạc dạo dài -> không kéo giãn câu
        prev_end = words[-1][0] + 0.45 if words else None
        for k, tok in enumerate(toks):
            # dòng cũ cách xa dòng trước (nhạc dạo) và bắt đầu bằng chữ hoa -> giữ chỗ xuống dòng;
            # bắt đầu bằng chữ thường thì là phần tiếp của câu trước
            far = k == 0 and prev_end is not None and t - prev_end > 1.5 and _starts_upper(tok)
            words.append((t + k * step, tok, far))
    out, cur = [], []
    for tm, tok, far in words:
        new_sentence = len(cur) >= 2 and _starts_upper(tok) and not _starts_upper(cur[-1][1])
        if cur and (far or new_sentence or len(cur) >= max_words):
            out.append(cur)
            cur = []
        cur.append((tm, tok))
    if cur:
        out.append(cur)
    return [(round(ln[0][0], 2), " ".join(tok for _, tok in ln)) for ln in out]


def line_text(ln):
    return "".join(w[2] for w in ln).strip().strip(",.")


class Transcriber:
    """Chép lời cho một bài. Gửi (thời_điểm_trong_bài, câu) qua on_line,
    trạng thái (key i18n, tham số) qua on_status."""

    PASS_EVERY = 3.0     # giây âm thanh mới giữa 2 lần nhận dạng
    MAX_BUFFER = 24.0    # bộ đệm dài hơn thì cắt bớt phần đã chốt

    def __init__(self, state, track_key, model_name, lang, on_line, on_status,
                 only_spotify=True, device="", separate=True):
        self.state, self.key = state, track_key
        self.device = device  # "" = loa mặc định; tên khác = thiết bị riêng chỉ có tiếng Spotify
        self.only_spotify = only_spotify and not device
        self.separate = separate
        self.model_name, self.lang = model_name, (None if lang == "auto" else lang)
        self.on_line, self.on_status = on_line, on_status
        self.stop_flag = threading.Event()
        self.audio = queue.Queue(maxsize=40)  # ~20 giây; đầy thì bỏ đoạn cũ nhất
        self.recorded_sec = 0.0
        self.lines = []
        self.first_pos = None
        self.last_pos = 0.0
        self.paused_by = None
        self.recordings = []   # [[vị_trí_bắt_đầu, [block...]]] các đoạn thu liền mạch (để chép lại cả bài)
        self.committed_t = -1.0
        self.prev_hyp = []     # giả thuyết lần trước (chưa chốt)
        self.pending = []      # từ đã chốt nhưng dòng chưa kết thúc

    def start(self):
        threading.Thread(target=self._work, daemon=True).start()  # _work tự bật thu âm khi mô hình sẵn sàng

    def _put(self, item):
        while True:
            try:
                self.audio.put_nowait(item)
                return
            except queue.Full:
                try:
                    self.audio.get_nowait()
                except queue.Empty:
                    pass

    def stop(self):
        self.stop_flag.set()

    def _current(self):
        track, pos, playing, _ = self.state.snapshot()
        same = track is not None and (track["title"], track["artist"]) == self.key
        return same, pos, playing

    def _prompt(self):
        title, artist = self.key
        last = self.lines[-1][1] if self.lines else ""
        return f"{title} - {artist}. {last}".strip()

    # ---- thu âm ------------------------------------------------------------ #

    def _record(self):
        import soundcard as sc
        meters = AppMeters() if self.only_spotify else None
        try:
            spk = sc.default_speaker()
            if self.device:
                spk = next((d for d in sc.all_speakers() if d.name == self.device), None)
                if spk is None:
                    self.on_status("ai_no_device", name=self.device)
                    self._put(None)
                    return
            mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
            with mic.recorder(samplerate=SR, channels=1, blocksize=1024) as rec:
                while not self.stop_flag.is_set():
                    _, pos_before, _ = self._current()
                    block = rec.record(numframes=SR // 2)[:, 0].astype(np.float32)
                    same, pos, playing = self._current()
                    if not same:
                        break
                    # Windows 10 không thu riêng được tiếng của Spotify -> bỏ qua đoạn có app khác kêu
                    others = meters.others_playing() if meters else []
                    if others:
                        if self.paused_by != others[0]:
                            self.paused_by = others[0]
                            self.on_status("ai_paused", app=self.paused_by)
                        continue
                    if self.paused_by:
                        self.paused_by = None
                        self.on_status("ai_listening")
                    self._put((pos_before, block, playing))  # vị trí trong bài ứng với đầu block
        except Exception as e:  # noqa: BLE001
            self.on_status("ai_capture_err", err=e)
        self._put(None)

    # ---- nhận dạng trực tiếp ------------------------------------------------ #

    def _work(self):
        try:
            model = get_model(self.model_name, self.on_status)
            sep = get_separator(self.on_status) if self.separate and separation_available() else None
        except Exception as e:  # noqa: BLE001
            self.on_status("ai_model_err", err=e)
            self.stop_flag.set()
            return
        if self.stop_flag.is_set():
            return
        threading.Thread(target=self._record, daemon=True).start()
        try:
            self._loop(model, sep)
        finally:
            self.stop_flag.set()  # luồng xử lý dừng -> luồng thu âm cũng dừng

    def _loop(self, model, sep):
        if self.paused_by:
            self.on_status("ai_paused", app=self.paused_by)
        else:
            self.on_status("ai_listening")
        buf, buf_start, expected, since = np.zeros(0, np.float32), 0.0, None, 0.0
        while not self.stop_flag.is_set():
            item = self.audio.get()
            if item is None:
                break
            pos, block, playing = item
            if not playing:
                continue
            if expected is None or abs(pos - expected) > 2.0:  # tua bài / bỏ đoạn -> bộ đệm mới
                if len(buf):
                    self._pass(model, sep, buf, buf_start, final=True)
                buf, buf_start, self.prev_hyp = np.zeros(0, np.float32), pos, []
                self.committed_t = -1.0  # sau khi tua, so trùng theo thời điểm các dòng đã có
                self.recordings.append([pos, []])
                if self.first_pos is None:
                    self.first_pos = pos
            buf = np.concatenate([buf, block])
            self.recordings[-1][1].append(block)
            expected = pos + len(block) / SR
            self.recorded_sec += len(block) / SR
            self.last_pos = expected
            since += len(block) / SR
            if since >= self.PASS_EVERY:
                since = 0.0
                cut = self._pass(model, sep, buf, buf_start, final=False)
                if cut > 0:
                    buf, buf_start = buf[int(cut * SR):], buf_start + cut
        if len(buf) and not self.stop_flag.is_set():
            self._pass(model, sep, buf, buf_start, final=True)

    def _recognize(self, model, sep, audio, offset, prompt=None):
        """-> [(start, end, word)] theo thời gian trong bài."""
        if float(np.sqrt(np.mean(audio ** 2))) < 1e-4:  # im lặng
            return []
        if sep is not None:
            try:
                audio = sep(audio)
            except Exception:  # noqa: BLE001 - tách lỗi thì dùng âm thanh gốc
                pass
        segs, info = model.transcribe(
            audio, language=self.lang, beam_size=5, word_timestamps=True,
            condition_on_previous_text=False, initial_prompt=prompt or self._prompt(),
            vad_filter=True, vad_parameters={"min_silence_duration_ms": 400, "threshold": 0.35},
            no_speech_threshold=0.6, hallucination_silence_threshold=2.0)
        words = []
        for seg in segs:
            if seg.no_speech_prob > 0.7 or seg.avg_logprob < -1.2 or HALLUCINATION.search(seg.text):
                continue
            words.extend((offset + w.start, offset + w.end, w.word) for w in seg.words or [])
        if self.lang is None and info.language_probability > 0.7:
            self.lang = info.language  # cố định ngôn ngữ sau lần nhận đầu
        return words

    def _pass(self, model, sep, buf, buf_start, final):
        """Một lần nhận dạng bộ đệm. Trả về số giây có thể cắt khỏi đầu bộ đệm."""
        words = [w for w in self._recognize(model, sep, buf, buf_start) if w[0] >= self.committed_t - 0.05]
        if final:
            agreed = words
        else:  # LocalAgreement: chỉ chốt phần đầu trùng với lần nhận dạng trước
            agreed = []
            for a, b in zip(self.prev_hyp, words):
                if _norm(a[2]) != _norm(b[2]):
                    break
                agreed.append(b)
            self.prev_hyp = words[len(agreed):]
        if agreed:
            self.committed_t = agreed[-1][1]
            self.pending.extend(agreed)
        self._emit(final)
        dur = len(buf) / SR
        if final:
            return dur
        if dur > self.MAX_BUFFER:
            if self.committed_t > buf_start:
                return min(self.committed_t - buf_start, dur - 4.0)
            self.prev_hyp = []
            return dur - 10.0  # chưa chốt được gì (nhạc dạo dài) -> chỉ giữ 10 giây cuối
        return 0.0

    def _emit(self, final):
        groups = group_lines(self.pending)
        done, self.pending = (groups, []) if final else (groups[:-1], groups[-1] if groups else [])
        for ln in done:
            text = line_text(ln)
            t = float(ln[0][0])
            if not text or (self.lines and _norm(text) == _norm(self.lines[-1][1])):
                continue
            if any(abs(t - old) < 1.0 for old, _ in self.lines):  # đã chép đoạn này (tua lại)
                continue
            self.lines.append((t, text))
            self.on_line(t, text)

    # ---- chép lại cả bài --------------------------------------------------- #

    def covers_whole_song(self, duration):
        return (self.first_pos is not None and self.first_pos <= 20 and duration
                and self.last_pos >= duration - 25 and len(self.lines) >= 6
                and self.recorded_sec >= duration * 0.8)

    def refine_lines(self):
        """Chép lại đoạn thu dài nhất một lượt (đủ ngữ cảnh) -> [(t, câu)]. Lỗi thì trả lời trực tiếp."""
        try:
            start, blocks = max(self.recordings, key=lambda r: len(r[1]))
            audio = np.concatenate(blocks)
            model = get_model(self.model_name)
            sep = get_separator() if self.separate and separation_available() else None
            words = self._recognize(model, sep, audio, start, prompt="{} - {}".format(*self.key))
            lines = [(float(ln[0][0]), line_text(ln)) for ln in group_lines(words) if line_text(ln)]
            return lines if len(lines) >= len(self.lines) * 0.6 else self.lines
        except Exception:  # noqa: BLE001
            return self.lines
