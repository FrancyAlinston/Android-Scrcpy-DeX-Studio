#!/usr/bin/env python3
"""
Automated Dual-Platform Publisher for J.A.R.V.I.S. Android & Scrcpy DeX Studio v3.0.0:
1. Creates & pushes repository to Private/Self-Hosted Forgejo (http://192.168.8.100:3000 / https://forgejo.449100.xyz)
2. Creates & pushes repository to Public GitHub (https://github.com/FrancyAlinston/Android-Scrcpy-DeX-Studio)
3. Publishes v3.0.0 Releases on both Forgejo and GitHub and uploads all 4 release packages:
   - AndroidScrcpyDeXStudio-Setup-v2.0.exe (Windows GUI Setup Wizard)
   - AndroidScrcpyDeXStudio.exe (Windows Portable --onefile Self-Contained EXE)
   - android-scrcpy-dex-studio_3.0.0_all.deb (Debian / Ubuntu Linux Package)
   - android-scrcpy-dex-studio-3.0.0.tar.gz (Arch / CachyOS Linux AUR Package Tarball)
"""

import os
import sys
import subprocess
import urllib.parse
import win32cred
import requests

STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_NAME = "Android-Scrcpy-DeX-Studio"
TAG_NAME = "v3.0.0"
RELEASE_TITLE = "J.A.R.V.I.S. Android & Scrcpy DeX Studio v3.0.0 — Flagship Obsidian Glass Edition"
RELEASE_NOTES = """## ⚡ J.A.R.V.I.S. Android & Scrcpy DeX Studio v3.0.0 (Flagship Obsidian Glass Edition)

Cross-platform (**Windows 11** & **CachyOS / Arch / Debian / Ubuntu Linux**) workstation for Android ADB device control, Live System Task Manager, Multi-APK Batch Installation, Scrcpy 4.0 Mirroring with a **Magnetic Android Emulator Side-Toolbar**, and **PC as Samsung DeX / Android Desktop Workstation Mode**.

### ✨ Key Features in v3.0.0
1. **2-Pane Obsidian Glass Navigation Rail Architecture (`#06080d` Void / `#0e131d` Glass Cards)**:
   - Left Sidebar Navigation Rail with high-DPI logo badge, 5 module pills, a live **Device Mini-Telemetry Card** (pulsing status LED halo, device model, Android version, Battery %, CPU %, RAM % visible from every view), and a dedicated **Wireless ADB Bridge** card.
2. **Magnetic Android Emulator Side-Toolbar (`ScrcpyEmulatorSideBar`)**:
   - Docks directly alongside the mirrored Scrcpy display window (tracks position, resize, and minimize at 30fps via Win32 `EnumWindows` / `GetWindowRect` and Linux `xdotool`).
   - Dedicated vector buttons for **Power**, **Volume +**, **Volume -**, **Mute**, **Rotate Screen**, **Instant PNG Screenshot**, **Notifications Shade**, **`BACK` (`4`)**, **`HOME` (`3`)**, and **`RECENT` (`187`)**.
3. **PC as Samsung DeX / Android Desktop Mode Workstation**:
   - Spawns an independent virtual external display via Scrcpy 4.0 `--new-display=<res>/<dpi>` (`1080p`, `1440p 120Hz`, `4K UHD`, `Ultrawide 21:9`) and enables Android global freeform multi-window & desktop display flags.
4. **Multi-APK Batch Installer Modal (`BatchApkInstallModal`)**:
   - Select multiple `.apk` files at once (`Ctrl+Click` / `Shift+Click`) with a 60fps animated shimmer progress bar, live step counter, `✅ Success | ❌ Failed` badge, and live console output log.
5. **Live System Task Manager (4× Supersampled Pillow Radial Gauges & Glowing Sparklines)**:
   - Real-time `top -b -n 1`, `/proc/meminfo`, and battery/thermal polling every 2.0s with 4× supersampled Lanczos radial rings, grid-backed sparklines, process filter, 1-click Force-Stop, and RAM cache trimming.

### 📦 Release Assets
- **`AndroidScrcpyDeXStudio-Setup-v2.0.exe`**: Animated Windows 11 GUI Setup Installer (installs to `%LOCALAPPDATA%\\Programs\\Android Scrcpy DeX Studio`, enables `Pin to Start`, creates Desktop & Start Menu shortcuts).
- **`AndroidScrcpyDeXStudio.exe`**: 100% Self-Contained Windows Portable Single-File Executable (`--onefile` with embedded Python 3.14, `adb.exe`, `scrcpy.exe v4.0`, `scrcpy-server`, and `SDL3.dll`).
- **`android-scrcpy-dex-studio_3.0.0_all.deb`**: Debian / Ubuntu Linux binary package (`sudo apt install ./android-scrcpy-dex-studio_3.0.0_all.deb`).
- **`android-scrcpy-dex-studio-3.0.0.tar.gz`**: Arch / CachyOS Linux AUR source package (use with `PKGBUILD` and `makepkg -si`).
"""


