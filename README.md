# mrZ — Ultra-Lightweight Screen Capture AI Assistant (`DRM-ready`)

Aplikasi pembantu ujian/CBT real-time berbasis AI vision. Super ringan, `DXGI`/`WGC` aware (bisa capture konten dengan hardware overlay/DRM yang bikin screenshot biasa hitam), overlay HUD click-through, hotkey.

> **Public build: tanpa API key bawaan.** Isi `api_key` kamu di `config.json` baru bisa dipakai. Butuh key OpenAI-compatible (cleanapis / OpenAI / dll).

## Fitur

- Capture `DXGI Desktop Duplication` → `WGC (WinRT)` → `mss/GDI` fallback + deteksi frame hitam otomatis
- HUD transparan `WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE`, `WDA_EXCLUDEFROMCAPTURE` (overlay gak ikut ke-capture)
- Hotkey `Ctrl+Del` capture, `Ctrl+End` / `Ctrl+\` / `Enter` submit, `Ctrl+Shift+Q` quit
- Tray icon `Exit`

## Cara pakai (exe)

1. Download `mrZ.exe` + `config.json` dari Releases
2. Edit `config.json` → isi `api_key` (dan `api_base_url` kalau bukan cleanapis)
3. Jalankan `mrZ.exe` (akan muncul di system tray `^` → klik kanan `Exit` untuk keluar)
4. `Ctrl+Del` untuk capture, `Ctrl+End` untuk kirim ke AI

Tanpa `api_key` HUD akan menampilkan `err: no key`.

## Cara pakai (dari source)

```bat
pip install -r requirements.txt
python mrz.py
```

## Build exe sendiri

```bat
build.bat
:: atau
pyinstaller --noconsole --onefile --icon=icon.ico --name=mrZ --hidden-import=dxcam --hidden-import=comtypes --hidden-import=numpy --hidden-import=cv2 mrz.py
```

## Konfigurasi (`config.json`)

`api_base_url`, `api_key`, `model`, `system_prompt`, `user_prompt`, `image_max_width`, `image_jpeg_quality`, `display_duration_seconds`, `hud_offset_x/y`, `font_size_*`.

## Lisensi

MIT
