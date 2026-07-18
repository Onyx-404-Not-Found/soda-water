"""
Device Controller - ADB-based Android phone automation
"""

import subprocess
import time
import random
import logging

from config import (
    ADB_PATH, DEVICE_SERIAL, ADB_TIMEOUT, POST_TAP_DELAY,
    RANDOM_OFFSET, OFFSET_RANGE,
)

logger = logging.getLogger(__name__)


class DeviceController:
    """Android device controller via ADB"""

    def __init__(self, adb_path=None, serial=None):
        self.adb = adb_path or ADB_PATH
        self.serial = serial or DEVICE_SERIAL
        self._adb_prefix = self._build_prefix()

    def _build_prefix(self):
        cmd = [self.adb]
        if self.serial:
            cmd.extend(["-s", self.serial])
        return cmd

    def _run(self, *args, timeout=None):
        """Run an ADB command and return the CompletedProcess."""
        cmd = self._adb_prefix + list(args)
        timeout = timeout or ADB_TIMEOUT
        logger.debug(f"ADB: {' '.join(cmd)}")
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    # -------- Connection --------

    def check_connection(self):
        """Check if an Android device is connected via ADB."""
        try:
            result = self._run("devices")
        except FileNotFoundError:
            logger.error(
                f"ADB not found at '{self.adb}'.\n"
                f"  Install platform-tools: https://developer.android.com/studio/releases/platform-tools\n"
                f"  Or set ADB_PATH in config.py to the correct path."
            )
            return False
        except Exception as e:
            logger.error(f"Failed to run ADB: {e}")
            return False

        lines = result.stdout.strip().split("\n")[1:]
        devices = [l.split("\t")[0] for l in lines if l.strip() and "\tdevice" in l]

        if devices:
            logger.info(f"Connected devices: {', '.join(devices)}")
            if not self.serial and len(devices) == 1:
                self.serial = devices[0]
                self._adb_prefix = self._build_prefix()
            return True

        # No devices — give helpful error
        if any("unauthorized" in l for l in lines):
            logger.error(
                "Device unauthorized! Unlock your phone and accept the USB debugging dialog."
            )
        else:
            logger.error(
                "No Android device detected!\n"
                "  1. Enable Developer Options on your phone\n"
                "  2. Enable USB Debugging\n"
                "  3. Connect via USB and accept the prompt\n"
                "  4. Run: adb devices   to verify"
            )
        return False

    def get_device_info(self):
        """Return device model, Android version, and manufacturer."""
        info = {}
        for prop in ["ro.product.model", "ro.build.version.release", "ro.product.manufacturer"]:
            result = self._run("shell", "getprop", prop)
            info[prop.split(".")[-1]] = result.stdout.strip()
        return info

    # -------- Screenshot --------

    def capture_screen(self):
        """
        Capture phone screen via ADB exec-out.
        Returns PNG bytes on success, None on failure.
        """
        try:
            result = subprocess.run(
                self._adb_prefix + ["exec-out", "screencap", "-p"],
                capture_output=True,
                timeout=ADB_TIMEOUT,
            )
            if result.returncode != 0:
                logger.error(f"Screenshot failed: {result.stderr.strip()}")
                return None
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error("Screenshot timed out — is the phone locked or frozen?")
            return None
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return None

    def save_screenshot(self, path):
        """Capture screen and save to a file. Returns True on success."""
        data = self.capture_screen()
        if data:
            with open(path, "wb") as f:
                f.write(data)
            return True
        return False

    # -------- Touch --------

    def tap(self, x, y):
        """
        Tap at screen coordinates.
        Random offset is applied here (once!) to avoid double-offset bugs.
        """
        if RANDOM_OFFSET:
            x += random.randint(-OFFSET_RANGE, OFFSET_RANGE)
            y += random.randint(-OFFSET_RANGE, OFFSET_RANGE)
        logger.info(f"Tap: ({x}, {y})")
        self._run("shell", "input", "tap", str(x), str(y))
        time.sleep(POST_TAP_DELAY)

    def long_press(self, x, y, duration_ms=1000):
        """Long press at screen coordinates."""
        if RANDOM_OFFSET:
            x += random.randint(-OFFSET_RANGE, OFFSET_RANGE)
            y += random.randint(-OFFSET_RANGE, OFFSET_RANGE)
        logger.info(f"Long press: ({x}, {y}), {duration_ms}ms")
        self._run("shell", "input", "swipe", str(x), str(y), str(x), str(y), str(duration_ms))
        time.sleep(POST_TAP_DELAY)

    def swipe(self, x1, y1, x2, y2, duration_ms=300):
        """Swipe from (x1,y1) to (x2,y2)."""
        logger.info(f"Swipe: ({x1},{y1}) -> ({x2},{y2}), {duration_ms}ms")
        self._run("shell", "input", "swipe",
                  str(x1), str(y1), str(x2), str(y2), str(duration_ms))
        time.sleep(0.5)

    def swipe_up(self, screen_width, screen_height):
        """Swipe up (scroll down)."""
        x = screen_width // 2
        y1 = int(screen_height * 0.8)
        y2 = int(screen_height * 0.3)
        self.swipe(x, y1, x, y2)

    def swipe_down(self, screen_width, screen_height):
        """Swipe down (scroll up)."""
        x = screen_width // 2
        y1 = int(screen_height * 0.3)
        y2 = int(screen_height * 0.8)
        self.swipe(x, y1, x, y2)

    def press_back(self):
        """Press the Android BACK button."""
        logger.info("Press BACK")
        self._run("shell", "input", "keyevent", "4")
        time.sleep(0.5)

    def press_home(self):
        """Press the Android HOME button."""
        logger.info("Press HOME")
        self._run("shell", "input", "keyevent", "3")
        time.sleep(0.5)

    # -------- App control --------

    def start_app(self, package, activity=None):
        """Launch an app by package name."""
        if activity:
            cmd = f"am start -n {package}/{activity}"
        else:
            cmd = f"monkey -p {package} -c android.intent.category.LAUNCHER 1"
        self._run("shell", cmd)

    def force_stop(self, package):
        """Force-stop an app by package name."""
        self._run("shell", "am", "force-stop", package)

    # -------- Screen info --------

    def get_screen_size(self):
        """Return (width, height) of the device screen."""
        result = self._run("shell", "wm", "size")
        for token in result.stdout.split():
            if "x" in token and token[0].isdigit():
                w, h = token.split("x")
                return int(w), int(h)
        logger.warning("Cannot get screen size, using default 1080x1920")
        return 1080, 1920
