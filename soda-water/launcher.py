"""
Soda Music Ad Clicker - Launcher
=================================
Double-click this file to start (or run: python launcher.py)
"""

import os
import sys
import subprocess
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

MENU = """
================================================
  Soda Music Ad Auto-Clicker
================================================

  [1] Start      auto-clicker (CLI + hotkeys)
  [2] GUI         desktop control panel
  [3] Web UI      browser at http://127.0.0.1:8765

  [4] Capture     first-time template setup
  [5] Test        verify templates on screen
  [6] Install     reinstall dependencies

  [0] Exit
================================================
"""


def check_deps():
    """Check if core dependencies are installed."""
    try:
        import cv2      # noqa: F401
        import numpy    # noqa: F401
        return True
    except ImportError:
        return False


def install_deps():
    print("\nInstalling dependencies...\n")
    ok = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=HERE,
    ).returncode == 0
    if ok:
        print("\nDone! Dependencies installed.")
    else:
        print("\nWARNING: Some dependencies may have failed to install.")
        print("Try running as Administrator or install manually:")
        print("  pip install opencv-python numpy keyboard pillow")
    return ok


def run_script(filename, *args):
    """Run a Python script in the same directory."""
    path = os.path.join(HERE, filename)
    cmd = [sys.executable, path] + list(args)
    return subprocess.run(cmd, cwd=HERE).returncode


def check_adb():
    """Check if ADB is available on PATH."""
    return shutil.which("adb") is not None


def main():
    # First-time dependency check
    if not check_deps():
        print("\nDependencies not installed. Installing now...")
        install_deps()
        if not check_deps():
            input("\nDependency check failed. Press Enter to exit.")
            return

    # ADB check (warn but don't block)
    if not check_adb():
        print("\n" + "=" * 48)
        print("  WARNING: ADB not found on PATH!")
        print("=" * 48)
        print()
        print("  ADB is required to communicate with your phone.")
        print("  Download: https://developer.android.com/studio/releases/platform-tools")
        print("  Extract to C:\\platform-tools and add to system PATH.")
        print()
        input("Press Enter to continue anyway...")

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(MENU)
        try:
            choice = input("Enter choice [0-6]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == "0":
            print("Goodbye.")
            break
        elif choice == "1":
            print("\nStarting CLI mode (Ctrl+C to stop)...\n")
            run_script("main.py", "--now")
            input("\nPress Enter to return to menu...")
        elif choice == "2":
            print("\nStarting GUI... (close the GUI window to return)\n")
            run_script("gui.py")
        elif choice == "3":
            print("\nOpening http://127.0.0.1:8765 in browser...\n")
            print("Press Ctrl+C to stop the server.\n")
            if os.name == "nt":
                os.startfile("http://127.0.0.1:8765")
            run_script("server.py")
            input("\nPress Enter to return to menu...")
        elif choice == "4":
            run_script("main.py", "--capture")
            input("\nPress Enter to return to menu...")
        elif choice == "5":
            run_script("main.py", "--test")
            input("\nPress Enter to return to menu...")
        elif choice == "6":
            install_deps()
            input("\nPress Enter to return to menu...")
        else:
            print("Invalid choice, try again.")


if __name__ == "__main__":
    main()
