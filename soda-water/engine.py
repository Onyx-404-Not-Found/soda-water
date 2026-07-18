"""
Ad Engine - Shared core logic for ad detection and clicking
===========================================================
Used by all three entry points (CLI, server, GUI) so behavior is
consistent regardless of how you run the tool.
"""

import os
import time
import threading
import numpy as np

from config import (
    AD_TEMPLATES, MATCH_THRESHOLD, CYCLE_INTERVAL, AD_TIMEOUT,
    POST_TAP_DELAY, CLAIM_TIMEOUT, PLAY_AGAIN_TIMEOUT,
    SAVE_SCREENSHOTS, SCREENSHOT_DIR, PROGRESS_LOG_INTERVAL,
    COUNTDOWN_FILTER_ENABLED, COUNTDOWN_FILTER_MAX_SKIPS,
    AUTO_CLEANUP_SCREENSHOTS, KEEP_SCREENSHOTS,
)


class AdEngine:
    """
    Shared ad-clicking engine.

    Usage:
        engine = AdEngine(device, detector, on_log=print)
        engine.running = True

        while engine.running:
            if engine.paused:
                time.sleep(0.3)
                continue
            ok = engine.process_one_ad()
            engine.cycle_count += 1
            if ok:
                engine.success_count += 1
            time.sleep(CYCLE_INTERVAL)
    """

    def __init__(self, device, detector, on_log=None):
        self.device = device
        self.detector = detector

        # Thread-safe state
        self._lock = threading.Lock()
        self._running = False
        self._paused = False

        # Stats
        self.cycle_count = 0
        self.success_count = 0

        # Countdown filter failsafe counter
        self._skip_count = 0

        # Log callback: called with (message_string) from any thread
        self._on_log = on_log or (lambda msg: None)

    # ---- State properties (thread-safe) ----

    @property
    def running(self):
        with self._lock:
            return self._running

    @running.setter
    def running(self, value):
        with self._lock:
            self._running = value

    @property
    def paused(self):
        with self._lock:
            return self._paused

    @paused.setter
    def paused(self, value):
        with self._lock:
            self._paused = value

    # ---- Logging ----

    def _log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self._on_log(f"[{ts}] {msg}")

    # ---- Screenshot helpers ----

    def _save_hit_screenshot(self, screen, prefix):
        """Save a screenshot when a template was matched (debug)."""
        if not SAVE_SCREENSHOTS or screen is None:
            return
        self.detector.save_screenshot(screen, prefix)

    def _auto_cleanup(self):
        """Remove old screenshots, keeping only the latest N."""
        if not AUTO_CLEANUP_SCREENSHOTS:
            return
        ss_dir = SCREENSHOT_DIR
        if not os.path.isdir(ss_dir):
            return
        try:
            files = sorted(
                [f for f in os.listdir(ss_dir)
                 if f.lower().endswith((".png", ".jpg", ".jpeg"))],
                key=lambda x: os.path.getmtime(os.path.join(ss_dir, x)),
            )
            for f in files[:-KEEP_SCREENSHOTS]:
                os.remove(os.path.join(ss_dir, f))
        except Exception:
            pass  # cleanup is best-effort

    # ---- Countdown filter ----

    @staticmethod
    def _countdown_digit_ratio(screen, match_left, match_top, tmpl_w, tmpl_h):
        """
        Check if pixels to the LEFT of the match contain countdown digits.
        Countdown text like "45s later claim success" has bright digits.
        The real "claim success" indicator has no digits — just background.

        Returns the ratio of non-background pixels (0.0 ~ 1.0).
        Higher = more likely to be a countdown (should skip).
        """
        check_w = 80
        check_h = tmpl_h
        left = match_left - check_w
        if left < 0:
            return 0.0

        top = match_top
        region = screen[top:top + check_h, left:match_left]
        if region.size == 0:
            return 0.0

        gray = np.mean(region, axis=2) if len(region.shape) == 3 else region
        bg = float(np.mean(gray[:, -5:]))  # background from rightmost 5px
        bright_pixels = np.sum(np.abs(gray - bg) > 40)
        return float(bright_pixels / gray.size)

    # ---- Main ad cycle ----

    def process_one_ad(self):
        """
        One complete ad cycle:
          Phase 1: wait for ad_finished → tap
          Phase 2: wait for claim_reward → tap
          Phase 3: wait for play_again → tap (optional)
          Fallback: check claim_reward / play_again directly

        Returns True if at least ad_finished was found and tapped.
        """
        start = time.time()
        last_log = 0
        self._skip_count = 0  # reset failsafe per cycle

        # ================================================================
        # Phase 1: Wait for ad_finished (with countdown filter)
        # ================================================================
        while time.time() - start < AD_TIMEOUT:
            if not self.running or self.paused:
                return False

            screen = self.detector.capture_screen()
            if screen is None:
                time.sleep(CYCLE_INTERVAL)
                continue

            result = self.detector.find_template(screen, "ad_finished")
            if result:
                cx, cy, conf = result
                tmpl = self.detector.templates.get("ad_finished")
                if tmpl is not None:
                    tmpl_h, tmpl_w = tmpl.shape[:2]
                    match_left = cx - tmpl_w // 2
                    match_top = cy - tmpl_h // 2

                    # Countdown filter: skip if countdown digits are present
                    if COUNTDOWN_FILTER_ENABLED:
                        ratio = self._countdown_digit_ratio(
                            screen, match_left, match_top, tmpl_w, tmpl_h
                        )
                        if ratio > 0.08:
                            self._skip_count += 1
                            if self._skip_count <= COUNTDOWN_FILTER_MAX_SKIPS:
                                self._log(
                                    f"Countdown filter: skipped (digit ratio={ratio:.3f}, "
                                    f"skip #{self._skip_count})"
                                )
                                time.sleep(CYCLE_INTERVAL)
                                continue
                            else:
                                self._log(
                                    f"Countdown filter: forcing through after "
                                    f"{self._skip_count} skips (failsafe)"
                                )

                # ---- ad_finished confirmed ----
                waited = time.time() - start
                self._log(f"ad_finished found! (waited {waited:.0f}s, conf={conf:.3f}) → tapping")
                self._save_hit_screenshot(screen, "hit_ad_finished")
                x, y = self.detector.add_random_offset(cx, cy)
                self.device.tap(x, y)
                break  # move to phase 2

            # ---- Fallback: check claim_reward / play_again directly ----
            cr = self.detector.find_template(screen, "claim_reward")
            if cr:
                self._log(f"claim_reward found directly (conf={cr[2]:.3f}) → tapping")
                self._save_hit_screenshot(screen, "hit_claim_reward")
                x, y = self.detector.add_random_offset(cr[0], cr[1])
                self.device.tap(x, y)
                return True

            pa = self.detector.find_template(screen, "play_again")
            if pa:
                self._log(f"play_again found directly (conf={pa[2]:.3f}) → tapping")
                self._save_hit_screenshot(screen, "hit_play_again")
                x, y = self.detector.add_random_offset(pa[0], pa[1])
                self.device.tap(x, y)
                return True

            # Progress update
            elapsed = int(time.time() - start)
            if elapsed > 0 and elapsed - last_log >= PROGRESS_LOG_INTERVAL:
                self._log(f"Polling ad_finished... ({elapsed}s)")
                last_log = elapsed

            time.sleep(CYCLE_INTERVAL)
        else:
            self._log(f"Timeout: ad_finished not found within {AD_TIMEOUT}s")
            return False

        # ================================================================
        # Phase 2: Wait for claim_reward button
        # ================================================================
        self._log("Looking for claim_reward...")
        for _ in range(int(CLAIM_TIMEOUT)):
            if not self.running or self.paused:
                return True  # ad_finished was tapped, partial success

            time.sleep(1)
            screen = self.detector.capture_screen()
            if screen is None:
                continue

            cr = self.detector.find_template(screen, "claim_reward")
            if cr:
                self._log(f"claim_reward found (conf={cr[2]:.3f}) → tapping")
                self._save_hit_screenshot(screen, "hit_claim_reward")
                x, y = self.detector.add_random_offset(cr[0], cr[1])
                self.device.tap(x, y)
                break
        else:
            self._log("claim_reward not found, continuing...")
            time.sleep(CYCLE_INTERVAL)
            return True  # ad_finished was tapped, partial success

        # ================================================================
        # Phase 3: Wait for play_again (optional, some ad flows show this)
        # ================================================================
        time.sleep(2)
        self._log("Looking for play_again...")
        for _ in range(PLAY_AGAIN_TIMEOUT):
            if not self.running or self.paused:
                return True

            time.sleep(1)
            screen = self.detector.capture_screen()
            if screen is None:
                continue

            pa = self.detector.find_template(screen, "play_again")
            if pa:
                self._log(f"play_again found (conf={pa[2]:.3f}) → tapping")
                self._save_hit_screenshot(screen, "hit_play_again")
                x, y = self.detector.add_random_offset(pa[0], pa[1])
                self.device.tap(x, y)
                self._log("=== Full cycle complete! ===")
                self._auto_cleanup()
                return True

        self._log("play_again not found, cycle complete (partial)")
        self._auto_cleanup()
        return True
