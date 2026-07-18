"""
Soda Music Ad Auto-Clicker (CLI)
================================
User manually starts each ad in the app.
Program handles: ad_finished → claim_reward → play_again → repeat.

Usage:
  python main.py                  Wait for hotkey to start
  python main.py --now            Start immediately
  python main.py --capture        Capture template images
  python main.py --test           Test template matching
  python main.py --threshold 0.8  Override match threshold

Hotkeys:
  Ctrl+Shift+A  Start
  Ctrl+Shift+S  Stop
  Ctrl+Shift+D  Pause/Resume
"""

import sys
import os
import time
import argparse
import logging
import threading

from config import (
    AD_TEMPLATES, CYCLE_INTERVAL, AD_TIMEOUT,
    MATCH_THRESHOLD, SAVE_SCREENSHOTS, SCREENSHOT_DIR,
    LOG_LEVEL, LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT,
    HOTKEY_START, HOTKEY_STOP, HOTKEY_PAUSE,
    TEMPLATES_DIR,
)
from ad_detector import AdDetector
from device_controller import DeviceController
from engine import AdEngine

# ---------------------------------------------------------------------------
# Logging setup (with log rotation)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            LOG_FILE, encoding="utf-8",
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
        ),
    ],
)
logger = logging.getLogger("main")


# ---------------------------------------------------------------------------
# Hotkey callbacks (named functions, not lambdas-in-tuples)
# ---------------------------------------------------------------------------
def _on_hotkey_start(engine):
    engine.running = True
    engine.paused = False
    logger.info(">> Started")


def _on_hotkey_stop(engine):
    engine.running = False
    logger.info(">> Stopped")


def _on_hotkey_pause(engine):
    engine.paused = not engine.paused
    logger.info(f">> {'Paused' if engine.paused else 'Resumed'}")


def setup_hotkeys(engine):
    """Register global hotkeys (requires keyboard package)."""
    try:
        import keyboard
        keyboard.add_hotkey(HOTKEY_START, lambda: _on_hotkey_start(engine))
        keyboard.add_hotkey(HOTKEY_STOP, lambda: _on_hotkey_stop(engine))
        keyboard.add_hotkey(HOTKEY_PAUSE, lambda: _on_hotkey_pause(engine))
        logger.info(
            f"Hotkeys: start={HOTKEY_START}  stop={HOTKEY_STOP}  pause={HOTKEY_PAUSE}"
        )
    except ImportError:
        logger.warning(
            "Package 'keyboard' not installed — hotkeys unavailable.\n"
            "  Install: pip install keyboard\n"
            "  (Run as Administrator on Windows for global hotkeys)"
        )


# ---------------------------------------------------------------------------
# Template capture mode
# ---------------------------------------------------------------------------
def capture_mode(detector, device):
    """Interactive mode to capture template images from the phone screen."""
    logger.info("=" * 50)
    logger.info("Template Capture Mode")
    logger.info("=" * 50)
    print("\nMake sure the target button/element is visible on your phone screen.\n")

    items = {
        "1": ("ad_finished",  "ad_finished  — claim success indicator at top-right"),
        "2": ("claim_reward", "claim_reward — claim reward button at center"),
        "3": ("play_again",   "play_again   — 'play another' button (optional)"),
    }
    for k, (name, desc) in items.items():
        print(f"  {k}. {name}")
        print(f"     {desc}")
    print("  0. Exit")

    while True:
        choice = input("\nNumber: ").strip()
        if choice == "0":
            break
        if choice not in items:
            print("Invalid choice. Try again.")
            continue

        name, desc = items[choice]
        print(f"\nCapturing '{name}' in 3 seconds... Show the element on screen!")
        for i in range(3, 0, -1):
            print(f"  {i}...")
            time.sleep(1)

        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        path = os.path.join(SCREENSHOT_DIR, f"{name}_full.png")
        if device.save_screenshot(path):
            print(f"\n✓ Screenshot saved: {path}")
            os.makedirs(TEMPLATES_DIR, exist_ok=True)
            target = os.path.join(TEMPLATES_DIR, AD_TEMPLATES[name])
            print(f"  Next step: crop the element and save as: {target}")
        else:
            print(f"\n✗ Screenshot failed! Check ADB connection.")
        print()