def get_cred(target: str) -> tuple[str, str]:
    c = win32cred.CredRead(target, win32cred.CRED_TYPE_GENERIC)
    user = c["UserName"]
    pwd = c["CredentialBlob"].decode("utf-16le").rstrip("\x00").strip()
    return user, pwd


def clean_markdown_fences(path: str) -> None:
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read().strip()
    if txt.startswith("```markdown"):
        txt = txt[len("```markdown") :].strip()
    elif txt.startswith("```"):
        txt = txt[3:].strip()
    if txt.endswith("```"):
        txt = txt[:-3].strip()
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt + "\n")


def init_and_commit_git() -> None:
    clean_markdown_fences(os.path.join(STUDIO_DIR, "README.md"))
    subprocess.run(["git", "init", "-b", "main"], cwd=STUDIO_DIR, check=True)
    subprocess.run(["git", "config", "user.name", "Francy Alinston"], cwd=STUDIO_DIR, check=True)
    subprocess.run(["git", "config", "user.email", "francyalinston@gmail.com"], cwd=STUDIO_DIR, check=True)
    subprocess.run(["git", "add", "-A"], cwd=STUDIO_DIR, check=True)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=STUDIO_DIR, capture_output=True, text=True).stdout
    if status.strip():
        subprocess.run(
            ["git", "commit", "-m", "feat: release J.A.R.V.I.S. Android & Scrcpy DeX Studio v3.0.0 (Flagship Obsidian Glass Edition)"],
            cwd=STUDIO_DIR,
            check=True,
        )
    subprocess.run(["git", "tag", "-f", TAG_NAME], cwd=STUDIO_DIR, check=True)


