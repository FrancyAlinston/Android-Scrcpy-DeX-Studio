#!/usr/bin/env python3
"""
Dual-Host Automated Deployer for J.A.R.V.I.S. Android & Scrcpy DeX Studio:
1. Installs on Windows Workstation (H:\Program Files\Android Scrcpy DeX Studio, Desktop/Start Menu, Downloads)
2. Installs on ASUS Vivobook 15 Laptop (DOOMSDAY - dsilva@192.168.8.247) over SSH via makepkg / pacman
   and configures Passwordless ED25519 SSH key auth from Windows Workstation to DOOMSDAY.
"""

import os
import sys
import subprocess
import win32cred
import paramiko

STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))
DOOMSDAY_IP = "192.168.8.247"
DOOMSDAY_USER = "dsilva"


def get_homelab_password() -> str:
    cred = win32cred.CredRead("TERMSRV/192.168.8.179", win32cred.CRED_TYPE_GENERIC)
    return cred["CredentialBlob"].decode("utf-16le").rstrip("\x00").strip()


def deploy_windows() -> None:
    print("[*] Deploying v2.2.0 on Windows 11 Workstation...")
    ps1 = os.path.join(STUDIO_DIR, "install_windows.ps1")
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1],
        check=True,
    )


def deploy_asus_doomsday() -> None:
    print(f"[*] Connecting to ASUS Laptop (DOOMSDAY - {DOOMSDAY_USER}@{DOOMSDAY_IP})...")
    pwd = get_homelab_password()

    # Ensure Windows Workstation has an ed25519 SSH key authorized on DOOMSDAY for future instant sync
    ssh_dir = os.path.expanduser("~/.ssh")
    os.makedirs(ssh_dir, exist_ok=True)
    key_path = os.path.join(ssh_dir, "id_ed25519_doomsday")
    pub_path = key_path + ".pub"
    if not os.path.isfile(key_path):
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-f", key_path], check=True)

    with open(pub_path, "r", encoding="utf-8") as f:
        pub_key = f.read().strip()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(DOOMSDAY_IP, port=22, username=DOOMSDAY_USER, password=pwd, timeout=10)

    # 1. Authorize SSH key on DOOMSDAY
    auth_cmd = (
        f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && "
        f"grep -qF '{pub_key}' ~/.ssh/authorized_keys 2>/dev/null || echo '{pub_key}' >> ~/.ssh/authorized_keys && "
        f"chmod 600 ~/.ssh/authorized_keys"
    )
    client.exec_command(auth_cmd)[1].read()

    # 2. Upload AUR build suite via SFTP to /tmp/aur-android-scrcpy-dex-studio
    sftp = client.open_sftp()
    remote_build_dir = "/tmp/aur-android-scrcpy-dex-studio"
    client.exec_command(f"rm -rf {remote_build_dir} && mkdir -p {remote_build_dir}")[1].read()

    local_aur_dir = os.path.join(STUDIO_DIR, "linux-packages", "aur")
    for fname in ["PKGBUILD", ".SRCINFO", "android-scrcpy-dex-studio-3.1.0.tar.gz", "install_aur.sh"]:
        lpath = os.path.join(local_aur_dir, fname)
        if os.path.isfile(lpath):
            sftp.put(lpath, f"{remote_build_dir}/{fname}")

    # Also sync to ~/Documents/Projects/iRipper/Mobile Engineering Studio/adb-scrcpy-studio on DOOMSDAY
    remote_proj_dir = "/home/dsilva/Documents/Projects/iRipper/Mobile Engineering Studio/adb-scrcpy-studio"
    client.exec_command(f"mkdir -p '{remote_proj_dir}/assets' '{remote_proj_dir}/adb_keys' '{remote_proj_dir}/linux-packages/aur' '~/.android'")[1].read()
    sftp.put(os.path.join(STUDIO_DIR, "adb_scrcpy_studio.py"), f"{remote_proj_dir}/adb_scrcpy_studio.py")
    sftp.put(os.path.join(STUDIO_DIR, "assets", "android_scrcpy_dex.png"), f"{remote_proj_dir}/assets/android_scrcpy_dex.png")
    sftp.put(os.path.join(STUDIO_DIR, "assets", "android_scrcpy_dex.ico"), f"{remote_proj_dir}/assets/android_scrcpy_dex.ico")
    for kname in ["iripper_adbkey", "iripper_adbkey.pub", "doomsday_adbkey", "doomsday_adbkey.pub"]:
        kpath = os.path.join(STUDIO_DIR, "adb_keys", kname)
        if os.path.isfile(kpath):
            sftp.put(kpath, f"{remote_proj_dir}/adb_keys/{kname}")
            sftp.put(kpath, f"/home/dsilva/.android/{kname}")
    for fname in ["PKGBUILD", ".SRCINFO", "android-scrcpy-dex-studio-3.1.0.tar.gz", "install_aur.sh"]:
        lpath = os.path.join(local_aur_dir, fname)
        if os.path.isfile(lpath):
            sftp.put(lpath, f"{remote_proj_dir}/linux-packages/aur/{fname}")
    sftp.close()

    # 3. Install dependencies (scrcpy, android-tools, tk, xdotool, python-psutil, python-pillow) & build/install AUR package
    client.close()
    install_cmd = (
        f"chmod 600 ~/.android/*adbkey 2>/dev/null || true && "
        f"echo '{pwd}' | sudo -S pacman -S --needed --noconfirm android-tools scrcpy tk xdotool python-psutil python-pillow python-pip && "
        f"cd {remote_build_dir} && makepkg -f && "
        f"echo '{pwd}' | sudo -S pacman -U --noconfirm {remote_build_dir}/android-scrcpy-dex-studio-3.1.0-1-any.pkg.tar* && "
        f"mkdir -p ~/.local/share/android-scrcpy-dex-studio && "
        f"if [ ! -x ~/.local/share/android-scrcpy-dex-studio/venv/bin/python ]; then "
        f"  python3 -m venv ~/.local/share/android-scrcpy-dex-studio/venv && "
        f"  ~/.local/share/android-scrcpy-dex-studio/venv/bin/pip install --quiet customtkinter psutil pillow; "
        f"fi && "
        f"cp /usr/share/applications/android-scrcpy-dex-studio.desktop ~/Desktop/ 2>/dev/null || true && "
        f"chmod +x ~/Desktop/android-scrcpy-dex-studio.desktop 2>/dev/null || true && "
        f"pacman -Qi android-scrcpy-dex-studio"
    )
    res = subprocess.run(
        ["ssh", "-i", key_path, "-o", "StrictHostKeyChecking=no", f"{DOOMSDAY_USER}@{DOOMSDAY_IP}", "bash", "-s"],
        input=install_cmd,
        text=True,
        capture_output=True,
    )
    print(res.stdout)
    if res.returncode != 0:
        print("[STDERR]", res.stderr)
    else:
        print("[+] Successfully installed android-scrcpy-dex-studio v3.1.0 on ASUS Laptop (DOOMSDAY)!")


if __name__ == "__main__":
    deploy_windows()
    deploy_asus_doomsday()
