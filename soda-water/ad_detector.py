"""
Ad detection module - OpenCV template matching on Android screenshots
"""

import os
import time
import logging
from datetime import datetime

import cv2
import numpy as np

from config import (
    AD_TEMPLATES, TEMPLATES_DIR, MATCH_THRESHOLD,
    SAVE_SCREENSHOTS, SCREENSHOT_DIR, CYCLE_INTERVAL,
    SCREENSHOT_FORMAT, SCREENSHOT_JPEG_QUALITY,
)

logger = logging.getLogger(__name__)


class AdDetector:
    """Ad detector using OpenCV template matching"""

    def __init__(self, device, templates_dir=None):
        self.device = device
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.templates = {}
        self._load_templates()

    def _load_templates(self):
        """Load all template images from disk."""
        os.makedirs(self.templates_dir, exist_ok=True)
        for name, filename in AD_TEMPLATES.items():
            path = os.path.join(self.templates_dir, filename)
            if os.path.exists(path):
                self.templates[name] = cv2.imread(path)
                h, w = self.templates[name].shape[:2]
                logger.info(f"Template loaded: {name} ({w}x{h} from {path})")
            else:
                logger.warning(f"Template missing: {path}")
                self.templates[name] = None

    def capture_screen(self):
        """
        Capture phone screen via ADB and return OpenCV BGR image.
        Returns None on failure.
        """
        png_data = self.device.capture_screen()
        if png_data is None:
            return None
        nparr = np.frombuffer(png_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    def find_template(self, screen, template_name, threshold=None):
        """
        Find template in screen image.
        Returns (center_x, center_y, confidence) or None.
        """
        if threshold is None:
            threshold = MATCH_THRESHOLD

        template = self.templates.get(template_name)
        if template is None:
            return None
        if screen is None:
            return None

        screen_h, screen_w = screen.shape[:2]
        tmpl_h, tmpl_w = template.shape[:2]

        if tmpl_h > screen_h or tmpl_w > screen_w:
            logger.warning(f"Template {template_name} larger than screen, skipping")
            return None

        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            center_x = max_loc[0] + tmpl_w // 2
            center_y = max_loc[1] + tmpl_h // 2
            logger.debug(f"Matched {template_name}: ({center_x},{center_y}), conf={max_val:.3f}")
            return (center_x, center_y, max_val)
        return None

    def find_any_template(self, screen, template_names, threshold=None):
        """
        Find any of the given templates, return best match.
        Returns {"name": ..., "x": ..., "y": ..., "confidence": ...} or None.
        """
        best = None
        best_conf = 0
        for name in template_names:
            result = self.find_template(screen, name, threshold)
            if result and result[2] > best_conf:
                best = {"name": name, "x": result[0], "y": result[1], "confidence": result[2]}
                best_conf = result[2]
        return best

    def wait_for_template(self, template_name, timeout=60, threshold=None):
        """
        Loop until template is found or timeout.
        Returns {"name": ..., "x": ..., "y": ..., "confidence": ...} or None.
        """
        start = time.time()
        while time.time() - start < timeout:
            screen = self.capture_screen()
            if screen is None:
                time.sleep(CYCLE_INTERVAL)
                continue
            result = self.find_template(screen, template_name, threshold)
            if result:
                return {
                    "name": template_name,
                    "x": result[0], "y": result[1],
                    "confidence": result[2],
                }
            time.sleep(CYCLE_INTERVAL)
        logger.warning(f"Timeout waiting for template: {template_name}")
        return None

    def save_screenshot(self, screen, prefix="detect"):
        """
        Save screenshot to disk for debugging.

        Format is controlled by SCREENSHOT_FORMAT config:
          "jpg" — JPEG at SCREENSHOT_JPEG_QUALITY (80-90%% smaller than PNG)
          "png" — lossless PNG
        """
        if not SAVE_SCREENSHOTS or screen is None:
            return ""

        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        ext = SCREENSHOT_FORMAT if SCREENSHOT_FORMAT in ("jpg", "png") else "jpg"
        filename = f"{prefix}_{timestamp}.{ext}"
        path = os.path.join(SCREENSHOT_DIR, filename)

        if ext == "jpg":
            params = [cv2.IMWRITE_JPEG_QUALITY, SCREENSHOT_JPEG_QUALITY]
            cv2.imwrite(path, screen, params)
        else:
            cv2.imwrite(path, screen)

        # Log file size for awareness
        size_kb = os.path.getsize(path) / 1024
        logger.debug(f"Screenshot saved: {path} ({size_kb:.0f} KB)")
        return path

    @staticmethod
    def add_random_offset(x, y):
        """
        Passthrough — random offset is now applied ONLY in DeviceController.tap()
        to avoid double-offset bugs. Kept for API compatibility.
        """
        return (x, y)