def publish_forgejo(assets: list[str]) -> str:
    fg_user, fg_pass = get_cred("git:http://192.168.8.100:3000")
    base_api = "http://192.168.8.100:3000/api/v1"

    # 1. Create repo if not exists
    r = requests.get(f"{base_api}/repos/{fg_user}/{REPO_NAME}", auth=(fg_user, fg_pass), timeout=10)
    if r.status_code == 404:
        cr = requests.post(
            f"{base_api}/user/repos",
            auth=(fg_user, fg_pass),
            json={
                "name": REPO_NAME,
                "description": "J.A.R.V.I.S. Android & Scrcpy DeX Studio v3.0.0 — Self-Contained ADB Workstation, Live Task Manager, Multi-APK Installer, Scrcpy 4.0 Mirror + Magnetic Emulator Side-Toolbar & PC DeX Mode",
                "private": False,
                "auto_init": False,
            },
            timeout=10,
        )
        cr.raise_for_status()
        print(f"[+] Created Forgejo repository: {fg_user}/{REPO_NAME}")
    else:
        print(f"[*] Forgejo repository {fg_user}/{REPO_NAME} already exists.")

    # 2. Push code and tag
    enc_user = urllib.parse.quote(fg_user, safe="")
    enc_pass = urllib.parse.quote(fg_pass, safe="")
    remote_url = f"http://{enc_user}:{enc_pass}@192.168.8.100:3000/{fg_user}/{REPO_NAME}.git"
    subprocess.run(["git", "remote", "remove", "forgejo"], cwd=STUDIO_DIR, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "forgejo", f"https://forgejo.449100.xyz/{fg_user}/{REPO_NAME}.git"],
        cwd=STUDIO_DIR,
        check=True,
    )
    subprocess.run(["git", "push", "-u", "--force", remote_url, "main"], cwd=STUDIO_DIR, check=True)
    subprocess.run(["git", "push", "--force", remote_url, f"refs/tags/{TAG_NAME}"], cwd=STUDIO_DIR, check=True)
    print("[+] Pushed main branch and tag v3.0.0 to Forgejo.")

    # 3. Create or fetch Release on Forgejo
    rel_r = requests.get(
        f"{base_api}/repos/{fg_user}/{REPO_NAME}/releases/tags/{TAG_NAME}", auth=(fg_user, fg_pass), timeout=10
    )
    if rel_r.status_code == 200:
        rel_id = rel_r.json()["id"]
    else:
        cr_rel = requests.post(
            f"{base_api}/repos/{fg_user}/{REPO_NAME}/releases",
            auth=(fg_user, fg_pass),
            json={
                "tag_name": TAG_NAME,
                "target_commitish": "main",
                "name": RELEASE_TITLE,
                "body": RELEASE_NOTES,
                "draft": False,
                "prerelease": False,
            },
            timeout=15,
        )
        cr_rel.raise_for_status()
        rel_id = cr_rel.json()["id"]

    # Clear existing attachments on release if re-running
    existing_assets = requests.get(
        f"{base_api}/repos/{fg_user}/{REPO_NAME}/releases/{rel_id}/assets", auth=(fg_user, fg_pass), timeout=10
    ).json()
    for ea in existing_assets:
        requests.delete(
            f"{base_api}/repos/{fg_user}/{REPO_NAME}/releases/{rel_id}/assets/{ea['id']}",
            auth=(fg_user, fg_pass),
            timeout=10,
        )

    for asset_path in assets:
        if not os.path.isfile(asset_path):
            continue
        fname = os.path.basename(asset_path)
        print(f"[*] Uploading {fname} to Forgejo release...")
        with open(asset_path, "rb") as f:
            up = requests.post(
                f"{base_api}/repos/{fg_user}/{REPO_NAME}/releases/{rel_id}/assets",
                auth=(fg_user, fg_pass),
                params={"name": fname},
                files={"attachment": (fname, f, "application/octet-stream")},
                timeout=300,
            )
            up.raise_for_status()

    print(f"[+] Forgejo Release v3.0.0 published: https://forgejo.449100.xyz/{fg_user}/{REPO_NAME}/releases/tag/{TAG_NAME}")
    return f"https://forgejo.449100.xyz/{fg_user}/{REPO_NAME}"


