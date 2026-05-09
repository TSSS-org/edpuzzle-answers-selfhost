#!/usr/bin/env python3
# Edpuzzle Answers - Automated Setup Script
# Supports Windows, macOS, and Linux

import os
import sys
import json
import shutil
import socket
import subprocess
import platform
import argparse
import time
import threading
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "server", "config", "config.json")
DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "server", "config", "default.json")
VENV_DIR = os.path.join(BASE_DIR, ".venv")

IS_WINDOWS = platform.system() == "Windows"

# ===== colors & UI =====
def c(text, code):
    if IS_WINDOWS:
        return text
    return f"\033[{code}m{text}\033[0m"

def green(t): return c(t, "92")
def red(t):   return c(t, "91")
def yellow(t): return c(t, "93")
def bold(t):  return c(t, "1")
def cyan(t):  return c(t, "96")

def print_logo():
    logo = f"""
{cyan(bold("___________    .___                           .__                      _____                                              "))}
{cyan(bold(r"\_   _____/  __| _/_____  __ _________________|  |   ____             /  _  \   ____   ________  _  __ ___________  ______"))}
{cyan(bold(r" |    __)_  / __ |\____ \|  |  \___   /\___   /  | _/ __ \   ______  /  /_\  \ /    \ /  ___/\ \/ \/ // __ \_  __ \/  ___/"))}
{cyan(bold(r" |        \/ /_/ ||  |_> >  |  //    /  /    /|  |_\  ___/  /_____/ /    |    \   |  \\___ \  \     /\  ___/|  | \/\___ \ "))}
{cyan(bold(r"/_______  /\____ ||   __/|____//_____ \/_____ \____/\___  >         \____|__  /___|  /____  >  \/\_/  \___  >__|  /____  >"))}
{cyan(bold(r"        \/      \/|__|               \/      \/         \/                  \/     \/     \/              \/           \/ "))}
{yellow(r"                                                    Self-Hosted Setup Helper v2.0")}
    """
    print(logo)

def header(text):
    print()
    print(bold("=" * 54))
    print(bold(f"  {text}"))
    print(bold("=" * 54))

def ok(text):   print(green("  ✓ ") + text)
def err(text):  print(red("  ✗ ") + text)
def info(text): print(cyan("  → ") + text)
def warn(text): print(yellow("  ! ") + text)

