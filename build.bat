@echo off
title Build mrZ - Standalone Executable
cd /d "%~dp0"

echo ===================================================
echo   Compiling mrZ into Standalone Windows App (.exe)
echo   Fullscreen Game Support + DirectX GPU Capture
echo ===================================================
echo.

where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] PyInstaller belum terinstall. Menginstall pyinstaller...
    pip install pyinstaller
)

echo [INFO] Mematikan proses mrZ yang sedang berjalan (jika ada)...
taskkill /F /IM mrZ.exe >nul 2>nul

echo [INFO] Mulai compile dengan icon Z, mode tanpa console, dan Admin Privileges...
pyinstaller --uac-admin --noconsole --onefile --icon="icon.ico" --hidden-import=dxcam --hidden-import=comtypes --name="mrZ" mrz.py

if exist "dist\mrZ.exe" (
    echo [INFO] Menyalin dist\mrZ.exe ke folder utama...
    copy /y "dist\mrZ.exe" ".\mrZ.exe" >nul
    echo.
    echo ===================================================
    echo   [SUKSES] mrZ.exe berhasil dibuat!
    echo   Lokasi: %~dp0mrZ.exe
    echo ===================================================
) else (
    echo.
    echo [GAGAL] Terjadi kesalahan saat compile.
)

echo.
pause
