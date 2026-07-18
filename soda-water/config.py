"""
Soda Music Ad Auto-Clicker - Configuration
===========================================
Edit this file to match your environment before first run.

Quick start:
  1. Install ADB (platform-tools) and ensure "adb" is on your PATH
  2. Connect your Android phone via USB with USB Debugging enabled
  3. Run: python main.py --capture   to capture template images
  4. Run: python main.py --test      to verify templates work
  5. Run: python main.py             to start auto-clicking
"""

import os
import shutil

# Project root (where config.py lives) — all relative paths resolve from here
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def _resolve(path):
    """Make a path absolute, relative to the project root."""
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(_PROJECT_ROOT, path))


# ============================================================
# ADB / Device Settings
# ============================================================

def _find_adb():
    """
    Auto-detect the adb executable.
    Checks PATH first, then common installation locations.
    """
    # 1. Check PATH (works if platform-tools is in PATH)
    adb = shutil.which("adb")
    if adb:
        return adb

    # 2. Check common Windows locations
    candidates = [
        r"C:\platform-tools\adb.exe",
        r"C:\platform-tools-latest-windows\platform-tools\adb.exe",
        r"C:\adb\adb.exe",
    ]
    # 3. Check Android SDK default location
    android_home = os.environ.get("ANDROID_HOME", "")
    if android_home:
        candidates.append(os.path.join(android_home, "platform-tools", "adb.exe"))
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidates.append(os.path.join(local_app_data, "Android", "Sdk", "platform-tools", "adb.exe"))

    for p in candidates:
        if os.path.isfile(p):
            return p

    # 4. Fallback — hope it's on PATH
    return "adb"


ADB_PATH = _find_adb()

# Device serial number. Leave empty to auto-detect the single connected device.
# Use "adb devices" to list serials if you have multiple devices.
DEVICE_SERIAL = ""

# Timeout in seconds for ADB commands
ADB_TIMEOUT = 10


# ============================================================
# Template Matching (OpenCV)
# ============================================================

# Templates directory
TEMPLATES_DIR = _resolve("templates")

# Template image files. Only 2 are required for basic operation;
# "play_again" is optional (some ad flows show a "play again" dialog).
AD_TEMPLATES = {
    "ad_finished":  "ad_finished.png",   # "claim success" indicator at top-right
    "claim_reward": "claim_reward.png",  # "claim reward" button at center
    "play_again":   "play_again.png",    # "play another" button (optional)
}

# Template matching confidence threshold.
# 0.75 is a good starting point — raise if you get false matches,
# lower if templates aren't detected reliably.
MATCH_THRESHOLD = 0.65

# Countdown filter: when waiting for ad_finished, the countdown text
# "45s later claim success" can trigger false matches on the template.
# Enable this filter to skip frames that contain countdown digits.
COUNTDOWN_FILTER_ENABLED = True
COUNTDOWN_FILTER_MAX_SKIPS = 30  # failsafe: force through after this many skips


# ============================================================
# Timing
# ============================================================

CYCLE_INTERVAL = 2       # Seconds between screen checks
AD_TIMEOUT = 120         # Max seconds to wait for an ad to finish (safety net)
POST_TAP_DELAY = 1.5     # Seconds to wait after each tap
CLAIM_TIMEOUT = 30       # Max seconds to wait for claim_reward button
PLAY_AGAIN_TIMEOUT = 10  # Max seconds to wait for play_again button

# Random tap offset — adds subtle variation to tap coordinates
# to make the automation less detectable (pixels)
RANDOM_OFFSET = True
OFFSET_RANGE = 5


# ============================================================
# Screenshots (Debug)
# ============================================================

# Screenshot save mode:
#   "hit"  = only save when a template is matched (recommended, ~20-50 per run)
#   "all"  = save every screenshot (debug only, can produce GBs per run)
SAVE_SCREENSHOTS = "hit"    # "hit" | "all" | "" (disable)
SCREENSHOT_DIR = _resolve("screenshots")

# Screenshot format: "jpg" saves 80-90% disk space vs "png"
# JPEG at quality=70: ~200-400KB per image (vs 2-3MB PNG)
SCREENSHOT_FORMAT = "jpg"
SCREENSHOT_JPEG_QUALITY = 70

# Auto-cleanup: keep only the latest N screenshots
AUTO_CLEANUP_SCREENSHOTS = True
KEEP_SCREENSHOTS = 10


# ============================================================
# Logging
# ============================================================

LOG_LEVEL = "INFO"          # DEBUG, INFO, WARNING, ERROR
LOG_FILE = _resolve("soda_clicker.log")

# Log rotation: when LOG_FILE reaches LOG_MAX_BYTES, it's renamed
# to soda_clicker.log.1 and a new file starts. Keeps LOG_BACKUP_COUNT old files.
LOG_MAX_BYTES = 5 * 1024 * 1024   # 5 MB
LOG_BACKUP_COUNT = 3              # keep up to 3 backup files

# Progress log interval — how often to print "Still waiting..." messages
PROGRESS_LOG_INTERVAL = 15  # seconds


# ============================================================
# Hotkeys (CLI mode only)
# ============================================================

HOTKEY_START = "ctrl+shift+a"
HOTKEY_STOP  = "ctrl+shift+s"
HOTKEY_PAUSE = "ctrl+shift+d"


# ============================================================
# Server
# ============================================================

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765
