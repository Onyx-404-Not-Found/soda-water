"""
Soda Music Ad Auto-Clicker — Web Server
========================================
Provides a browser-based control panel at http://127.0.0.1:8765

Usage:
  python server.py
  Then open http://127.0.0.1:8765 in your browser.
"""

import sys
import os
import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

from config import (
    AD_TEMPLATES, CYCLE_INTERVAL,
    SERVER_HOST, SERVER_PORT, SCREENSHOT_DIR,
)
from ad_detector import AdDetector
from device_controller import DeviceController
from engine import AdEngine

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Thread-safe log buffer (simple lock + list)
# ---------------------------------------------------------------------------
_log_lock = threading.Lock()
_log_lines = []


def add_log(msg):
    """Thread-safe: add a message to the in-memory log."""
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with _log_lock:
        _log_lines.append(line)
        # Keep only last 200 lines to bound memory
        if len(_log_lines) > 200:
            _log_lines[:] = _log_lines[-100:]


def get_logs():
    """Return recent log lines (up to last 100)."""
    with _log_lock:
        return {"lines": list(_log_lines[-100:])}


# ---------------------------------------------------------------------------
# Threading HTTP server — each request runs in its own thread,
# so long operations (like capture screenshots) don't block the UI.
# ---------------------------------------------------------------------------
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
class AppState:
    def __init__(self):
        self.device = None
        self.detector = None
        self.engine = None
        self.thread = None


state = AppState()


# ---------------------------------------------------------------------------
# Device init
# ---------------------------------------------------------------------------
def init_device():
    """Lazy-init device connection."""
    if state.device is None:
        state.device = DeviceController()
        state.device.check_connection()
    if state.detector is None:
        state.detector = AdDetector(state.device)
    if state.engine is None:
        state.engine = AdEngine(state.device, state.detector, on_log=add_log)


# ---------------------------------------------------------------------------
# Screenshot cleanup
# ---------------------------------------------------------------------------
def clear_screenshots():
    ss_dir = SCREENSHOT_DIR
    count = 0
    if os.path.isdir(ss_dir):
        for f in os.listdir(ss_dir):
            if f.lower().endswith((".png", ".jpg", ".jpeg")):
                os.remove(os.path.join(ss_dir, f))
                count += 1
    add_log(f"Cleared {count} screenshots")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def runner_loop():
    """Background thread: continuously process ad cycles."""
    while state.engine.running:
        if state.engine.paused:
            time.sleep(0.3)
            continue
        try:
            ok = state.engine.process_one_ad()
            state.engine.cycle_count += 1
            if ok:
                state.engine.success_count += 1
        except Exception as e:
            add_log(f"Error in ad cycle: {e}")
        time.sleep(CYCLE_INTERVAL)


def start_runner():
    """Start the ad-clicking loop (idempotent)."""
    init_device()

    # Prevent double-start
    if state.engine.running:
        add_log("Already running!")
        return

    # Check templates
    loaded = sum(1 for t in state.detector.templates.values() if t is not None)
    if loaded < 2:
        add_log(f"ERROR: Only {loaded} templates loaded — need at least 2!")
        return

    state.engine.running = True
    state.engine.paused = False
    state.engine.cycle_count = 0
    state.engine.success_count = 0

    state.thread = threading.Thread(target=runner_loop, daemon=True)
    state.thread.start()
    add_log("=== Started ===")


def stop_runner():
    """Stop the ad-clicking loop."""
    state.engine.running = False
    state.engine.paused = False
    add_log(
        f"=== Stopped "
        f"({state.engine.cycle_count} cycles, {state.engine.success_count} success) ==="
    )


def toggle_pause():
    """Toggle pause state."""
    state.engine.paused = not state.engine.paused
    add_log(f"--- {'Paused' if state.engine.paused else 'Resumed'} ---")


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
def get_status():
    """Build a JSON-serializable status dict for the web UI."""
    init_device()
    dev_ok = state.device is not None and state.device.serial is not None
    sw, sh = 0, 0
    info = {}
    if dev_ok:
        try:
            info = state.device.get_device_info()
            sw, sh = state.device.get_screen_size()
        except Exception:
            dev_ok = False

    templates = []
    if state.detector:
        for name in AD_TEMPLATES:
            tmpl = state.detector.templates.get(name)
            if tmpl is not None:
                h, w = tmpl.shape[:2]
                templates.append({"name": name, "ok": True, "w": w, "h": h})
            else:
                templates.append({"name": name, "ok": False, "w": 0, "h": 0})

    running = state.engine.running if state.engine else False
    paused = state.engine.paused if state.engine else False

    if running and paused:
        status, color = "Paused", "orange"
    elif running:
        status, color = "Running", "green"
    else:
        status, color = "Idle", "gray"

    return {
        "dev_ok": dev_ok,
        "dev_model": info.get("model", ""),
        "dev_android": info.get("release", ""),
        "dev_screen": f"{sw}x{sh}",
        "templates": templates,
        "tmpl_names": list(AD_TEMPLATES.keys()),
        "running": running,
        "paused": paused,
        "status": status,
        "color": color,
        "cycles": state.engine.cycle_count if state.engine else 0,
        "success": state.engine.success_count if state.engine else 0,
    }


# ---------------------------------------------------------------------------
# HTTP Request Handler
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress access logs

    def _send_json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_html(self):
        path = os.path.join(HERE, "index.html")
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self._send_json(500, {"error": "index.html not found"})

    # ---- GET ----
    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            self._serve_html()
        elif path == "/api/status":
            self._send_json(200, get_status())
        elif path == "/api/log":
            self._send_json(200, get_logs())
        elif path == "/api/refresh":
            init_device()
            self._send_json(200, get_status())
        elif path == "/api/clear_screenshots":
            clear_screenshots()
            self._send_json(200, {"ok": True})
        elif path == "/api/start":
            start_runner()
            self._send_json(200, get_status())
        elif path == "/api/stop":
            stop_runner()
            self._send_json(200, get_status())
        elif path == "/api/pause":
            toggle_pause()
            self._send_json(200, get_status())
        else:
            self._send_json(404, {"error": "not found"})

    # ---- POST ----
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        path = urlparse(self.path).path

        if path == "/api/capture":
            name = body.get("name", "")
            if not name or state.device is None:
                self._send_json(400, {"error": "No device or missing template name"})
                return

            add_log(f"Capturing '{name}' in 3s...")
            time.sleep(3)  # safe — each request is in its own thread now

            os.makedirs(SCREENSHOT_DIR, exist_ok=True)
            fpath = os.path.join(SCREENSHOT_DIR, f"{name}_full.png")
            if state.device.save_screenshot(fpath):
                add_log(f"Saved: {fpath}")
                self._send_json(200, {"ok": True, "path": fpath})
            else:
                self._send_json(500, {"error": "Screenshot failed"})

        elif path == "/api/clear_screenshots":
            clear_screenshots()
            self._send_json(200, {"ok": True})

        elif path == "/api/start":
            start_runner()
            self._send_json(200, get_status())

        elif path == "/api/stop":
            stop_runner()
            self._send_json(200, get_status())

        elif path == "/api/pause":
            toggle_pause()
            self._send_json(200, get_status())

        else:
            self._send_json(404, {"error": "not found"})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    add_log(f"Server starting at http://{SERVER_HOST}:{SERVER_PORT}")
    add_log("Open this URL in your browser to control the ad clicker.")
    add_log("Press Ctrl+C to stop the server.")

    server = ThreadingHTTPServer((SERVER_HOST, SERVER_PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        add_log("Server stopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
