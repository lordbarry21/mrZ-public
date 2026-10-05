"""
mrZ - Ultra-Lightweight Screen Capture AI Assistant
"""

import os
import sys
import time
import json
import base64
import io
import re
import threading
import urllib.request
import urllib.error
import ctypes
from pathlib import Path

# Third-party lightweight dependencies
from PIL import Image
import mss
import pystray
try:
    import dxcam as _dxcam
    import numpy as _np
    _DXCAM_AVAILABLE = True
except Exception:
    _dxcam = None
    _np = None
    _DXCAM_AVAILABLE = False

# Windows API constants
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Virtual Key Codes
VK_RETURN = 0x0D       # Enter
VK_ESCAPE = 0x1B       # Esc
VK_BACK = 0x08         # Backspace
VK_DELETE = 0x2E       # Del key
VK_END = 0x23          # End key
VK_NUMPAD1 = 0x61      # Numpad 1 (End key di laptop HP/Lenovo saat NumLock ON)
VK_INSERT = 0x2D       # Insert key
VK_NUMPAD0 = 0x60      # Numpad 0 (Ins key saat NumLock ON)
VK_NEXT = 0x22         # Page Down key
VK_OEM_5 = 0xDC        # \ key (Backslash, letaknya persis di bawah Backspace/Del)
VK_CONTROL = 0x11      # Ctrl key
VK_SHIFT = 0x10        # Shift key
VK_KEY_Q = 0x51        # Q key

# Window Extended Styles
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

# Public build: no embedded keys. User must set api_key in config.json.
# To add your own embedded key, replace EMBEDDED_KEYS below.
EMBEDDED_BASE_URL = "https://cleanapis.com/v1"
EMBEDDED_KEYS: list[str] = []  # <- put your API key(s) here or leave empty and use config.json

DEFAULT_CONFIG = {
    "api_base_url": "https://cleanapis.com/v1",
    "api_key": "",
    "model": "claude-opus-5.5",
    "system_prompt": (
        "You are mrZ, an ultra-precise Indonesian exam solver specialized EXCLUSIVELY for multiple-choice and statement assessments (TKA, UTBK-SNBT, CBT Pijar/Sekolah, Ulangan Harian). "
        "You master ALL subjects: Matematika, Bahasa Indonesia, Bahasa Inggris, Fisika, Kimia, Biologi, Sejarah, Geografi, Sosiologi, Ekonomi, dan TPS.\n\n"
        "FOKUS AREA SOAL (SANGAT KRUSIAL):\n"
        "- Jika layar menampilkan split-screen, banyak jendela, atau ada panel catatan / chat AI lain / pembahasan di samping (misalnya di kanan/kiri layar): "
        "ABAIKAN SEMUA PANEL SAMPING / CHAT TERSEBUT! Fokus HANYA dan MUTLAK pada lembar soal ujian asli yang sedang dikerjakan. "
        "Selesaikan soal secara mandiri dari awal dan jangan terpengaruh oleh tulisan di panel samping.\n\n"
        "SOAL HANYA ADA 3 TIPE (KHUSUS FORMAT OBJEKTIF, TIDAK ADA ESSAY / ISIAN SINGKAT):\n"
        "1. Pilihan Ganda Tunggal (Single Choice): Pilih 1 huruf jawaban yang paling tepat (a, b, c, d, atau e).\n"
        "2. Pilihan Ganda Kompleks (Multi Choice / Jawaban Benar Lebih Dari Satu): Tentukan nomor-nomor pernyataan yang benar, urutkan dari atas ke bawah dipisah koma (contoh: 1,3,4 atau 2,5).\n"
        "3. Tabel Pernyataan Benar/Salah atau Ya/Tidak: Tentukan status setiap baris pernyataan secara berurutan (contoh: 1b, 2s, 3b atau 1y, 2t, 3y).\n\n"
        "ATURAN MENJAWAB:\n"
        "- Baca seluruh teks bacaan, rumus, data tabel, soal, dan opsi jawaban secara teliti.\n"
        "- Lakukan analisis dan verifikasi internal secara presisi 100%.\n"
        "- Pada baris TERAKHIR, WAJIB tuliskan HANYA 'FINAL: <jawaban>' tanpa kalimat penjelasan tambahan.\n\n"
        "FORMAT WAJIB BARIS TERAKHIR:\n"
        "- Tipe 1 (PG biasa): FINAL: <huruf> (Contoh: FINAL: b)\n"
        "- Tipe 2 (Multi benar): FINAL: <angka,angka> (Contoh: FINAL: 1,3,4 atau FINAL: 2,5)\n"
        "- Tipe 3 (Benar/Salah): FINAL: <nomorb/s> (Contoh: FINAL: 1b, 2s, 3b)"
    ),
    "user_prompt": "Fokus pada lembar soal ujian utama (abaikan jendela pembahasan/chat di samping jika ada). Analisis dan tentukan pilihan yang benar. Baris terakhir tulis: FINAL: <jawaban>",
    "debounce_seconds": 0,
    "display_duration_seconds": 7.0,
    "max_chars": 15,
    "image_max_width": 1920,
    "image_jpeg_quality": 95,
    "font_size_counter": 11,
    "font_size_result": 13,
    "hud_offset_x": 30,
    "hud_offset_y": 40
}

