#!/bin/bash
# Sovereign Engine Core — Linux/macOS Installer
echo "=== Sovereign Engine Core Setup ==="

cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3 is required but not installed."
    echo "Please install python3 and python3-venv."
    exit 1
fi

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Installing dependencies..."
if ! .venv/bin/python3 -m pip --version >/dev/null 2>&1; then
    echo "[GUARDIAN] pip missing in venv. Bootstrapping via local get-pip.py..."
    .venv/bin/python3 vendor/get-pip.py --no-index --find-links=vendor pip setuptools wheel
fi

.venv/bin/python3 -m pip install --no-index --find-links=vendor --upgrade pip
.venv/bin/python3 -m pip install --no-index --find-links=vendor -r requirements.txt

echo "Setting up configuration..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Generated .env from .env.example"
    fi
fi

echo ""
echo "INSTALLATION COMPLETE"
echo "====================="
