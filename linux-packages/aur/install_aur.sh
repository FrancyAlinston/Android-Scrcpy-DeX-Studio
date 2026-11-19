#!/usr/bin/env bash
# 1-Click CachyOS / Arch Linux AUR Package Builder & Installer
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"
echo "[*] Building and installing android-scrcpy-dex-studio v3.0.0 via makepkg..."
makepkg -si --noconfirm
echo "[+] android-scrcpy-dex-studio installed! Launch from App Menu or run: android-scrcpy-dex-studio"
