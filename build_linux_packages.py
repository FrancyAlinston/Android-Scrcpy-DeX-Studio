#!/usr/bin/env python3
"""
Pure-Python Debian (.deb) and Arch Linux / CachyOS AUR (PKGBUILD + .SRCINFO + build_aur.sh)
Package Generator for J.A.R.V.I.S. Android & Scrcpy DeX Studio v2.0.
Builds a specification-compliant Debian binary package (.deb) using standard ar + tar.gz archives
with LF line endings and proper POSIX file permissions (0755 for executables, 0644 for assets).
"""

import os
import io
import time
import tarfile
import hashlib


APP_NAME = "android-scrcpy-dex-studio"
APP_VERSION = "3.0.0"
MAINTAINER = "Francy Alinston (Alen) <alen@jarvis.local>"
DESCRIPTION = (
    "J.A.R.V.I.S. Android & Scrcpy DeX Studio - ADB Control, Live Task Manager, Scrcpy 4.0 Mirror & PC DeX Mode\n"
    " Cross-platform workstation for Android device management over USB and Wi-Fi ADB.\n"
    " Includes live CPU/RAM/Thermal Task Manager with radial gauges, APK installer/uninstaller,\n"
    " Android Emulator hardware navigation bar (Back, Home, Recents), Scrcpy audio/video controller,\n"
    " and PC DeX / Desktop virtual display mode."
)

DESKTOP_ENTRY = """[Desktop Entry]
Version=1.0
Type=Application
Name=J.A.R.V.I.S. Android & Scrcpy DeX Studio
GenericName=Android ADB, Task Manager, Scrcpy & DeX Workstation
Comment=Manage ADB Devices, Live System Monitor, APK Manager, Scrcpy Mirror & PC DeX Mode
Exec=/usr/bin/android-scrcpy-dex-studio
Icon=android-scrcpy-dex-studio
Terminal=false
Categories=Development;Utility;System;
Keywords=adb;android;scrcpy;dex;mirror;taskmanager;
StartupNotify=true
"""

LAUNCHER_WRAPPER = """#!/usr/bin/env bash
set -e
APP_DIR="/opt/android-scrcpy-dex-studio"
VENV_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/android-scrcpy-dex-studio/venv"

if python3 -c "import customtkinter, psutil, PIL" >/dev/null 2>&1; then
    exec python3 "$APP_DIR/adb_scrcpy_studio.py" "$@"
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
    mkdir -p "$(dirname "$VENV_DIR")"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip customtkinter psutil pillow >/dev/null 2>&1
fi

exec "$VENV_DIR/bin/python" "$APP_DIR/adb_scrcpy_studio.py" "$@"
"""

POSTINST_SCRIPT = """#!/bin/sh
set -e
chmod 0755 /usr/bin/android-scrcpy-dex-studio || true
chmod 0755 /opt/android-scrcpy-dex-studio/adb_scrcpy_studio.py || true
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
exit 0
"""


def _add_tar_bytes(tar: tarfile.TarFile, arcname: str, data: bytes, mode: int = 0o644) -> None:
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    info.mtime = int(time.time())
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    tar.addfile(info, io.BytesIO(data))


def _add_tar_dir(tar: tarfile.TarFile, arcname: str) -> None:
    info = tarfile.TarInfo(name=arcname)
    info.type = tarfile.DIRTYPE
    info.mtime = int(time.time())
    info.mode = 0o755
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    tar.addfile(info)