# ---------------------------------------------------------------------------
# Test mode
# ---------------------------------------------------------------------------
def test_mode(detector, device):
    """Test template matching against current phone screen."""
    print("Capturing phone screen in 3 seconds...")
    time.sleep(3)

    screen = detector.capture_screen()
    if screen is None:
        print("ERROR: Screenshot failed. Check ADB connection.")
        return

    detector.save_screenshot(screen, "test")
    print(f"\nTesting templates (threshold={MATCH_THRESHOLD}):\n")

    all_ok = True
    for name in AD_TEMPLATES:
        r = detector.find_template(screen, name)
        if r:
            print(f"  ✓ {name}: pos=({r[0]},{r[1]})  conf={r[2]:.3f}")
        else:
            tag = "[SKIP]" if detector.templates.get(name) is None else "[MISS]"
            print(f"  ✗ {tag} {name} — not found on screen")
            if detector.templates.get(name) is None:
                all_ok = False

    if not all_ok:
        print("\nTip: Run 'python main.py --capture' to create missing templates.")


# ---------------------------------------------------------------------------
# Main loop (CLI)
# ---------------------------------------------------------------------------
def main_loop(device, detector, start_now=False, threshold=None):
    """Main ad-clicking loop — runs until stopped."""
    # Override threshold if specified
    if threshold is not None:
        import config
        config.MATCH_THRESHOLD = threshold

    engine = AdEngine(device, detector, on_log=logger.info)

    # Show device info
    info = device.get_device_info()
    sw, sh = device.get_screen_size()
    logger.info(
        f"Device: {info.get('manufacturer', '?')} {info.get('model', '?')} "
        f"Android {info.get('release', '?')}  |  Screen: {sw}x{sh}"
    )

    # Validate templates
    loaded = sum(1 for t in detector.templates.values() if t is not None)
    required = 2  # ad_finished + claim_reward
    if loaded < required:
        logger.error(
            f"Need at least {required} templates, only {loaded} found.\n"
            f"  Missing templates go in: {os.path.abspath(TEMPLATES_DIR)}/\n"
            f"  Run: python main.py --capture   to capture screenshots\n"
            f"  Then crop and save the matching template images."
        )
        sys.exit(1)
    logger.info(f"Templates loaded: {loaded}/{len(AD_TEMPLATES)}")

    # Start hotkey listener in background
    threading.Thread(target=setup_hotkeys, args=(engine,), daemon=True).start()

    # Set initial running state from --now flag
    if start_now:
        engine.running = True
        logger.info("Auto-starting (--now flag)...")
    else:
        logger.info(f"Ready. Press {HOTKEY_START.upper()} to start.")
        logger.info("(Or use python main.py --now to start immediately)")

    # ---- Main event loop ----
    try:
        while True:
            if not engine.running:
                time.sleep(0.5)
                continue
            if engine.paused:
                time.sleep(0.5)
                continue

            ok = engine.process_one_ad()
            engine.cycle_count += 1
            if ok:
                engine.success_count += 1
                logger.info(
                    f"Stats: {engine.success_count}/{engine.cycle_count} cycles successful"
                )
            time.sleep(CYCLE_INTERVAL)

    except KeyboardInterrupt:
        logger.info(
            f"Interrupted. Final stats: {engine.success_count}/{engine.cycle_count} "
            f"cycles successful."
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Soda Music Ad Auto-Clicker — Android ADB + OpenCV automation"
    )
    parser.add_argument(
        "--capture", action="store_true",
        help="Capture phone screenshots for creating template images"
    )
    parser.add_argument(
        "--now", action="store_true",
        help="Start auto-clicking immediately (no hotkey needed)"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Test template matching against current phone screen"
    )
    parser.add_argument(
        "--threshold", type=float, default=None,
        help=f"Override template match threshold (default: {MATCH_THRESHOLD})"
    )
    args = parser.parse_args()

    # ---- Connect to device ----
    device = DeviceController()
    if not device.check_connection():
        sys.exit(1)

    detector = AdDetector(device)

    # ---- Dispatch ----
    if args.capture:
        capture_mode(detector, device)
    elif args.test:
        test_mode(detector, device)
    else:
        main_loop(device, detector, start_now=args.now, threshold=args.threshold)


if __name__ == "__main__":
    main()