def publish_github(assets: list[str]) -> str:
    gh_user, gh_token = get_cred("git:https://github.com")
    headers = {
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github+json",
    }

    # 1. Create repo if not exists
    r = requests.get(f"https://api.github.com/repos/{gh_user}/{REPO_NAME}", headers=headers, timeout=10)
    if r.status_code == 404:
        cr = requests.post(
            "https://api.github.com/user/repos",
            headers=headers,
            json={
                "name": REPO_NAME,
                "description": "J.A.R.V.I.S. Android & Scrcpy DeX Studio v3.0.0 — Self-Contained ADB Workstation, Live Task Manager, Multi-APK Installer, Scrcpy 4.0 Mirror + Magnetic Emulator Side-Toolbar & PC DeX Mode",
                "private": False,
                "auto_init": False,
            },
            timeout=15,
        )
        cr.raise_for_status()
        print(f"[+] Created GitHub repository: {gh_user}/{REPO_NAME}")
    else:
        print(f"[*] GitHub repository {gh_user}/{REPO_NAME} already exists.")

    # 2. Push code and tag
    enc_token = urllib.parse.quote(gh_token, safe="")
    remote_url = f"https://{gh_user}:{enc_token}@github.com/{gh_user}/{REPO_NAME}.git"
    subprocess.run(["git", "remote", "remove", "origin"], cwd=STUDIO_DIR, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", f"https://github.com/{gh_user}/{REPO_NAME}.git"],
        cwd=STUDIO_DIR,
        check=True,
    )
    subprocess.run(["git", "push", "-u", "--force", remote_url, "main"], cwd=STUDIO_DIR, check=True)
    subprocess.run(["git", "push", "--force", remote_url, f"refs/tags/{TAG_NAME}"], cwd=STUDIO_DIR, check=True)
    print("[+] Pushed main branch and tag v3.0.0 to GitHub.")

    # 3. Create or fetch Release on GitHub
    rel_r = requests.get(
        f"https://api.github.com/repos/{gh_user}/{REPO_NAME}/releases/tags/{TAG_NAME}", headers=headers, timeout=10
    )
    if rel_r.status_code == 200:
        rel_data = rel_r.json()
    else:
        cr_rel = requests.post(
            f"https://api.github.com/repos/{gh_user}/{REPO_NAME}/releases",
            headers=headers,
            json={
                "tag_name": TAG_NAME,
                "target_commitish": "main",
                "name": RELEASE_TITLE,
                "body": RELEASE_NOTES,
                "draft": False,
                "prerelease": False,
            },
            timeout=15,
        )
        cr_rel.raise_for_status()
        rel_data = cr_rel.json()

    rel_id = rel_data["id"]
    for ea in rel_data.get("assets", []):
        requests.delete(
            f"https://api.github.com/repos/{gh_user}/{REPO_NAME}/releases/assets/{ea['id']}",
            headers=headers,
            timeout=10,
        )

    for asset_path in assets:
        if not os.path.isfile(asset_path):
            continue
        fname = os.path.basename(asset_path)
        print(f"[*] Uploading {fname} to GitHub release...")
        up_headers = headers.copy()
        up_headers["Content-Type"] = "application/octet-stream"
        with open(asset_path, "rb") as f:
            up = requests.post(
                f"https://uploads.github.com/repos/{gh_user}/{REPO_NAME}/releases/{rel_id}/assets",
                headers=up_headers,
                params={"name": fname},
                data=f,
                timeout=600,
            )
            up.raise_for_status()

    print(f"[+] GitHub Release v3.0.0 published: https://github.com/{gh_user}/{REPO_NAME}/releases/tag/{TAG_NAME}")
    return f"https://github.com/{gh_user}/{REPO_NAME}"


if __name__ == "__main__":
    init_and_commit_git()
    release_assets = [
        os.path.join(STUDIO_DIR, "dist", "AndroidScrcpyDeXStudio-Setup-v2.0.exe"),
        os.path.join(STUDIO_DIR, "dist", "AndroidScrcpyDeXStudio.exe"),
        os.path.join(STUDIO_DIR, "linux-packages", "debian", "android-scrcpy-dex-studio_3.0.0_all.deb"),
        os.path.join(STUDIO_DIR, "linux-packages", "aur", "android-scrcpy-dex-studio-3.0.0.tar.gz"),
        os.path.join(STUDIO_DIR, "linux-packages", "aur", "PKGBUILD"),
    ]
    fg_url = publish_forgejo(release_assets)
    gh_url = publish_github(release_assets)
    print("\n============================================================")
    print(f"  FORGEJO: {fg_url}")
    print(f"  GITHUB : {gh_url}")
    print("============================================================")
