@echo off
title Multi-Courier Tracker — Starting...
color 0B
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║       🚀 MULTI-COURIER TRACKING SOFTWARE                 ║
echo  ║  FedEx  DHL  UPS  Aramex  Shiprocket  OnPoint  Xindus   ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python install nahi hai!
    echo  Please install from: https://python.org/downloads/
    echo  "Add Python to PATH" checkbox zaroor tick karein!
    echo.
    pause
    exit /b 1
)

echo  [✓] Python found
echo  [*] Installing required packages...
pip install requests openpyxl -q --disable-pip-version-check
echo  [✓] Packages ready
echo.
echo  [*] Launching tracker software...
echo.

cd /d "%~dp0"
python app.py

if errorlevel 1 (
    echo.
    echo  [ERROR] Software start nahi hua!
    echo  Error details upar dekhen.
    pause
)