def build_deb_package(base_dir: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    deb_filename = f"{APP_NAME}_{APP_VERSION}_all.deb"
    deb_path = os.path.join(out_dir, deb_filename)

    py_src = os.path.join(base_dir, "adb_scrcpy_studio.py")
    png_src = os.path.join(base_dir, "assets", "android_scrcpy_dex.png")
    ico_src = os.path.join(base_dir, "assets", "android_scrcpy_dex.ico")

    with open(py_src, "rb") as f:
        py_bytes = f.read().replace(b"\r\n", b"\n")
    with open(png_src, "rb") as f:
        png_bytes = f.read()
    with open(ico_src, "rb") as f:
        ico_bytes = f.read()

    # 1. Build data.tar.gz
    data_buf = io.BytesIO()
    with tarfile.open(fileobj=data_buf, mode="w:gz", format=tarfile.GNU_FORMAT) as dtar:
        for d in [
            "./opt",
            "./opt/android-scrcpy-dex-studio",
            "./opt/android-scrcpy-dex-studio/assets",
            "./usr",
            "./usr/bin",
            "./usr/share",
            "./usr/share/applications",
            "./usr/share/pixmaps",
        ]:
            _add_tar_dir(dtar, d)

        _add_tar_bytes(dtar, "./opt/android-scrcpy-dex-studio/adb_scrcpy_studio.py", py_bytes, mode=0o755)
        _add_tar_bytes(dtar, "./opt/android-scrcpy-dex-studio/assets/android_scrcpy_dex.png", png_bytes, mode=0o644)
        _add_tar_bytes(dtar, "./opt/android-scrcpy-dex-studio/assets/android_scrcpy_dex.ico", ico_bytes, mode=0o644)
        _add_tar_bytes(dtar, "./usr/bin/android-scrcpy-dex-studio", LAUNCHER_WRAPPER.encode("utf-8"), mode=0o755)
        _add_tar_bytes(
            dtar,
            "./usr/share/applications/android-scrcpy-dex-studio.desktop",
            DESKTOP_ENTRY.encode("utf-8"),
            mode=0o644,
        )
        _add_tar_bytes(dtar, "./usr/share/pixmaps/android-scrcpy-dex-studio.png", png_bytes, mode=0o644)

    data_tar_gz = data_buf.getvalue()

    # 2. Build control.tar.gz
    installed_kb = max(128, (len(py_bytes) + len(png_bytes) + len(ico_bytes)) // 1024)
    control_content = (
        f"Package: {APP_NAME}\n"
        f"Version: {APP_VERSION}\n"
        f"Section: utils\n"
        f"Priority: optional\n"
        f"Architecture: all\n"
        f"Installed-Size: {installed_kb}\n"
        f"Depends: python3, python3-tk, python3-venv, python3-pip, adb | android-tools-adb, scrcpy\n"
        f"Maintainer: {MAINTAINER}\n"
        f"Description: {DESCRIPTION}\n"
    ).encode("utf-8")

    md5sums_content = (
        f"{hashlib.md5(py_bytes).hexdigest()}  opt/android-scrcpy-dex-studio/adb_scrcpy_studio.py\n"
        f"{hashlib.md5(png_bytes).hexdigest()}  opt/android-scrcpy-dex-studio/assets/android_scrcpy_dex.png\n"
        f"{hashlib.md5(ico_bytes).hexdigest()}  opt/android-scrcpy-dex-studio/assets/android_scrcpy_dex.ico\n"
        f"{hashlib.md5(LAUNCHER_WRAPPER.encode('utf-8')).hexdigest()}  usr/bin/android-scrcpy-dex-studio\n"
        f"{hashlib.md5(DESKTOP_ENTRY.encode('utf-8')).hexdigest()}  usr/share/applications/android-scrcpy-dex-studio.desktop\n"
        f"{hashlib.md5(png_bytes).hexdigest()}  usr/share/pixmaps/android-scrcpy-dex-studio.png\n"
    ).encode("utf-8")

    ctrl_buf = io.BytesIO()
    with tarfile.open(fileobj=ctrl_buf, mode="w:gz", format=tarfile.GNU_FORMAT) as ctar:
        _add_tar_dir(ctar, ".")
        _add_tar_bytes(ctar, "./control", control_content, mode=0o644)
        _add_tar_bytes(ctar, "./md5sums", md5sums_content, mode=0o644)
        _add_tar_bytes(ctar, "./postinst", POSTINST_SCRIPT.encode("utf-8"), mode=0o755)

    control_tar_gz = ctrl_buf.getvalue()

    # 3. Assemble standard Unix `ar` archive (.deb)
    def ar_member(name: str, content: bytes) -> bytes:
        mtime = str(int(time.time())).ljust(12)
        uid = "0".ljust(6)
        gid = "0".ljust(6)
        mode = "100644".ljust(8)
        size = str(len(content)).ljust(10)
        header = f"{name.ljust(16)}{mtime}{uid}{gid}{mode}{size}`\n".encode("ascii")
        pad = b"\n" if (len(content) % 2 == 1) else b""
        return header + content + pad

    with open(deb_path, "wb") as out_f:
        out_f.write(b"!<arch>\n")
        out_f.write(ar_member("debian-binary", b"2.0\n"))
        out_f.write(ar_member("control.tar.gz", control_tar_gz))
        out_f.write(ar_member("data.tar.gz", data_tar_gz))

    print(f"[+] Built Debian (.deb) Package: {deb_path} ({os.path.getsize(deb_path)} bytes)")
    return deb_path


def build_aur_package(base_dir: str, aur_dir: str) -> str:
    os.makedirs(aur_dir, exist_ok=True)

    py_src = os.path.join(base_dir, "adb_scrcpy_studio.py")
    png_src = os.path.join(base_dir, "assets", "android_scrcpy_dex.png")
    ico_src = os.path.join(base_dir, "assets", "android_scrcpy_dex.ico")

    # Create source tarball for makepkg
    tar_name = f"{APP_NAME}-{APP_VERSION}.tar.gz"
    tar_path = os.path.join(aur_dir, tar_name)

    with open(py_src, "rb") as f:
        py_bytes = f.read().replace(b"\r\n", b"\n")
    with open(png_src, "rb") as f:
        png_bytes = f.read()
    with open(ico_src, "rb") as f:
        ico_bytes = f.read()

    with tarfile.open(tar_path, mode="w:gz", format=tarfile.GNU_FORMAT) as star:
        root_d = f"{APP_NAME}-{APP_VERSION}"
        _add_tar_dir(star, root_d)
        _add_tar_dir(star, f"{root_d}/assets")
        _add_tar_bytes(star, f"{root_d}/adb_scrcpy_studio.py", py_bytes, mode=0o755)
        _add_tar_bytes(star, f"{root_d}/assets/android_scrcpy_dex.png", png_bytes, mode=0o644)
        _add_tar_bytes(star, f"{root_d}/assets/android_scrcpy_dex.ico", ico_bytes, mode=0o644)
        _add_tar_bytes(star, f"{root_d}/android-scrcpy-dex-studio.sh", LAUNCHER_WRAPPER.encode("utf-8"), mode=0o755)
        _add_tar_bytes(
            star,
            f"{root_d}/android-scrcpy-dex-studio.desktop",
            DESKTOP_ENTRY.encode("utf-8"),
            mode=0o644,
        )

    with open(tar_path, "rb") as f:
        sha256_hash = hashlib.sha256(f.read()).hexdigest()

    pkgbuild_content = f"""# Maintainer: Francy Alinston (Alen) <alen@jarvis.local>
pkgname={APP_NAME}
pkgver={APP_VERSION}
pkgrel=1
pkgdesc="J.A.R.V.I.S. Android & Scrcpy DeX Studio - ADB Control, Live Task Manager, Scrcpy 4.0 Mirror & PC DeX Workstation"
arch=('any')
url="https://github.com/Genymobile/scrcpy"
license=('MIT')
depends=('python' 'tk' 'python-psutil' 'python-pillow' 'python-pip' 'android-tools' 'scrcpy')
optdepends=('python-customtkinter: system-wide CustomTkinter library')
source=("{tar_name}")
sha256sums=('{sha256_hash}')

package() {{
    cd "$srcdir/$pkgname-$pkgver"
    install -dm755 "$pkgdir/opt/$pkgname/assets"
    install -Dm755 "adb_scrcpy_studio.py" "$pkgdir/opt/$pkgname/adb_scrcpy_studio.py"
    install -Dm644 "assets/android_scrcpy_dex.png" "$pkgdir/opt/$pkgname/assets/android_scrcpy_dex.png"
    install -Dm644 "assets/android_scrcpy_dex.ico" "$pkgdir/opt/$pkgname/assets/android_scrcpy_dex.ico"
    install -Dm755 "android-scrcpy-dex-studio.sh" "$pkgdir/usr/bin/$pkgname"
    install -Dm644 "android-scrcpy-dex-studio.desktop" "$pkgdir/usr/share/applications/$pkgname.desktop"
    install -Dm644 "assets/android_scrcpy_dex.png" "$pkgdir/usr/share/pixmaps/$pkgname.png"
}}
"""

    srcinfo_content = f"""pkgbase = {APP_NAME}
\tpkgdesc = J.A.R.V.I.S. Android & Scrcpy DeX Studio - ADB Control, Live Task Manager, Scrcpy 4.0 Mirror & PC DeX Workstation
\tpkgver = {APP_VERSION}
\tpkgrel = 1
\turl = https://github.com/Genymobile/scrcpy
\tarch = any
\tlicense = MIT
\tdepends = python
\tdepends = tk
\tdepends = python-psutil
\tdepends = python-pillow
\tdepends = python-pip
\tdepends = android-tools
\tdepends = scrcpy
\toptdepends = python-customtkinter: system-wide CustomTkinter library
\tsource = {tar_name}
\tsha256sums = {sha256_hash}

pkgname = {APP_NAME}
"""

    build_aur_sh = f"""#!/usr/bin/env bash
# 1-Click CachyOS / Arch Linux AUR Package Builder & Installer
set -e
cd "$(dirname "${{BASH_SOURCE[0]}}")"
echo "[*] Building and installing {APP_NAME} v{APP_VERSION} via makepkg..."
makepkg -si --noconfirm
echo "[+] {APP_NAME} installed! Launch from App Menu or run: {APP_NAME}"
"""

    with open(os.path.join(aur_dir, "PKGBUILD"), "wb") as f:
        f.write(pkgbuild_content.encode("utf-8"))
    with open(os.path.join(aur_dir, ".SRCINFO"), "wb") as f:
        f.write(srcinfo_content.encode("utf-8"))
    with open(os.path.join(aur_dir, "install_aur.sh"), "wb") as f:
        f.write(build_aur_sh.encode("utf-8"))

    print(f"[+] Built Arch/CachyOS AUR Suite in: {aur_dir} (PKGBUILD, .SRCINFO, {tar_name}, install_aur.sh)")
    return aur_dir


if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    deb_out = os.path.join(root, "linux-packages", "debian")
    aur_out = os.path.join(root, "linux-packages", "aur")
    build_deb_package(root, deb_out)
    build_aur_package(root, aur_out)
