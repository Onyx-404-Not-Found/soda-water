@echo off
title Soda Music - Environment Setup
cd /d "%~dp0"
set "NEED_RESTART="

echo.
echo ================================================
echo   Soda Music Ad Clicker - Setup Wizard
echo ================================================
echo.

:: ============================================
:: Check 1: Python
:: ============================================
echo [1/3] Checking Python...
python --version >nul 2>&1
if not errorlevel 1 goto python_ok

echo.
echo   [MISSING] Python not found.
echo.
echo   Please install Python 3.8 or newer:
echo.
echo   1. Open: https://www.python.org/downloads/
echo   2. Download the latest installer
echo   3. Run the installer
echo   4. CHECK THE BOX: [x] Add Python to PATH
echo   5. Click Install Now
echo   6. Restart this computer (or this terminal)
echo.
echo ================================================
pause
exit /b 1

:python_ok
python --version
echo   [OK] Python found.

:: ============================================
:: Check 2: ADB
:: ============================================
echo.
echo [2/3] Checking ADB...
adb --version >nul 2>&1
if not errorlevel 1 goto adb_ok

echo.
echo   [MISSING] ADB not found on PATH.
echo.
echo   ADB is needed to communicate with your phone.
echo.
echo   Option A: Download platform-tools (recommended)
echo     1. Open: https://developer.android.com/studio/releases/platform-tools
echo     2. Download the Windows zip
echo     3. Extract to C:\platform-tools
echo     4. Add C:\platform-tools to your system PATH
echo        (Win+R -> sysdm.cpl -> Advanced -> Environment Variables)
echo.
echo   Option B: Run the manual installer below
echo     powershell -Command "iwr ..." (may be blocked)
echo.
echo   Continue anyway? You'll need ADB to connect.
echo ================================================
pause

:adb_ok
adb --version 2>nul | findstr /i "version"
echo   [OK] ADB found.

:: ============================================
:: Check 3: Python dependencies
:: ============================================
echo.
echo [3/3] Installing Python dependencies...
echo.
pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo.
    echo   [WARNING] Some packages failed to install.
    echo   You can retry later from the main menu [6].
) else (
    echo.
    echo   [OK] Dependencies installed.
)

:: ============================================
:: Create template folders
:: ============================================
if not exist "%~dp0templates" mkdir "%~dp0templates"
if not exist "%~dp0screenshots" mkdir "%~dp0screenshots"

:: ============================================
:: Done
:: ============================================
echo.
echo ================================================
echo   Setup complete!
echo ================================================
echo.
echo   NEXT STEPS:
echo.
echo   1. Enable USB Debugging on your Android phone
echo      Settings - About Phone - Tap Build Number 7 times
echo      Settings - Developer Options - USB Debugging = ON
echo.
echo   2. Connect phone to PC via USB cable
echo      Accept the "Allow USB debugging" prompt on phone
echo.
echo   3. Capture templates: double-click launcher.py
echo      then choose [4] Capture
echo.
echo   4. Start auto-clicking: choose [1] Start
echo ================================================
echo.
pause
