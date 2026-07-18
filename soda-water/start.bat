@echo off
title Soda Music Ad Clicker
cd /d "%~dp0"

:: ============================================
:: Step 1: Check Python
:: ============================================
python --version >nul 2>&1
if not errorlevel 1 goto check_deps

echo.
echo ================================================
echo   ERROR: Python not found on PATH
echo ================================================
echo.
echo   Install Python 3.8+ from:
echo   https://www.python.org/downloads/
echo.
echo   IMPORTANT: Check [x] Add Python to PATH
echo   during installation.
echo ================================================
pause
exit /b

:: ============================================
:: Step 2: Check dependencies
:: ============================================
:check_deps
python -c "import cv2; import numpy" >nul 2>&1
if not errorlevel 1 goto menu

echo.
echo ================================================
echo   First run - installing dependencies...
echo ================================================
echo.
pip install -r "%~dp0requirements.txt"
if not errorlevel 1 goto menu

echo.
echo ================================================
echo   WARNING: pip install may have failed
echo ================================================
echo.
echo   Try running as Administrator or install manually:
echo   pip install opencv-python numpy keyboard pillow
echo ================================================
pause

:: ============================================
:: Menu
:: ============================================
:menu
cls
echo.
echo ================================================
echo     Soda Music Ad Auto-Clicker
echo ================================================
echo.
echo   [1] Start      auto-clicker (CLI + hotkeys)
echo   [2] GUI         desktop control panel
echo   [3] Web UI      browser at http://127.0.0.1:8765
echo.
echo   [4] Capture     first-time template setup
echo   [5] Test        verify templates on screen
echo   [6] Install     reinstall dependencies
echo.
echo   [0] Exit
echo ================================================
echo.
set "choice="
set /p "choice=Enter choice [0-6]: "

if "%choice%"=="0" exit /b 0
if "%choice%"=="1" goto run_cli
if "%choice%"=="2" goto run_gui
if "%choice%"=="3" goto run_web
if "%choice%"=="4" goto run_capture
if "%choice%"=="5" goto run_test
if "%choice%"=="6" goto run_install
goto menu

:: ============================================
:: [1] CLI
:: ============================================
:run_cli
cls
echo.
echo ================================================
echo   CLI Mode
echo ================================================
echo.
echo   Ctrl+Shift+A  Start    Ctrl+Shift+S  Stop
echo   Ctrl+Shift+D  Pause    Ctrl+C        Exit
echo ================================================
echo.
python "%~dp0main.py" --now
pause
goto menu

:: ============================================
:: [2] GUI
:: ============================================
:run_gui
cls
echo.
echo Starting GUI... (close the GUI window to return)
echo.
python "%~dp0gui.py"
goto menu

:: ============================================
:: [3] Web Server
:: ============================================
:run_web
cls
echo.
echo ================================================
echo   Opening browser at http://127.0.0.1:8765
echo   Press Ctrl+C to stop the server
echo ================================================
echo.
start "" http://127.0.0.1:8765
python "%~dp0server.py"
pause
goto menu

:: ============================================
:: [4] Capture Templates
:: ============================================
:run_capture
cls
echo.
echo ================================================
echo   Template Capture
echo ================================================
echo.
python "%~dp0main.py" --capture
pause
goto menu

:: ============================================
:: [5] Test Templates
:: ============================================
:run_test
cls
echo.
echo ================================================
echo   Template Test
echo ================================================
echo.
python "%~dp0main.py" --test
pause
goto menu

:: ============================================
:: [6] Install Dependencies
:: ============================================
:run_install
cls
echo.
echo Installing dependencies...
echo.
pip install -r "%~dp0requirements.txt" --upgrade
echo.
echo Done.
pause
goto menu
