#!/usr/bin/env bash
# Cross-Platform CachyOS / Linux Launcher for J.A.R.V.I.S. Android & Scrcpy DeX Studio
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Verify dependencies on CachyOS / Arch Linux
if ! command -v adb >/dev/null 2>&1 || ! command -v scrcpy >/dev/null 2>&1; then
    echo "[*] Installing android-tools (adb) and scrcpy via pacman..."
    sudo pacman -S --needed --noconfirm android-tools scrcpy tk
fi

PYTHON_BIN="python3"
if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif ! python3 -c "import customtkinter, psutil" >/dev/null 2>&1; then
    echo "[*] Setting up local Python venv with customtkinter & psutil..."
    python3 -m venv "$SCRIPT_DIR/.venv"
    "$SCRIPT_DIR/.venv/bin/pip" install --upgrade pip customtkinter psutil pillow
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
fi

nohup "$PYTHON_BIN" "$SCRIPT_DIR/adb_scrcpy_studio.py" >/dev/null 2>&1 &
echo "[+] Launched J.A.R.V.I.S. Android & Scrcpy DeX Studio (PID $!)"
