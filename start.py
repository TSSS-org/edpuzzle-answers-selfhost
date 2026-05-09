import subprocess
import sys
import os

# Activate venv and start server
venv_python = os.path.join(".venv", "Scripts" if sys.platform == "win32" else "bin", "python")

if not os.path.exists(venv_python):
    print("Virtual environment not found. Please run setup.py first.")
    sys.exit(1)

subprocess.run([venv_python, "server/main.py"])