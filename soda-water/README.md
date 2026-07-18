# Soda Music Ad Auto-Clicker

Automatically detect and tap ads in the Qishui Music (Soda Music) Android app using ADB + OpenCV template matching.

## Blog

详细原理与使用教程：[CSDN 博客](https://blog.csdn.net/l_14yhl9t/article/details/162992286)

## How It Works

1. ADB captures the phone screen
2. OpenCV matches pre-captured ad button templates
3. ADB simulates taps at matched coordinates
4. Smart countdown filter avoids false positives from timer text
5. Full cycle: watch ad -> claim reward -> continue -> repeat

## Prerequisites

### Phone
- Enable Developer Options -> USB Debugging
- Connect to PC via USB

### PC
`ash
# Install ADB (Platform Tools)
# https://developer.android.com/studio/releases/platform-tools

# Install Python dependencies
pip install -r requirements.txt
`

## Quick Start

### Windows (double-click)

| File | What it does |
|------|-------------|
| setup.bat | One-click install (pip + adb check) |
| start.bat | Launch the web control panel |

### Manual

`ash
# Web UI (recommended)
python server.py
# Open http://127.0.0.1:8765

# CLI
python main.py --now

# Desktop GUI (requires tkinter)
python gui.py
`

## Template Setup

1. Click **Capture Template** in the web panel
2. Crop the button area from the screenshot
3. Save to 	emplates/:

| Template | Description |
|----------|-------------|
| d_finished.png | "Claim success" indicator |
| claim_reward.png | "Claim reward" button |
| play_again.png | "Continue watching" button |

## Project Structure

`
soda-water/
├── server.py              # Web UI server (primary entry)
├── main.py                # CLI entry
├── gui.py                 # Desktop GUI entry
├── launcher.py            # Smart launcher
├── engine.py              # Shared core logic
├── ad_detector.py         # OpenCV template matching
├── device_controller.py   # ADB device control
├── config.py              # Settings
├── templates/             # Ad button images
├── setup.bat / start.bat  # Windows helpers
└── requirements.txt
`

## License

For educational purposes only.
