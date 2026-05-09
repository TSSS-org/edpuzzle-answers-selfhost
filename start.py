#!/usr/bin/env python3
import os
import sys
import subprocess
import platform

IS_WINDOWS = platform.system() == "Windows"

# ===== colors & UI =====
def c(text, code):
    if IS_WINDOWS:
        return text
    return f"\033[{code}m{text}\033[0m"

def green(t): return c(t, "92")
def cyan(t):  return c(t, "96")
def yellow(t): return c(t, "93")
def bold(t):  return c(t, "1")
def red(t):   return c(t, "91")

def print_logo():
    logo = f"""
{cyan(bold("      ______     __                            __   "))}
{cyan(bold("     / ____/____/ /___  __  __________  ____  / /__ "))}
{cyan(bold("    / __/ / __  / __  / / / / /_  /_  / / __ \\/ / _ \\"))}
{cyan(bold("   / /___/ /_/ / /_/ / /_/ / / /_  / /_/ /_/ / /  __/"))}
{cyan(bold("  /_____/\\__,_/\\__,_/\\__,_/ /___/ /___/ .___/_/\\___/ "))}
{cyan(bold("                                     /_/             "))}
{yellow("                     Launcher v2.0")}
    """
    print(logo)

def main():
    print_logo()
    print(f"  {bold('Welcome to Edpuzzle Answers!')}\n")

    # Smart check: Look for the virtual environment
    venv_python = os.path.join(".venv", "Scripts" if IS_WINDOWS else "bin", "python" + (".exe" if IS_WINDOWS else "3"))
    has_setup = os.path.exists(venv_python)

    # If no environment exists, force them to set up first
    if not has_setup:
        print(yellow("  Looks like this is your first time here!"))
        print(f"  {bold('Let\'s get everything installed and set up.')}\n")
        input(f"  {cyan('Press Enter to start the Setup Process...')} ")
        subprocess.run([sys.executable, "setup.py"])
        return

    # The Main Menu (Only shows if setup is already complete)
    print(f"  {cyan('[ 1 ]')} {bold('Start the Server')}")
    print(f"      {green('->')} Run this if you just want to use the app.")
    print()
    print(f"  {cyan('[ 2 ]')} {bold('Run Setup / Settings')}")
    print(f"      {green('->')} Run this to change ports, add an AI key, or fix errors.")
    print()

    while True:
        choice = input(f"  {bold('What would you like to do? (1/2): ')}").strip()

        if choice == "1":
            print(f"\n  {green('Starting Server...')}")
            subprocess.run([venv_python, os.path.join("server", "main.py")])
            break
        elif choice == "2":
            print(f"\n  {green('Starting Setup...')}")
            subprocess.run([sys.executable, "setup.py"])
            break
        else:
            print(yellow("  Please type 1 or 2."))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print(yellow("\n  Goodbye!"))
        sys.exit(0)