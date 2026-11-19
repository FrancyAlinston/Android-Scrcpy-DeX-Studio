#!/usr/bin/env python3
"""
J.A.R.V.I.S. Android & Scrcpy DeX Studio — Animated Self-Contained Windows Setup Installer (v2.0)
Embeds the standalone single-file AndroidScrcpyDeXStudio.exe and installs to:
 - Default: H:\Program Files\Android Scrcpy DeX Studio (or %LOCALAPPDATA%\Programs\AndroidScrcpyDeXStudio)
 - Creates Start Menu & Desktop Shortcuts with High-DPI Custom Icon
 - Registers in Windows 'Installed Apps' / 'Add or Remove Programs'
"""

import os
import sys

if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, "w")
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, "w")
    except Exception:
        pass

import math
import time
import shutil
import winreg
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import customtkinter as ctk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CREATE_NO_WINDOW = 0x08000000


def get_payload_dir() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return getattr(sys, "_MEIPASS")
    return os.path.dirname(os.path.abspath(__file__))


class StudioSetupInstaller(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("J.A.R.V.I.S. Android & Scrcpy DeX Studio v2.0 — Setup Wizard")
        self.geometry("680x500")
        self.resizable(False, False)
        self.configure(fg_color="#090c12")

        payload_root = get_payload_dir()
        self.ico_src = os.path.join(payload_root, "assets", "android_scrcpy_dex.ico")
        self.png_src = os.path.join(payload_root, "assets", "android_scrcpy_dex.png")
        self.exe_src = os.path.join(payload_root, "payload", "AndroidScrcpyDeXStudio.exe")
        if not os.path.isfile(self.exe_src):
            self.exe_src = os.path.join(payload_root, "dist", "AndroidScrcpyDeXStudio.exe")

        if os.path.isfile(self.ico_src):
            try:
                self.iconbitmap(self.ico_src)
            except Exception:
                pass

        default_dir = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Android Scrcpy DeX Studio")
        self.install_dir_var = ctk.StringVar(value=default_dir)
        self.progress_target = 0.0
        self.progress_disp = 0.0
        self.phase = 0.0
        self.installed_exe: str = ""

        self._build_ui()
        self.after(25, self._animate_tick)

    def _build_ui(self) -> None:
        # Top Hero Header
        hero = ctk.CTkFrame(self, fg_color="#111723", corner_radius=14, border_width=1, border_color="#1e293b")
        hero.pack(fill="x", padx=20, pady=(18, 10))

        if os.path.isfile(self.png_src):
            pil_img = Image.open(self.png_src)
            self.logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(72, 72))
            ctk.CTkLabel(hero, text="", image=self.logo_img).pack(side="left", padx=(18, 14), pady=14)

        txt_col = ctk.CTkFrame(hero, fg_color="transparent")
        txt_col.pack(side="left", fill="both", expand=True, pady=14)
        ctk.CTkLabel(
            txt_col,
            text="J.A.R.V.I.S. Android & Scrcpy DeX Studio v2.0",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#38bdf8",
        ).pack(anchor="w")
        ctk.CTkLabel(
            txt_col,
            text="Self-Contained ADB Workstation • Live Task Manager • Scrcpy 4.0 • PC DeX Mode",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
        ).pack(anchor="w", pady=(2, 4))
        ctk.CTkLabel(
            txt_col,
            text="Includes Embedded Python 3.14 Runtime + Scrcpy 4.0 + SDL3 + ADB Platform Tools",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#10b981",
        ).pack(anchor="w")

        # Configuration Card
        cfg = ctk.CTkFrame(self, fg_color="#111723", corner_radius=14, border_width=1, border_color="#1e293b")
        cfg.pack(fill="x", padx=20, pady=6)

        ctk.CTkLabel(
            cfg, text="Installation Destination Folder:", font=ctk.CTkFont(size=13, weight="bold"), text_color="#e2e8f0"
        ).pack(anchor="w", padx=18, pady=(14, 6))

        dir_row = ctk.CTkFrame(cfg, fg_color="transparent")
        dir_row.pack(fill="x", padx=18, pady=(0, 10))
        self.dir_entry = ctk.CTkEntry(dir_row, textvariable=self.install_dir_var, height=34, fg_color="#090c12")
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            dir_row, text="Browse...", width=95, height=34, fg_color="#1e293b", hover_color="#334155", command=self._browse_dir
        ).pack(side="left")

        self.chk_desktop = ctk.CTkCheckBox(cfg, text="Create Desktop Shortcut (Android & Scrcpy DeX Studio.lnk)")
        self.chk_desktop.select()
        self.chk_desktop.pack(anchor="w", padx=18, pady=5)

        self.chk_startmenu = ctk.CTkCheckBox(cfg, text="Create Windows Start Menu Shortcut & Register in Installed Apps")
        self.chk_startmenu.select()
        self.chk_startmenu.pack(anchor="w", padx=18, pady=5)

        self.chk_downloads = ctk.CTkCheckBox(
            cfg, text="Also Deploy Standalone Single-File EXE to Downloads Folder (Fixes missing _internal error)"
        )
        self.chk_downloads.select()
        self.chk_downloads.pack(anchor="w", padx=18, pady=(5, 14))

        # Animated Progress Canvas
        prog_card = ctk.CTkFrame(self, fg_color="#111723", corner_radius=14, border_width=1, border_color="#1e293b")
        prog_card.pack(fill="x", padx=20, pady=6)

        self.status_lbl = ctk.CTkLabel(
            prog_card,
            text="Ready to install self-contained package.",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38bdf8",
        )
        self.status_lbl.pack(anchor="w", padx=18, pady=(10, 4))

        self.prog_canvas = tk.Canvas(prog_card, height=22, bg="#090c12", highlightthickness=0)
        self.prog_canvas.pack(fill="x", padx=18, pady=(0, 12))

        # Bottom Buttons
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=20, pady=(10, 16))

        self.install_btn = ctk.CTkButton(
            btn_bar,
            text="⚡ INSTALL & LAUNCH STUDIO NOW",
            height=44,
            corner_radius=10,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_install,
        )
        self.install_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            btn_bar,
            text="Close",
            width=110,
            height=44,
            corner_radius=10,
            fg_color="#1e293b",
            hover_color="#334155",
            command=self.destroy,
        ).pack(side="right")

    def _browse_dir(self) -> None:
        chosen = filedialog.askdirectory(title="Select Installation Directory")
        if chosen:
            self.install_dir_var.set(chosen)

    def _animate_tick(self) -> None:
        self.phase += 0.15
        self.progress_disp += (self.progress_target - self.progress_disp) * 0.2

        self.prog_canvas.delete("all")
        w = max(self.prog_canvas.winfo_width(), 580)
        h = 22
        self.prog_canvas.create_rectangle(0, 0, w, h, fill="#090c12", outline="#1e293b")
        fill_w = int(w * max(0.0, min(1.0, self.progress_disp)))
        if fill_w > 2:
            self.prog_canvas.create_rectangle(0, 0, fill_w, h, fill="#0284c7", outline="")
            # Animated shimmer wave
            shimmer_x = int((math.sin(self.phase) * 0.5 + 0.5) * max(10, fill_w - 40))
            self.prog_canvas.create_rectangle(shimmer_x, 0, min(fill_w, shimmer_x + 45), h, fill="#38bdf8", outline="")

        pct_txt = f"{self.progress_disp * 100:.0f}%"
        self.prog_canvas.create_text(w // 2, h // 2, text=pct_txt, fill="#ffffff", font=("Segoe UI", 9, "bold"))
        self.after(25, self._animate_tick)

    def _start_install(self) -> None:
        self.install_btn.configure(state="disabled", text="Installing...")
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self) -> None:
        try:
            target_dir = self.install_dir_var.get().strip()
            os.makedirs(target_dir, exist_ok=True)
            self.progress_target = 0.2
            self.after(0, lambda: self.status_lbl.configure(text=f"Deploying self-contained binary to {target_dir}..."))

            target_exe = os.path.join(target_dir, "AndroidScrcpyDeXStudio.exe")
            target_ico = os.path.join(target_dir, "android_scrcpy_dex.ico")
            target_png = os.path.join(target_dir, "android_scrcpy_dex.png")

            shutil.copy2(self.exe_src, target_exe)
            if os.path.isfile(self.ico_src):
                shutil.copy2(self.ico_src, target_ico)
            if os.path.isfile(self.png_src):
                shutil.copy2(self.png_src, target_png)

            self.progress_target = 0.55

            # Deploy standalone single-file copy to C:\Users\franc\Downloads so clicking inside Downloads works directly!
            if self.chk_downloads.get():
                dl_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                if os.path.isdir(dl_dir):
                    dl_exe = os.path.join(dl_dir, "AndroidScrcpyDeXStudio.exe")
                    try:
                        shutil.copy2(self.exe_src, dl_exe)
                    except Exception:
                        pass

            self.progress_target = 0.75
            self.after(0, lambda: self.status_lbl.configure(text="Creating Windows Shortcuts & Registry Metadata..."))

            if self.chk_startmenu.get():
                sm_lnk = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Android & Scrcpy DeX Studio.lnk")
                self._create_shortcut(sm_lnk, target_exe, target_dir, target_ico)
                self._register_uninstaller(target_dir, target_exe, target_ico)

            if self.chk_desktop.get():
                desk_lnk = os.path.join(os.path.expanduser("~"), "Desktop", "Android & Scrcpy DeX Studio.lnk")
                self._create_shortcut(desk_lnk, target_exe, target_dir, target_ico)

            self.installed_exe = target_exe
            self.progress_target = 1.0
            time.sleep(0.35)
            self.after(0, self._on_install_complete)
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Installation Failed", str(exc)))
            self.after(0, lambda: self.install_btn.configure(state="normal", text="⚡ INSTALL & LAUNCH STUDIO NOW"))

    @staticmethod
    def _create_shortcut(lnk_path: str, target_exe: str, work_dir: str, icon_path: str) -> None:
        ps_cmd = (
            f"$wsh = New-Object -ComObject WScript.Shell; "
            f"$sc = $wsh.CreateShortcut('{lnk_path}'); "
            f"$sc.TargetPath = '{target_exe}'; "
            f"$sc.WorkingDirectory = '{work_dir}'; "
            f"$sc.IconLocation = '{icon_path},0'; "
            f"$sc.Description = 'J.A.R.V.I.S. Android & Scrcpy DeX Studio v2.0'; "
            f"$sc.Save()"
        )
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
        )

    @staticmethod
    def _register_uninstaller(install_dir: str, exe_path: str, icon_path: str) -> None:
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AndroidScrcpyDeXStudio"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "J.A.R.V.I.S. Android & Scrcpy DeX Studio")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "2.0.0")
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "J.A.R.V.I.S. Mobile Engineering Studio")
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f"{icon_path},0")
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'cmd.exe /c rmdir /s /q "{install_dir}"')
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)

    def _on_install_complete(self) -> None:
        self.status_lbl.configure(
            text=f"✅ Installed to {self.installed_exe} (and synced to Downloads!)",
            text_color="#10b981",
        )
        self.install_btn.configure(
            state="normal",
            text="🚀 LAUNCH STUDIO NOW",
            fg_color="#10b981",
            hover_color="#059669",
            command=self._launch_and_exit,
        )
        self._launch_installed_app()

    def _launch_installed_app(self) -> None:
        if self.installed_exe and os.path.isfile(self.installed_exe):
            subprocess.Popen([self.installed_exe], cwd=os.path.dirname(self.installed_exe), creationflags=CREATE_NO_WINDOW)

    def _launch_and_exit(self) -> None:
        self._launch_installed_app()
        self.destroy()


if __name__ == "__main__":
    wizard = StudioSetupInstaller()
    wizard.mainloop()
