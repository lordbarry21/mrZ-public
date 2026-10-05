@echo off
title mrZ - Ultra-Lightweight AI Assistant
cd /d "%~dp0"

echo ===================================================
echo   mrZ - Ultra-Lightweight Screen Capture AI Assistant
echo   Tugas RPL - SMKN 6 Tangsel
echo ===================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak terdeteksi di PATH!
    pause
    exit /b 1
)

echo [INFO] Menjalankan mrZ...
python mrz.py

pause