class Spinner:
    """A simple terminal spinner for long tasks"""
    def __init__(self, message="Working..."):
        self.message = message
        self.stop_running = False
        self.thread = threading.Thread(target=self._animate)

    def _animate(self):
        chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        while not self.stop_running:
            sys.stdout.write(f"\r  {cyan(chars[i % len(chars)])} {self.message}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_running = True
        self.thread.join()
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")

# ===== helpers =====
def get_python():
    return sys.executable

def get_venv_python():
    if IS_WINDOWS:
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python3")

def get_venv_pip():
    if IS_WINDOWS:
        return os.path.join(VENV_DIR, "Scripts", "pip.exe")
    return os.path.join(VENV_DIR, "bin", "pip3")

def get_venv_playwright():
    if IS_WINDOWS:
        return os.path.join(VENV_DIR, "Scripts", "playwright.exe")
    return os.path.join(VENV_DIR, "bin", "playwright")

def run(cmd, spinner_msg=None, **kwargs):
    if IS_WINDOWS and cmd[0] == "npm":
        cmd[0] = "npm.cmd"
    
    if spinner_msg:
        with Spinner(spinner_msg):
            return subprocess.run(cmd, **kwargs)
    else:
        return subprocess.run(cmd, **kwargs)

def ask(prompt, default=None):
    if default:
        result = input(f"\n  {prompt} [{green(default)}]: ").strip()
        return result if result else default
    else:
        while True:
            result = input(f"\n  {prompt}: ").strip()
            if result:
                return result
            print(red("  This field cannot be empty."))

def ask_yn(prompt, default="y"):
    while True:
        # Display the default option in uppercase and colored
        options = f"[{green('Y')}/n]" if default == "y" else f"[y/{green('N')}]"
        
        result = input(f"\n  {prompt} {options}: ").strip().lower()
        if not result:
            return default == "y"
        if result in ("y", "yes"):
            return True
        if result in ("n", "no"):
            return False
        print(red("  Please enter y or n."))

def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0

# ===== tester / developer actions =====
def nuke_local_env():
    header("Cleaning Environment")
    
    # 1. Delete all the generated folders (Removed "server/config" from this list)
    to_delete_folders = [VENV_DIR, "node_modules", "dist", "__pycache__"]
    for folder in to_delete_folders:
        path = os.path.join(BASE_DIR, folder)
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                ok(f"Deleted {folder}")
            except Exception as e:
                warn(f"Could not delete folder {folder}: {e}")

    # 2. Delete ONLY the config.json file, leaving default.json alone
    if os.path.exists(CONFIG_PATH):
        try:
            os.remove(CONFIG_PATH)
            ok("Deleted config.json")
        except Exception as e:
            warn(f"Could not delete config.json: {e}")

    print()
    ok("Clean slate achieved! Starting fresh setup...")
    time.sleep(1)

# ===== steps =====
def check_dependencies():
    header("Step 1: System Checks")

    if IS_WINDOWS:
        system32 = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32')
        if not os.path.exists(os.path.join(system32, "vcruntime140.dll")):
            warn("Microsoft Visual C++ Redistributable is missing!")
            print("  This is required for the app to run on Windows.")
            info("Opening download page... please install the X64 version.")
            webbrowser.open("https://aka.ms/vs/17/release/vc_redist.x64.exe")
            input(f"\n  {bold('Press Enter AFTER you have finished installing the Redistributable...')} ")

    major, minor = sys.version_info[:2]
    if major < 3 or minor < 9:
        err(f"Python 3.9+ is required. You have {major}.{minor}.")
        err("Download it from https://python.org")
        sys.exit(1)
    ok(f"Python {major}.{minor} detected")

    node = shutil.which("node")
    if not node:
        err("Node.js is not installed.")
        err("Download it from https://nodejs.org (npm is included)")
        sys.exit(1)
    node_ver = run(["node", "--version"], capture_output=True, text=True).stdout.strip()
    ok(f"Node.js {node_ver} detected")

    npm = shutil.which("npm")
    if not npm:
        err("npm is not installed. It should come with Node.js.")
        err("Try reinstalling Node.js from https://nodejs.org")
        sys.exit(1)
    npm_ver = run(["npm", "--version"], capture_output=True, text=True).stdout.strip()
    ok(f"npm {npm_ver} detected")

def setup_venv():
    header("Step 2: Python Environment")
    if os.path.exists(VENV_DIR):
        ok("Virtual environment already exists, skipping.")
        return
    result = run([get_python(), "-m", "venv", VENV_DIR], spinner_msg="Creating isolated Python space...")
    if result.returncode != 0:
        err("Failed to create virtual environment.")
        sys.exit(1)
    ok("Python environment created.")

def install_python_deps():
    header("Step 3: Python Dependencies")
    req_path = os.path.join(BASE_DIR, "requirements.txt")
    if not os.path.exists(req_path):
        err("requirements.txt not found. Are you in the right folder?")
        sys.exit(1)
    result = run([get_venv_pip(), "install", "-r", req_path, "-q"], spinner_msg="Downloading Python packages (this takes a minute)...")
    if result.returncode != 0:
        err("Failed to install Python dependencies.")
        sys.exit(1)
    ok("Python dependencies installed.")

def install_playwright():
    result = run([get_venv_playwright(), "install", "chromium"], spinner_msg="Downloading browser engine for Teacher Login...")
    if result.returncode != 0:
        err("Failed to install Playwright Chromium.")
        sys.exit(1)
    ok("Browser engine installed.")

def install_node_deps():
    header("Step 4: Frontend & App UI")
    result = run(["npm", "install"], cwd=BASE_DIR, spinner_msg="Downloading Node.js packages...")
    if result.returncode != 0:
        err("npm install failed.")
        sys.exit(1)
    ok("Node packages installed.")

    result = run(["npm", "run", "build:prod"], cwd=BASE_DIR, spinner_msg="Building the user interface...")
    if result.returncode != 0:
        err("Frontend build failed.")
        sys.exit(1)
    ok("User interface built successfully.")

def setup_config():
    header("Step 5: App Configuration")

    if os.path.exists(CONFIG_PATH):
        warn("config.json already exists.")
        if not ask_yn("Do you want to reconfigure it?", default="n"):
            ok("Keeping existing config.")
            return

    print(f"\n  {bold('Let\'s set up your settings.')}")
    print("  For most people, simply pressing [Enter] for every question is perfect.")

    print(f"\n  {bold('1. Network Port')}")
    print("  This is the 'door' your computer uses to show the app.")
    print("  Default is 8080. Only change this if you know what you are doing.")
    
    while True:
        port_str = ask("What port should the app run on?", default="8080")
        try:
            port = int(port_str)
        except ValueError:
            warn("Please enter a valid number.")
            continue
            
        if port_in_use(port):
            warn(f"Port {port} is currently being used by another app!")
            suggested = port + 1
            while port_in_use(suggested): 
                suggested += 1
            
            if ask_yn(f"Would you like to use Port {suggested} instead?", default="y"):
                port = suggested
                ok(f"Switched to port {port}")
                break
            else:
                err("Cannot continue while port is busy. Close the other app and try again.")
        else:
            break

    origin = f"http://localhost:{port}"

    print(f"\n  {bold('2. AI Features (Optional)')}")
    print("  The Gemini API key enables AI-powered open-ended answers.")
    print("  Get a free key at: https://aistudio.google.com/apikey")
    use_gemini = ask_yn("Do you have a Gemini API key?", default="n")
    if use_gemini:
        gemini_key = ask("Paste your Gemini API key")
        gemini_model = ask("Gemini model to use", default="gemini-3.1-flash-lite-preview")
    else:
        gemini_key = "GEMINI_KEY"
        gemini_model = "gemini-3.1-flash-lite-preview"
        warn("Skipping Gemini — AI open-ended answers will not work.")

    print(f"\n  {bold('3. Advanced')}")
    dev_mode = ask_yn("Enable dev mode? (only for developers)", default="n")

    config = {
        "dev_mode": dev_mode,
        "include_traceback": dev_mode,
        "behind_proxy": False,
        "gzip_responses": True,
        "server_port": port,
        "limiter_storage_uri": "memory://",
        "origin": origin,
        "teacher_token": "",
        "gemini": {
            "key": gemini_key,
            "model": gemini_model
        },
        "rate_limit": {
            "captions": "60/minute",
            "generate": "60/minute",
            "media": "60/minute"
        }
    }

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    ok("Configuration saved successfully!")
    header("Setup Complete!")
    print(f"  {green('You can now start the server.')}")
    print(f"  {green('Next time, just double-click your Start launcher file!')}")

def start_server():
    print()
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            config = json.load(f)

    token = config.get("teacher_token", "").strip()
    port = config.get("server_port", 8080)
    origin = config.get("origin", f"http://localhost:{port}")

    if not token:
        print(bold("  A browser window will open for you to log into your"))
        print(bold("  Edpuzzle TEACHER account. The window will close"))
        print(bold("  automatically once you've signed in."))
        print()
    else:
        print("  Teacher token found — skipping browser login.")

    print()
    info("Launching server...")
    
    # Wait for the actual server to spin up before opening the browser
    def open_browser():
        # This loop polls the port. Once it's in use, it means Playwright is done
        # and the Flask server has successfully bound to the port.
        for _ in range(600): # Waits up to 10 minutes in the background
            if port_in_use(port):
                time.sleep(0.5) # Give Flask a fraction of a second to fully stabilize
                webbrowser.open(origin)
                break
            time.sleep(1)
    
    # Daemon=True ensures this background listening stops if the main script crashes
    threading.Thread(target=open_browser, daemon=True).start()

    print(f"  {green('The app should open automatically in your browser after you log in.')}")
    print(f"  {green('If it does not, go to:')} {bold(cyan(origin))}")
    print(f"\n  {yellow('Press CTRL+C in this window to stop the server.')}\n")

    server_path = os.path.join(BASE_DIR, "server", "main.py")
    run([get_venv_python(), server_path])

# ===== main =====
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--clean', action='store_true', help='Delete environment and start over')
    args, unknown = parser.parse_known_args()

    if args.clean:
        nuke_local_env()

    # If config exists and setup already done, just start
    already_setup = (
        os.path.exists(CONFIG_PATH) and
        os.path.exists(VENV_DIR) and
        os.path.exists(os.path.join(BASE_DIR, "dist"))
    )

    if already_setup and not args.clean:
        if ask_yn("Setup is already complete. Do you want to start the server?", default="y"):
            start_server()
        return

    check_dependencies()
    setup_venv()
    install_python_deps()
    install_playwright()
    install_node_deps()
    setup_config()
    
    print()
    if ask_yn("Would you like to start the server now?", default="y"):
        start_server()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print(yellow("\n  Process stopped by user."))
        sys.exit(0)