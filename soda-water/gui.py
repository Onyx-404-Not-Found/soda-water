"""
Soda Music Ad Clicker - GUI
============================
tkinter-based control panel for the ad auto-clicker.
No extra dependencies needed (tkinter is built into Python).

Usage:
  python gui.py
"""

import os
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime

from config import (
    AD_TEMPLATES, CYCLE_INTERVAL, AD_TIMEOUT,
    TEMPLATES_DIR, MATCH_THRESHOLD, SCREENSHOT_DIR,
)
from ad_detector import AdDetector
from device_controller import DeviceController
from engine import AdEngine


class AdClickerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Soda Music - Ad Auto Clicker")
        self.root.geometry("520x660")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Core components (created after auto-connect)
        self.device = None
        self.detector = None
        self.engine = None

        # Style
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.build_ui()
        self.root.after(500, self.auto_connect)

    # ================================================================
    # UI Construction
    # ================================================================
    def build_ui(self):
        pad = {"padx": 12, "pady": 4}

        # ---- Title ----
        title = ttk.Label(
            self.root, text="Soda Music Ad Auto-Clicker",
            font=("Segoe UI", 14, "bold"),
        )
        title.pack(pady=(12, 2))

        subtitle = ttk.Label(self.root, text="Android ADB + OpenCV", foreground="gray")
        subtitle.pack()

        # ---- Device Section ----
        dev_frame = ttk.LabelFrame(self.root, text=" Device ", padding=8)
        dev_frame.pack(fill="x", **pad)

        self.dev_status = ttk.Label(dev_frame, text="Checking...", foreground="orange")
        self.dev_status.pack(anchor="w")

        self.dev_detail = ttk.Label(dev_frame, text="")
        self.dev_detail.pack(anchor="w")

        btn_row = ttk.Frame(dev_frame)
        btn_row.pack(fill="x", pady=(6, 0))
        self.refresh_btn = ttk.Button(btn_row, text="Refresh", command=self.refresh_device)
        self.refresh_btn.pack(side="left", padx=(0, 8))
        self.capture_btn = ttk.Button(
            btn_row, text="Capture Template", command=self.capture_template
        )
        self.capture_btn.pack(side="left")

        # ---- Template Section ----
        tmpl_frame = ttk.LabelFrame(self.root, text=" Templates ", padding=8)
        tmpl_frame.pack(fill="x", **pad)

        self.tmpl_labels = {}
        for name in AD_TEMPLATES:
            row = ttk.Frame(tmpl_frame)
            row.pack(fill="x", pady=1)
            lbl = ttk.Label(row, text=name, width=18, anchor="e")
            lbl.pack(side="left")
            status = ttk.Label(row, text="...", foreground="gray", width=10, anchor="w")
            status.pack(side="left", padx=(6, 0))
            self.tmpl_labels[name] = status

        # ---- Control Buttons ----
        ctrl_frame = ttk.Frame(self.root)
        ctrl_frame.pack(fill="x", **pad, pady=(8, 0))

        self.start_btn = ttk.Button(
            ctrl_frame, text="START", command=self.start, width=10,
        )
        self.start_btn.pack(side="left", padx=(0, 6))

        self.pause_btn = ttk.Button(
            ctrl_frame, text="Pause", command=self.toggle_pause,
            width=8, state="disabled",
        )
        self.pause_btn.pack(side="left", padx=(0, 6))

        self.stop_btn = ttk.Button(
            ctrl_frame, text="Stop", command=self.stop,
            width=8, state="disabled",
        )
        self.stop_btn.pack(side="left")

        # ---- Stats ----
        stats_frame = ttk.Frame(self.root)
        stats_frame.pack(fill="x", **pad)

        self.status_label = ttk.Label(
            stats_frame, text="Status: Idle", font=("Segoe UI", 9, "bold"),
        )
        self.status_label.pack(anchor="w")

        self.stats_label = ttk.Label(
            stats_frame, text="Cycles: 0  |  Success: 0", foreground="gray",
        )
        self.stats_label.pack(anchor="w")

        # ---- Progress Bar ----
        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill="x", padx=12, pady=(0, 2))

        # ---- Log ----
        log_frame = ttk.LabelFrame(self.root, text=" Log ", padding=4)
        log_frame.pack(fill="both", expand=True, **pad)

        self.log_area = scrolledtext.ScrolledText(
            log_frame, height=12, font=("Consolas", 9),
            bg="#1e1e1e", fg="#d4d4d4", wrap="word", state="disabled",
        )
        self.log_area.pack(fill="both", expand=True)

        # ---- Bottom ----
        bottom = ttk.Frame(self.root)
        bottom.pack(fill="x", padx=12, pady=(2, 8))
        ttk.Label(
            bottom, text="User taps ad → Program claims reward → Repeat",
            foreground="gray",
        ).pack(side="left")
        ttk.Button(bottom, text="Clear Log", command=self.clear_log).pack(side="right")

    # ================================================================
    # Logging (thread-safe via root.after)
    # ================================================================
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"

        def _append():
            self.log_area.configure(state="normal")
            self.log_area.insert("end", line)
            self.log_area.see("end")
            self.log_area.configure(state="disabled")

        self.root.after(0, _append)
        print(f"[{timestamp}] {msg}")

    # ================================================================
    # Device
    # ================================================================
    def auto_connect(self):
        self.log("Auto-detecting device...")
        self.device = DeviceController()
        if self.device.check_connection():
            info = self.device.get_device_info()
            sw, sh = self.device.get_screen_size()
            self.dev_status.config(
                text=f"Connected: {info.get('manufacturer', '')} {info.get('model', '')}",
                foreground="green",
            )
            self.dev_detail.config(
                text=f"Android {info.get('release', '')}  |  Screen: {sw}x{sh}",
            )
            self.log(f"Device connected: {info.get('model', '')} ({sw}x{sh})")

            self.detector = AdDetector(self.device)
            self.engine = AdEngine(self.device, self.detector, on_log=self.log)
            self.refresh_templates()
            self.start_btn.config(state="normal")
        else:
            self.dev_status.config(text="No device detected", foreground="red")
            self.dev_detail.config(text="Check USB debugging and cable")
            self.start_btn.config(state="disabled")
            self.log("ERROR: No Android device found")
            self.log("  → Enable USB Debugging on your phone")
            self.log("  → Connect via USB and accept the prompt")

    def refresh_device(self):
        self.log("Refreshing device connection...")
        self.auto_connect()

    def refresh_templates(self):
        if self.detector is None:
            return
        for name, status_label in self.tmpl_labels.items():
            tmpl = self.detector.templates.get(name)
            if tmpl is not None:
                h, w = tmpl.shape[:2]
                status_label.config(text=f"OK ({w}x{h})", foreground="green")
            else:
                status_label.config(text="MISSING", foreground="red")

    # ================================================================
    # Template Capture
    # ================================================================
    def capture_template(self):
        if self.device is None:
            messagebox.showerror("Error", "Device not connected")
            return

        names = list(AD_TEMPLATES.keys())
        win = tk.Toplevel(self.root)
        win.title("Capture Template")
        win.geometry("360x320")
        win.transient(self.root)
        win.grab_set()

        ttk.Label(
            win, text="Select template to capture:", font=("Segoe UI", 10),
        ).pack(pady=(12, 8))

        choice_var = tk.StringVar(value=names[0])
        for name in names:
            ttk.Radiobutton(
                win, text=name, variable=choice_var, value=name,
            ).pack(anchor="w", padx=40, pady=2)

        def do_capture():
            name = choice_var.get()
            win.destroy()
            self.log(f"Capturing '{name}' in 3 seconds...")
            self.root.update()
            time.sleep(3)
            os.makedirs(SCREENSHOT_DIR, exist_ok=True)
            path = os.path.join(SCREENSHOT_DIR, f"{name}_full.png")
            if self.device.save_screenshot(path):
                self.log(f"Saved: {path}")
                messagebox.showinfo(
                    "Capture Done",
                    f"Screenshot saved to:\n{path}\n\n"
                    f"Crop the '{name}' element and save as:\n"
                    f"templates/{AD_TEMPLATES[name]}\n\n"
                    f"Then click Refresh to reload templates.",
                )
            else:
                self.log("ERROR: Screenshot failed!")
                messagebox.showerror("Error", "Screenshot failed. Check ADB connection.")

        ttk.Button(win, text="Capture (3s delay)", command=do_capture).pack(pady=(12, 6))
        ttk.Button(win, text="Cancel", command=win.destroy).pack()

    # ================================================================
    # Control
    # ================================================================
    def start(self):
        if self.device is None or self.detector is None or self.engine is None:
            self.refresh_device()
            if self.device is None:
                return

        self.refresh_templates()
        loaded = sum(1 for t in self.detector.templates.values() if t is not None)
        if loaded < 2:
            messagebox.showerror(
                "Error",
                f"Need at least 2 templates, only {loaded} loaded.\n"
                "Use 'Capture Template' to get missing images.",
            )
            return

        # Reset stats
        self.engine.running = True
        self.engine.paused = False
        self.engine.cycle_count = 0
        self.engine.success_count = 0

        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal", text="Pause")
        self.stop_btn.config(state="normal")
        self.refresh_btn.config(state="disabled")
        self.capture_btn.config(state="disabled")
        self.progress.start(8)
        self.status_label.config(text="Status: Running", foreground="green")
        self.log("=== Started ===")
        self.log("Waiting for ad_finished on phone screen...")

        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def toggle_pause(self):
        if self.engine is None:
            return
        self.engine.paused = not self.engine.paused
        if self.engine.paused:
            self.pause_btn.config(text="Resume")
            self.status_label.config(text="Status: Paused", foreground="orange")
            self.progress.stop()
            self.log("--- Paused ---")
        else:
            self.pause_btn.config(text="Pause")
            self.status_label.config(text="Status: Running", foreground="green")
            self.progress.start(8)
            self.log("--- Resumed ---")

    def stop(self):
        if self.engine is None:
            return
        self.engine.running = False
        self.engine.paused = False

        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text="Pause")
        self.stop_btn.config(state="disabled")
        self.refresh_btn.config(state="normal")
        self.capture_btn.config(state="normal")
        self.progress.stop()
        self.status_label.config(text="Status: Stopped", foreground="gray")
        self.log(
            f"=== Stopped "
            f"(cycles: {self.engine.cycle_count}, "
            f"success: {self.engine.success_count}) ==="
        )

    def on_close(self):
        if self.engine:
            self.engine.running = False
        self.root.destroy()

    # ================================================================
    # Main Loop (background thread)
    # ================================================================
    def _run_loop(self):
        """Background worker — delegates to AdEngine."""
        while self.engine.running:
            if self.engine.paused:
                time.sleep(0.3)
                continue

            try:
                ok = self.engine.process_one_ad()
                self.engine.cycle_count += 1
                if ok:
                    self.engine.success_count += 1
            except Exception as e:
                self.log(f"ERROR in ad cycle: {e}")
                time.sleep(2)  # brief pause before retrying

            # Update stats in main thread
            self.root.after(0, self._update_stats)
            time.sleep(CYCLE_INTERVAL)

        self.root.after(0, self._on_thread_stop)

    def _update_stats(self):
        if self.engine is None:
            return
        self.stats_label.config(
            text=f"Cycles: {self.engine.cycle_count}  |  Success: {self.engine.success_count}"
        )

    def _on_thread_stop(self):
        self.progress.stop()
        self.status_label.config(text="Status: Stopped", foreground="gray")

    # ---- Log ----
    def clear_log(self):
        self.log_area.configure(state="normal")
        self.log_area.delete("1.0", "end")
        self.log_area.configure(state="disabled")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = AdClickerGUI()
    app.run()
