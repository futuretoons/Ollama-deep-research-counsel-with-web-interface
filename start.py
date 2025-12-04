import subprocess
import os
import sys
import time
import requests
from importlib import import_module

def check_and_install(package, import_name=None):
    if import_name is None:
        import_name = package.replace('-', '_')
    try:
        import_module(import_name)
        print(f"{import_name} is already installed.")
    except ImportError:
        response = input(f"{package} is not installed. Do you want to install it? (y/n): ").strip().lower()
        if response == 'y':
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"{package} installed successfully.")
        else:
            print(f"Skipping installation of {package}.")
            sys.exit(1)

packages = [
    ('requests', 'requests'),
    ('flask', 'flask'),
    ('flask-cors', 'flask_cors'),
    ('beautifulsoup4', 'bs4')
]

for pkg, imp in packages:
    check_and_install(pkg, imp)

print("Checking if Ollama is running...")
time.sleep(2)

try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        print("Ollama is running.")
    else:
        raise Exception()
except Exception:
    response = input("Ollama is not running. Do you want to start it? (y/n): ").strip().lower()
    if response == 'y':
        subprocess.Popen(["ollama", "serve"])
        print("Starting Ollama... waiting 10 seconds for it to start.")
        time.sleep(10)
    else:
        print("Ollama not started. Exiting.")
        sys.exit(1)

# Starts the Counsel..
subprocess.call([sys.executable, "app.py"])