def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent

def log(msg: str):
    """Write timestamped log to file and console."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    try:
        log_file = get_app_dir() / "mrz.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass
    try:
        if sys.stdout:
            print(formatted)
    except Exception:
        pass

def load_config() -> dict:
    config_path = get_app_dir() / "config.json"
    cfg = DEFAULT_CONFIG.copy()
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                cfg.update(user_cfg)
                log(f"[CFG] Loaded config from {config_path}")
        except Exception as e:
            log(f"[WARN] Failed to read config.json: {e}")
    return cfg

def parse_final_answer(raw_text: str, max_chars: int = 15) -> str:
    """Extract and sanitize the concise final answer for HUD display."""
    if not raw_text:
        return "unknown"
    
    # 1. Look for 'FINAL:' or 'JAWABAN:' marker (pick the first definitive answer)
    m = re.findall(r'(?:FINAL|JAWABAN|ANSWER|KUNCI)\s*:\s*([^\n\r]+)', raw_text, re.I)
    target = m[0].strip() if m else raw_text.strip().split('\n')[-1].strip()
    
    # Cut off explanatory suffixes: e.g. "2 dan 5 yaitu 6...", "1,3,4 karena..."
    target = re.split(r'\b(?:yaitu|karena|adalah|seperti|artinya|yang)\b', target, flags=re.I)[0].strip()
    target = re.sub(r'\(.*?\)', '', target).strip()
    target = re.sub(r'[*_`#~"\'\[\]]', '', target).strip()
    
    # Check True/False / Ya/Tidak table: e.g. 1b, 2s, 3b or 1y, 2t, 3y
    tb_matches = re.findall(r'\b([1-9])\s*([bsytBSYT])\b', target)
    if tb_matches and len(tb_matches) >= 2:
        return ', '.join(f'{num}{val.lower()}' for num, val in tb_matches)
    
    # Check Multi-selection statements: e.g. 'Pernyataan 1, 3, dan 4' or '2 dan 5' or '1, 3, 4'
    if 'pernyataan' in target.lower() or 'opsi' in target.lower() or ',' in target or ' dan ' in target.lower():
        found_nums = re.findall(r'\b([1-9])\b', target)
        if len(found_nums) >= 2:
            return ','.join(found_nums)
            
    # Check if target is just digit sequence like "25" or "134" or "235"
    if re.fullmatch(r'[1-9]{2,5}', target):
        return ','.join(list(target))
        
    # Check Single multiple-choice letter: A, B, C, D, E
    opt_match = re.search(r'^(?:pilihan|opsi|jawaban)?\s*([A-Ea-e])(?:\.|\b)', target)
    if not opt_match:
        opt_match = re.search(r'\b([A-Ea-e])\b', target)
    if opt_match and len(target) <= 40:
        return opt_match.group(1).lower()
        
    # Fallback: clean and clamp up to max_chars
    cleaned = re.sub(r'^(pilihan|opsi|jawaban|jawaban adalah)\s*', '', target, flags=re.I).strip()
    if len(cleaned) > max_chars:
        single_letter = re.search(r'\b([A-Ea-e])\b', cleaned)
        if single_letter:
            return single_letter.group(1).lower()
        cleaned = cleaned[:max_chars].strip()
    return cleaned.lower()


class ScreenCapturer:
    """Hybrid DRM-aware capture: DXGI Desktop Duplication -> WGC WinRT -> mss GDI fallback.

    Why hybrid: mss/GDI goes black on DRM / hardware-overlay video (Netflix, Widevine,
    CBT secure browser). DXGI Duplication captures at GPU backbuffer level and
    WGC (Windows Graphics Capture) captures at DWM compositor level -- both can
    see through overlays that GDI cannot. We try strongest first and keep the
    first non-black result.
    """
    def __init__(self, max_width: int = 1920, quality: int = 95):
        self.max_width = max_width
        self.quality = quality
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]  # Primary display
        # Lazy DXGI/WGC cameras -- created on first use to avoid startup cost
        self._dxgi_cam = None
        self._wgc_cam = None
        self._dxgi_failed = False
        self._wgc_failed = False

    # --- internal helpers ---
    def _is_mostly_black(self, img: Image.Image, threshold: float = 0.97) -> bool:
        """Detect pure-black DRM placeholder (all pixels ~0)."""
        try:
            small = img.resize((32, 32), Image.Resampling.BILINEAR).convert("L")
            hist = small.histogram()
            # hist[0..15] = near-black pixels
            near_black = sum(hist[:16])
            total = 32 * 32
            return (near_black / total) > threshold
        except Exception:
            return False

    def _prepare_image(self, img: Image.Image) -> tuple[Image.Image, bytes]:
        if img.width > self.max_width:
            ratio = self.max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((self.max_width, new_height), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=self.quality, optimize=True)
        return img, buf.getvalue()

    def _grab_dxgi(self) -> Image.Image | None:
        if not _DXCAM_AVAILABLE or self._dxgi_failed:
            return None
        try:
            if self._dxgi_cam is None:
                self._dxgi_cam = _dxcam.create(output_idx=0, output_color="RGB", backend="dxgi")
            # Retry for transient None (DXGI duplicator timing)
            frame = None
            for _ in range(4):
                frame = self._dxgi_cam.grab()
                if frame is not None:
                    break
                time.sleep(0.02)
            if frame is None:
                return None
            return Image.fromarray(frame)
        except Exception as e:
            log(f"[CAP] DXGI grab failed: {e}")
            self._dxgi_failed = True
            try:
                if self._dxgi_cam:
                    self._dxgi_cam.release()
            except Exception:
                pass
            self._dxgi_cam = None
            return None

    def _grab_wgc(self) -> Image.Image | None:
        if not _DXCAM_AVAILABLE or self._wgc_failed:
            return None
        try:
            if self._wgc_cam is None:
                self._wgc_cam = _dxcam.create(output_idx=0, output_color="RGB", backend="winrt")
            frame = None
            for _ in range(4):
                frame = self._wgc_cam.grab()
                if frame is not None:
                    break
                time.sleep(0.04)
            if frame is None:
                return None
            return Image.fromarray(frame)
        except Exception as e:
            log(f"[CAP] WGC grab failed: {e}")
            self._wgc_failed = True
            try:
                if self._wgc_cam:
                    self._wgc_cam.release()
            except Exception:
                pass
            self._wgc_cam = None
            return None

    def _grab_mss(self) -> Image.Image | None:
        try:
            sct_img = self.sct.grab(self.monitor)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception as e:
            log(f"[CAP] mss grab failed: {e}")
            return None

    def _save_debug(self, img_bytes: bytes):
        try:
            debug_path = get_app_dir() / "last_capture.jpg"
            with open(debug_path, "wb") as f:
                f.write(img_bytes)
        except Exception:
            pass

    def capture_frame_base64(self) -> str:
        candidates: list[tuple[str, Image.Image]] = []

        # 1) DXGI Desktop Duplication (GPU backbuffer, best for DRM/overlay)
        img = self._grab_dxgi()
        if img is not None:
            candidates.append(("dxgi", img))

        # 2) WGC WinRT (DWM compositor, fallback when DXGI blocked)
        # Only try if DXGI missing or looked black
        need_wgc = not candidates or self._is_mostly_black(candidates[0][1], threshold=0.92)
        if need_wgc:
            img2 = self._grab_wgc()
            if img2 is not None:
                candidates.append(("wgc", img2))

        # 3) mss GDI (always available, guaranteed not to crash)
        need_mss = not candidates or all(self._is_mostly_black(c[1], threshold=0.92) for c in candidates)
        if need_mss:
            img3 = self._grab_mss()
            if img3 is not None:
                candidates.append(("mss", img3))

        # Pick best: first non-black, else the largest / last
        chosen_name, chosen_img = candidates[0] if candidates else ("none", None)
        if chosen_img is None:
            raise RuntimeError("All capture backends failed")

        # If the primary candidate is black but a later one is not, prefer non-black
        for name, cimg in candidates:
            if not self._is_mostly_black(cimg, threshold=0.92):
                chosen_name, chosen_img = name, cimg
                break

        log(f"[CAP] backends tried: {[n for n,_ in candidates]} -> chosen: {chosen_name} ({chosen_img.width}x{chosen_img.height})"
            + (" [WARN black-detected, recovered]" if self._is_mostly_black(chosen_img, threshold=0.99) else ""))

        _, img_bytes = self._prepare_image(chosen_img)
        self._save_debug(img_bytes)
        return base64.b64encode(img_bytes).decode("utf-8")


class AIEngine:
    """Connects to OpenAI-compatible Vision API with multi-key failover and Claude Opus 5.5."""
    def __init__(self, config: dict):
        self.base_url = config.get("api_base_url", EMBEDDED_BASE_URL).rstrip("/")
        custom_key = config.get("api_key", "").strip()
        self.model = config.get("model", "claude-opus-5.5")
        self.max_chars = config.get("max_chars", 15)
        self.system_prompt = config.get(
            "system_prompt",
            DEFAULT_CONFIG.get("system_prompt")
        )
        self.user_prompt = config.get(
            "user_prompt",
            DEFAULT_CONFIG.get("user_prompt")
        )

        # Key pool: config.json key + any embedded keys (empty in public build)
        if custom_key:
            self.keys_pool = [custom_key] + EMBEDDED_KEYS
        else:
            self.keys_pool = list(EMBEDDED_KEYS)

        self.current_key_idx = 0
        if not self.keys_pool:
            log("[WARN] No API key configured! Set api_key in config.json or EMBEDDED_KEYS in mrz.py")

    def analyze_screens(self, frames_b64: list[str]) -> str:
        url = f"{self.base_url}/chat/completions"
        content_items = [
            {
                "type": "text",
                "text": self.user_prompt
            }
        ]
        for b64_data in frames_b64:
            content_items.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64_data}"}
            })

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": content_items
                }
            ],
            "temperature": 0.1,
            "stream": False
        }

        if not self.keys_pool:
            log("[ERR] No API key — set api_key in config.json")
            return "err: no key"

        last_error = "err: api"
        for attempt in range(len(self.keys_pool)):
            key = self.keys_pool[(self.current_key_idx + attempt) % len(self.keys_pool)]
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                "User-Agent": "mrZ/1.0"
            }

            req = urllib.request.Request(
                url,
                headers=headers,
                data=json.dumps(payload).encode("utf-8")
            )

            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    raw_text = data["choices"][0]["message"]["content"]
                    log(f"[AI_RAW] {raw_text.strip()}")
                    self.current_key_idx = (self.current_key_idx + attempt) % len(self.keys_pool)
                    return parse_final_answer(raw_text, self.max_chars)
            except urllib.error.HTTPError as e:
                log(f"[WARN] Key #{attempt+1} failed with HTTP {e.code}: {e}")
                last_error = f"err: {e.code}"
            except Exception as e:
                log(f"[WARN] Key #{attempt+1} failed: {e}")
                last_error = "err: net"

        log(f"[ERR] All {len(self.keys_pool)} API keys exhausted. Last error: {last_error}")
        return last_error


import tkinter as tk

class OverlayHUD:
    """Transparent, click-through, non-activating HUD in bottom-left corner."""
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, config: dict):
        self.config = config
        self.font_size_counter = config.get("font_size_counter", 11)
        self.font_size_result = config.get("font_size_result", 13)
        self.offset_x = config.get("hud_offset_x", 30)
        self.offset_y = config.get("hud_offset_y", 40)
        self.display_duration = config.get("display_duration_seconds", 7.0)

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.trans_color = "#000001"
        self.root.attributes("-transparentcolor", self.trans_color)
        self.root.config(bg=self.trans_color)

        self.width = 300
        self.height = 40
        
        # Position bottom-left
        screen_h = user32.GetSystemMetrics(1)
        pos_x = self.offset_x
        pos_y = screen_h - self.height - self.offset_y
        self.root.geometry(f"{self.width}x{self.height}+{pos_x}+{pos_y}")

        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg=self.trans_color,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        self.state = "idle"  # idle | count | loading | result
        self.current_text = ""
        self.spinner_idx = 0
        self.spinner_job = None
        self.hide_job = None

        self._apply_win32_styles()

    def _apply_win32_styles(self):
        """Make window completely click-through and non-activating for games."""
        try:
            self.root.update_idletasks()
            hwnd = user32.GetParent(self.root.winfo_id())
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(
                hwnd,
                GWL_EXSTYLE,
                style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            )
            # WDA_EXCLUDEFROMCAPTURE (0x11): Ensures the overlay is 100% invisible to screen captures
            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception as e:
            log(f"[WARN] Failed to apply win32 click-through styles: {e}")

    def render_text(self, text: str, font_size: int = None, color: str = "#FFFFFF"):
        if font_size is None:
            font_size = self.font_size_result
        self.canvas.delete("all")
        if not text:
            return

        font = ("Segoe UI", font_size, "bold")
        cx = 12
        cy = self.height // 2

        # 1px crisp outline for minimal discreet HUD
        shadow_offsets = [(-1, -1), (1, -1), (-1, 1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)]
        for dx, dy in shadow_offsets:
            self.canvas.create_text(cx + dx, cy + dy, text=text, font=font, fill="#0a0a0a", anchor="w")

        # Draw main bright white text
        self.canvas.create_text(cx, cy, text=text, font=font, fill=color, anchor="w")

    def show_count(self, count: int):
        self._cancel_timers()
        self.state = "count"
        self.current_text = str(count)
        self.render_text(self.current_text, font_size=self.font_size_counter)

    def show_loading(self):
        self._cancel_timers()
        self.state = "loading"
        self.spinner_idx = 0
        self._spin_tick()

    def _spin_tick(self):
        if self.state != "loading":
            return
        frame = self.SPINNER_FRAMES[self.spinner_idx % len(self.SPINNER_FRAMES)]
        self.spinner_idx += 1
        self.render_text(frame, font_size=self.font_size_counter + 2, color="#E0E7FF")
        self.spinner_job = self.root.after(80, self._spin_tick)

    def show_result(self, result_text: str):
        self._cancel_timers()
        self.state = "result"
        self.current_text = result_text
        self.render_text(self.current_text, font_size=self.font_size_result, color="#FFFFFF")
        
        ms = int(self.display_duration * 1000)
        self.hide_job = self.root.after(ms, self.hide)

    def hide(self):
        self._cancel_timers()
        self.state = "idle"
        self.canvas.delete("all")

    def _cancel_timers(self):
        if self.spinner_job:
            try:
                self.root.after_cancel(self.spinner_job)
            except Exception:
                pass
            self.spinner_job = None
        if self.hide_job:
            try:
                self.root.after_cancel(self.hide_job)
            except Exception:
                pass
            self.hide_job = None


class MrZApp:
    """Coordinator for mrZ application."""
    def __init__(self):
        log("=" * 50)
        log("  mrZ - Lightweight Screen Capture AI Assistant")
        log("  SMKN 6 Tangsel - Tugas RPL")
        log("=" * 50)

        self.config = load_config()
        self.capturer = ScreenCapturer(
            max_width=self.config.get("image_max_width", 1920),
            quality=self.config.get("image_jpeg_quality", 95)
        )
        self.ai = AIEngine(self.config)
        self.hud = OverlayHUD(self.config)

        self.frames_buffer = []
        self.debounce_timer = None
        self.lock = threading.Lock()
        self.running = True

        # Setup Windows System Tray Icon in a background daemon thread
        self.tray_icon = None
        self._setup_tray_icon()

        log(f"[OK] Endpoint: {self.config.get('api_base_url')}")
        log(f"[OK] Model: {self.config.get('model')}")
        log(f"[OK] Hotkey Capture: Ctrl + Del")
        log(f"[OK] Hotkey Submit:  Ctrl + End / Ctrl + \\ / Enter")
        log(f"[OK] Quit: Ctrl + Shift + Q or Right-Click Tray Icon -> Exit mrZ")
        log("=" * 50)

        # Start hotkey listener thread
        self.hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self.hotkey_thread.start()

    def _setup_tray_icon(self):
        """Initializes system tray icon in its own thread to avoid deadlocks."""
        try:
            icon_path = get_app_dir() / "logo.png"
            if icon_path.exists():
                tray_image = Image.open(icon_path).resize((64, 64), Image.Resampling.LANCZOS)
            else:
                tray_image = Image.new("RGB", (64, 64), color=(10, 10, 10))

            def on_exit_click(icon, item):
                self.quit_app()

            menu = pystray.Menu(
                pystray.MenuItem("Exit", on_exit_click)
            )

            self.tray_icon = pystray.Icon("mrZ", tray_image, "mrZ", menu=menu)
            
            # Start tray icon via explicit threading to prevent Windows message pump freezing
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            log("[OK] System Tray Icon active in Windows taskbar tray.")
        except Exception as e:
            log(f"[WARN] Failed to initialize System Tray Icon: {e}")

    def quit_app(self, *args):
        """Clean shutdown of HUD, Tray Icon, and background threads."""
        log("[ACT] Exiting mrZ cleanly...")
        self.running = False
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        try:
            self.hud.root.destroy()
        except Exception:
            pass
        os._exit(0)

    def _is_key_down(self, vk: int) -> bool:
        return (user32.GetAsyncKeyState(vk) & 0x8000) != 0

    def _hotkey_loop(self):
        """High-efficiency hotkey polling loop (~15ms sleep = < 0.1% CPU)."""
        capture_was_down = False
        submit_was_down = False

        while self.running:
            ctrl_down = self._is_key_down(VK_CONTROL)
            del_down = self._is_key_down(VK_DELETE)

            # Check capture combo: Ctrl + Delete
            capture_active = ctrl_down and del_down

            if capture_active and not capture_was_down:
                self._handle_capture_trigger()
                capture_was_down = True
            elif not capture_active:
                capture_was_down = False

            # Check submit combo:
            # - Ctrl + End (VK_END 0x23, or VK_NUMPAD1 0x61 on laptops with NumLock)
            # - Ctrl + \ (VK_OEM_5 0xDC, right below Backspace/Del)
            # - Ctrl + Insert (VK_INSERT 0x2D or VK_NUMPAD0 0x60)
            # - Ctrl + PgDn (VK_NEXT 0x22)
            # - Single Enter key (VK_RETURN 0x0D, without Ctrl)
            end_down = self._is_key_down(VK_END) or self._is_key_down(VK_NUMPAD1)
            backslash_down = self._is_key_down(VK_OEM_5)
            insert_down = self._is_key_down(VK_INSERT) or self._is_key_down(VK_NUMPAD0)
            pgdn_down = self._is_key_down(VK_NEXT)
            enter_down = self._is_key_down(VK_RETURN)

            submit_key_combo = ctrl_down and (end_down or backslash_down or insert_down or pgdn_down)
            submit_active = submit_key_combo or (enter_down and not ctrl_down and self.frames_buffer)

            if submit_active and not submit_was_down:
                log("[ACT] Submit hotkey detected! Preparing AI inference...")
                self._handle_submit_trigger()
                submit_was_down = True
            elif not submit_active:
                submit_was_down = False

            # Check Exit hotkey: Ctrl + Shift + Q
            if ctrl_down and self._is_key_down(VK_SHIFT) and self._is_key_down(VK_KEY_Q):
                self.quit_app()
                break

            time.sleep(0.015)

    def _handle_capture_trigger(self):
        """Silently captures screen, appends to buffer, updates HUD count."""
        t0 = time.time()
        try:
            b64_frame = self.capturer.capture_frame_base64()
            with self.lock:
                self.frames_buffer.append(b64_frame)
                count = len(self.frames_buffer)

            # Update HUD on main Tk thread
            self.hud.root.after(0, self.hud.show_count, count)
            elapsed_ms = (time.time() - t0) * 1000
            log(f"[SHOT] Frame #{count} captured silently in {elapsed_ms:.1f}ms")

            # If debounce_seconds > 0, set auto-submit timer
            debounce_sec = self.config.get("debounce_seconds", 0)
            if debounce_sec and debounce_sec > 0:
                with self.lock:
                    if self.debounce_timer:
                        self.debounce_timer.cancel()
                    self.debounce_timer = threading.Timer(debounce_sec, self._trigger_ai_inference)
                    self.debounce_timer.daemon = True
                    self.debounce_timer.start()

        except Exception as e:
            log(f"[ERR] Capture error: {e}")

    def _handle_submit_trigger(self):
        """Processes submit: auto-captures 1 frame if buffer is empty, then sends."""
        with self.lock:
            if self.debounce_timer:
                try:
                    self.debounce_timer.cancel()
                except Exception:
                    pass
                self.debounce_timer = None

            # FOOLPROOF: If user didn't capture beforehand, grab 1 screen now!
            if not self.frames_buffer:
                log("[ACT] Buffer was empty -> Auto-capturing screen for instant submit...")
                try:
                    b64_frame = self.capturer.capture_frame_base64()
                    self.frames_buffer.append(b64_frame)
                except Exception as e:
                    log(f"[ERR] Auto-capture failed: {e}")
                    return

        self._trigger_ai_inference()

    def _trigger_ai_inference(self):
        with self.lock:
            if not self.frames_buffer:
                return
            frames_to_send = list(self.frames_buffer)
            self.frames_buffer.clear()

        # Switch HUD to loading animation
        self.hud.root.after(0, self.hud.show_loading)
        log(f"[AI] Sending {len(frames_to_send)} frame(s) to AI for identification...")

        # Run AI call in background worker thread so UI never freezes
        threading.Thread(target=self._run_ai_worker, args=(frames_to_send,), daemon=True).start()

    def _run_ai_worker(self, frames: list[str]):
        t0 = time.time()
        result = self.ai.analyze_screens(frames)
        elapsed = time.time() - t0
        log(f"[RESULT] AI returned: {result!r} ({elapsed:.2f}s)")
        
        # Deliver result to HUD
        self.hud.root.after(0, self.hud.show_result, result)

    def run(self):
        try:
            self.hud.root.mainloop()
        except KeyboardInterrupt:
            self.quit_app()


if __name__ == "__main__":
    app = MrZApp()
    app.run()
