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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "server", "config", "config.json")
DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "server", "config", "default.json")
VENV_DIR = os.path.join(BASE_DIR, ".venv")

IS_WINDOWS = platform.system() == "Windows"

# ===== colors =====
def c(text, code):
    if IS_WINDOWS:
        return text
    return f"\033[{code}m{text}\033[0m"

def green(t): return c(t, "92")
def red(t):   return c(t, "91")
def yellow(t): return c(t, "93")
def bold(t):  return c(t, "1")
def cyan(t):  return c(t, "96")

def header(text):
    print()
    print(bold("=" * 54))
    print(bold(f"  {text}"))
    print(bold("=" * 54))

def ok(text):   print(green("  ✓ ") + text)
def err(text):  print(red("  ✗ ") + text)
def info(text): print(cyan("  → ") + text)
def warn(text): print(yellow("  ! ") + text)

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

def run(cmd, **kwargs):
    # On Windows, 'npm' must be called as 'npm.cmd' when not using shell=True
    if IS_WINDOWS and cmd[0] == "npm":
        cmd[0] = "npm.cmd"
    return subprocess.run(cmd, **kwargs)

def ask(prompt, default=None):
    if default:
        result = input(f"\n  {prompt} [{default}]: ").strip()
        return result if result else default
    else:
        while True:
            result = input(f"\n  {prompt}: ").strip()
            if result:
                return result
            print(red("  This field cannot be empty."))

def ask_yn(prompt, default="y"):
    while True:
        result = input(f"\n  {prompt} (y/n) [{default}]: ").strip().lower()
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

# ===== steps =====
def check_dependencies():
    header("Checking Dependencies")

    # Python version
    major, minor = sys.version_info[:2]
    if major < 3 or minor < 9:
        err(f"Python 3.9+ is required. You have {major}.{minor}.")
        err("Download it from https://python.org")
        sys.exit(1)
    ok(f"Python {major}.{minor}")

    # Node
    node = shutil.which("node")
    if not node:
        err("Node.js is not installed.")
        err("Download it from https://nodejs.org (npm is included)")
        sys.exit(1)
    node_ver = run(["node", "--version"], capture_output=True, text=True).stdout.strip()
    ok(f"Node.js {node_ver}")

    # npm
    npm = shutil.which("npm")
    if not npm:
        err("npm is not installed. It should come with Node.js.")
        err("Try reinstalling Node.js from https://nodejs.org")
        sys.exit(1)
    npm_ver = run(["npm", "--version"], capture_output=True, text=True).stdout.strip()
    ok(f"npm {npm_ver}")

def setup_venv():
    header("Setting Up Python Environment")

    if os.path.exists(VENV_DIR):
        ok("Virtual environment already exists, skipping.")
        return

    info("Creating virtual environment...")
    result = run([get_python(), "-m", "venv", VENV_DIR])
    if result.returncode != 0:
        err("Failed to create virtual environment.")
        sys.exit(1)
    ok("Virtual environment created.")

def install_python_deps():
    header("Installing Python Dependencies")

    req_path = os.path.join(BASE_DIR, "requirements.txt")
    if not os.path.exists(req_path):
        err("requirements.txt not found. Are you in the right folder?")
        sys.exit(1)

    info("Installing packages (this may take a minute)...")
    result = run([get_venv_pip(), "install", "-r", req_path, "-q"])
    if result.returncode != 0:
        err("Failed to install Python dependencies.")
        sys.exit(1)
    ok("Python dependencies installed.")

def install_playwright():
    header("Installing Playwright Browser")

    info("Installing Chromium browser for teacher login...")
    result = run([get_venv_playwright(), "install", "chromium"])
    if result.returncode != 0:
        err("Failed to install Playwright Chromium.")
        sys.exit(1)
    ok("Chromium installed.")

def install_node_deps():
    header("Installing Node.js Dependencies & Building Frontend")

    info("Installing npm packages...")
    result = run(["npm", "install"], cwd=BASE_DIR)
    if result.returncode != 0:
        err("npm install failed.")
        sys.exit(1)
    ok("Node packages installed.")

    info("Building frontend (this may take a moment)...")
    result = run(["npm", "run", "build:prod"], cwd=BASE_DIR)
    if result.returncode != 0:
        err("Frontend build failed.")
        sys.exit(1)
    ok("Frontend built successfully.")

def setup_config():
    header("Configuration")

    if os.path.exists(CONFIG_PATH):
        warn("config.json already exists.")
        if not ask_yn("Do you want to reconfigure it?", default="n"):
            ok("Keeping existing config.")
            return

    print()
    print("  Answer the following questions to set up your config.")
    print("  Press Enter to accept the default value shown in [brackets].")

    # Port
    print()
    while True:
        port_str = ask("What port should the server run on?", default="8080")
        try:
            port = int(port_str)
        except ValueError:
            print(red("  Please enter a valid number."))
            continue
        if port_in_use(port):
            warn(f"Port {port} is already in use.")
            if IS_WINDOWS:
                warn("On Windows, check Task Manager for what's using it.")
            else:
                warn(f"Run: lsof -i :{port}   to see what's using it.")
            if not ask_yn(f"Use port {port} anyway?", default="n"):
                continue
        break

    origin = f"http://localhost:{port}"

    # Gemini
    print()
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

    # Dev mode
    dev_mode = ask_yn("Enable dev mode? (only for developers)", default="n")

    # Build config
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

    ok(f"Config saved to server/config/config.json")
    ok(f"Server will run on {origin}")

def start_server():
    header("Starting Server")

    print()
    print("  The server is about to start.")
    print()

    # Check if token is empty — warn the user what's about to happen
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            config = json.load(f)

    token = config.get("teacher_token", "").strip()
    if not token:
        print(bold("  A browser window will open for you to log into your"))
        print(bold("  Edpuzzle TEACHER account. The window will close"))
        print(bold("  automatically once you've signed in."))
        print()
        print("  After that, the server starts and you won't need to")
        print("  log in again unless your token expires (~7 days).")
    else:
        print("  Token found in config — skipping browser login.")

    print()
    info("Launching server...")
    print()

    server_path = os.path.join(BASE_DIR, "server", "main.py")
    run([get_venv_python(), server_path])

# ===== main =====
def main():
    print()
    print(bold(cyan("  Edpuzzle Answers — Self-Host Setup")))
    print(bold(cyan("  ====================================")))

    # If config exists and setup already done, just start
    already_setup = (
        os.path.exists(CONFIG_PATH) and
        os.path.exists(VENV_DIR) and
        os.path.exists(os.path.join(BASE_DIR, "dist"))
    )

    if already_setup:
        header("Setup Already Complete")
        ok("Config, venv, and dist folder all found.")
        if ask_yn("Run setup again from scratch?", default="n"):
            already_setup = False
        else:
            start_server()
            return

    if not already_setup:
        check_dependencies()
        setup_venv()
        install_python_deps()
        install_playwright()
        install_node_deps()
        setup_config()
        start_server()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print(yellow("\n  Setup cancelled."))
        sys.exit(0)