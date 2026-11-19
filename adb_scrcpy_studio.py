#!/usr/bin/env python3
"""
J.A.R.V.I.S. Android & Scrcpy DeX Studio v3.0 — Flagship Obsidian Glass Edition
Self-Contained Multi-Platform Android Control, Live Task Manager, Scrcpy Mirror & DeX Workstation
UI Architecture (v3.0):
 - Deep Obsidian Glassmorphism Palette (#06080d Void, #0c1018 Glass Card, #141b29 Elevated Surface, #1e293b Rim)
 - Sleek Left Sidebar Navigation Rail + Top Device Telemetry Header Banner (Zero visual clutter)
 - 1-Click Quick Profile Presets for Scrcpy Mirror & PC DeX Mode
 - 4x Supersampled Anti-Aliased Pillow Radial Gauges, Grid-Backed Glowing Sparklines & Alternating Row Tables
 - Magnetic Android Emulator Side-Toolbar (`ScrcpyEmulatorSideBar`) docked directly alongside the Scrcpy Mirror window
 - Multi-APK Batch Installer Popup Modal (`BatchApkInstallModal`) with 60fps Shimmer Progress Bar
"""

import os
import sys

# Windowed mode standard stream guards (PyInstaller --windowed safety)
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

import re
import math
import time
import json
import ctypes
import shutil
import threading
import subprocess
from collections import deque
from typing import Dict, List, Optional, Tuple, Any, Callable
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import psutil
from PIL import Image, ImageDraw
import customtkinter as ctk

# Configure Dark Obsidian theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
APP_VERSION = "3.1.0"

# Obsidian Glass Design System Palette
C_VOID = "#06080d"
C_SIDEBAR = "#0a0d14"
C_CARD = "#0e131d"
C_SURFACE = "#151c2b"
C_SURFACE_HOVER = "#1e293b"
C_BORDER = "#1e293b"
C_BORDER_GLOW = "#0284c7"
C_ACCENT = "#38bdf8"
C_PRIMARY = "#0284c7"
C_PRIMARY_HOV = "#0369a1"
C_EMERALD = "#10b981"
C_EMERALD_HOV = "#059669"
C_VIOLET = "#8b5cf6"
C_VIOLET_HOV = "#7c3aed"
C_AMBER = "#f59e0b"
C_AMBER_HOV = "#d97706"
C_CRIMSON = "#e11d48"
C_CRIMSON_HOV = "#be123c"
C_TEXT_MAIN = "#f8fafc"
C_TEXT_SUB = "#94a3b8"
C_TEXT_MUTED = "#64748b"


def get_bundle_dir() -> str:
    """Return PyInstaller _MEIPASS bundle extraction root or script directory."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return getattr(sys, "_MEIPASS")
    return os.path.dirname(os.path.abspath(__file__))


def get_subprocess_kwargs() -> Dict[str, Any]:
    """Return cross-platform subprocess arguments enforcing Rule #4 (CREATE_NO_WINDOW & SW_HIDE)."""
    kwargs: Dict[str, Any] = {}
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
        kwargs["startupinfo"] = startupinfo
        kwargs["creationflags"] = CREATE_NO_WINDOW
    return kwargs


def resolve_binary(bin_name: str, win_fallbacks: List[str], linux_fallbacks: List[str]) -> str:
    """
    Resolve binary executable path:
    - For `adb`, prefer system-installed Platform Tools first so the GUI shares the exact same ADB server
      version (e.g. 37.0.1) as the user's terminal without killing/restarting the daemon; fall back to
      the self-contained bundled_bins/adb.exe on machines without Platform Tools installed.
    - For `scrcpy`, prefer the self-contained bundled_bins/scrcpy.exe v4.0 first.
    """
    bundle_root = get_bundle_dir()
    exe_ext = ".exe" if os.name == "nt" else ""
    bundled_candidate = os.path.join(bundle_root, "bundled_bins", f"{bin_name}{exe_ext}")
    local_candidate = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bundled_bins", f"{bin_name}{exe_ext}")

    if bin_name == "adb":
        found = shutil.which(bin_name)
        if found:
            return found
        candidates = win_fallbacks if os.name == "nt" else linux_fallbacks
        for path in candidates:
            expanded = os.path.expandvars(os.path.expanduser(path))
            if os.path.isfile(expanded):
                return expanded

    if os.path.isfile(bundled_candidate):
        return bundled_candidate
    if os.path.isfile(local_candidate):
        return local_candidate

    found = shutil.which(bin_name)
    if found:
        return found

    candidates = win_fallbacks if os.name == "nt" else linux_fallbacks
    for path in candidates:
        expanded = os.path.expandvars(os.path.expanduser(path))
        if os.path.isfile(expanded):
            return expanded
    return bin_name


ADB_BIN = resolve_binary(
    "adb",
    [
        r"C:\Users\franc\adb.exe",
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools\adb.exe",
        r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe",
    ],
    ["/usr/bin/adb", "/usr/local/bin/adb", "~/Android/Sdk/platform-tools/adb"],
)

SCRCPY_BIN = resolve_binary(
    "scrcpy",
    [
        r"C:\Users\franc\scrcpy.exe",
        r"%USERPROFILE%\scrcpy.exe",
        r"%LOCALAPPDATA%\Microsoft\WinGet\Links\scrcpy.exe",
        r"C:\Program Files\scrcpy\scrcpy.exe",
    ],
    ["/usr/bin/scrcpy", "/usr/local/bin/scrcpy"],
)


def find_window_rect_by_title(title_sub: str) -> Optional[Tuple[int, int, int, int, bool]]:
    """
    Locate a native OS window matching `title_sub` and return (left, top, right, bottom, is_minimized).
    Uses Win32 user32 ctypes on Windows and xdotool on Linux.
    """
    if os.name == "nt":
        user32 = ctypes.windll.user32
        found_rect: List[Tuple[int, int, int, int, bool]] = []

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def enum_cb(hwnd: int, _lparam: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if title_sub.lower() in buf.value.lower():
                rc = RECT()
                if user32.GetWindowRect(hwnd, ctypes.byref(rc)):
                    is_min = bool(user32.IsIconic(hwnd))
                    found_rect.append((rc.left, rc.top, rc.right, rc.bottom, is_min))
                    return False
            return True

        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        return found_rect[0] if found_rect else None
    else:
        try:
            proc = subprocess.run(
                ["xdotool", "search", "--name", title_sub],
                capture_output=True,
                text=True,
                timeout=0.4,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                wid = proc.stdout.strip().splitlines()[0]
                gproc = subprocess.run(
                    ["xdotool", "getwindowgeometry", "--shell", wid],
                    capture_output=True,
                    text=True,
                    timeout=0.4,
                )
                if gproc.returncode == 0:
                    kv = {}
                    for line in gproc.stdout.splitlines():
                        if "=" in line:
                            k, v = line.split("=", 1)
                            kv[k.strip()] = int(v.strip())
                    x, y = kv.get("X", 100), kv.get("Y", 100)
                    w, h = kv.get("WIDTH", 400), kv.get("HEIGHT", 800)
                    return (x, y, x + w, y + h, False)
        except Exception:
            pass
        return None


class ModernVectorIconFactory:
    """Renders 4x supersampled anti-aliased vector icons and 4x radial gauges into CTkImage objects."""

    def __init__(self) -> None:
        self._cache: Dict[str, ctk.CTkImage] = {}

    def get(self, name: str, size: int = 20, color: Tuple[int, int, int, int] = (56, 189, 248, 255)) -> ctk.CTkImage:
        key = f"{name}_{size}_{color}"
        if key in self._cache:
            return self._cache[key]

        ss = size * 4  # 4x supersampling
        img = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        c = color
        w = max(6, ss // 11)
        m = ss // 7

        if name == "back":
            pts = [(ss - m * 1.4, m), (m * 1.3, ss // 2), (ss - m * 1.4, ss - m)]
            d.polygon(pts, fill=c)
        elif name == "home":
            d.ellipse([m, m, ss - m, ss - m], outline=c, width=w)
            im = int(ss * 0.28)
            d.ellipse([im, im, ss - im, ss - im], fill=c)
        elif name == "recents":
            d.rounded_rectangle([m, m, ss - m, ss - m], radius=ss // 6, outline=c, width=w)
        elif name == "vol_up":
            d.polygon(
                [
                    (m, ss * 0.38),
                    (ss * 0.35, ss * 0.38),
                    (ss * 0.55, m * 1.2),
                    (ss * 0.55, ss - m * 1.2),
                    (ss * 0.35, ss * 0.62),
                    (m, ss * 0.62),
                ],
                fill=c,
            )
            d.arc([ss * 0.38, ss * 0.25, ss * 0.85, ss * 0.75], start=-50, end=50, fill=c, width=w)
        elif name == "vol_down":
            d.polygon(
                [
                    (m * 1.3, ss * 0.38),
                    (ss * 0.42, ss * 0.38),
                    (ss * 0.65, m * 1.2),
                    (ss * 0.65, ss - m * 1.2),
                    (ss * 0.42, ss * 0.62),
                    (m * 1.3, ss * 0.62),
                ],
                fill=c,
            )
        elif name == "mute":
            d.polygon(
                [
                    (m, ss * 0.38),
                    (ss * 0.32, ss * 0.38),
                    (ss * 0.52, m * 1.2),
                    (ss * 0.52, ss - m * 1.2),
                    (ss * 0.32, ss * 0.62),
                    (m, ss * 0.62),
                ],
                fill=c,
            )
            d.line([(ss * 0.64, ss * 0.34), (ss - m, ss * 0.66)], fill=c, width=w)
            d.line([(ss - m, ss * 0.34), (ss * 0.64, ss * 0.66)], fill=c, width=w)
        elif name == "power":
            d.arc([m, m * 1.2, ss - m, ss - m], start=-55, end=235, fill=c, width=w)
            d.line([(ss // 2, m * 0.7), (ss // 2, ss * 0.48)], fill=c, width=w)
        elif name == "camera":
            d.rounded_rectangle([m, ss * 0.26, ss - m, ss - m * 1.1], radius=ss // 8, outline=c, width=w)
            d.ellipse([ss * 0.33, ss * 0.38, ss * 0.67, ss * 0.72], outline=c, width=w)
        elif name == "bell":
            d.chord([m * 1.3, m, ss - m * 1.3, ss * 0.78], start=180, end=360, fill=c)
            d.rounded_rectangle([m, ss * 0.68, ss - m, ss * 0.78], radius=4, fill=c)
            d.ellipse([ss * 0.42, ss * 0.78, ss * 0.58, ss - m * 0.8], fill=c)
        elif name == "rotate":
            d.arc([m, m, ss - m, ss - m], start=15, end=285, fill=c, width=w)
            d.polygon([(ss - m * 0.7, ss * 0.45), (ss - m * 2.1, ss * 0.45), (ss - m * 1.4, ss * 0.22)], fill=c)
        elif name == "mirror":
            d.rounded_rectangle([ss * 0.24, m * 0.8, ss * 0.76, ss - m * 0.8], radius=ss // 8, outline=c, width=w)
            d.ellipse([ss * 0.45, ss - m * 1.8, ss * 0.55, ss - m * 1.1], fill=c)
        elif name == "dex":
            d.rounded_rectangle([m * 0.8, m, ss - m * 0.8, ss * 0.72], radius=ss // 10, outline=c, width=w)
            d.line([(ss // 2, ss * 0.72), (ss // 2, ss - m)], fill=c, width=w)
            d.line([(ss * 0.3, ss - m), (ss * 0.7, ss - m)], fill=c, width=w)
        elif name == "cpu":
            d.rounded_rectangle([m * 1.4, m * 1.4, ss - m * 1.4, ss - m * 1.4], radius=ss // 9, outline=c, width=w)
            d.rectangle([ss * 0.36, ss * 0.36, ss * 0.64, ss * 0.64], fill=c)
            for p in (0.32, 0.5, 0.68):
                px = int(ss * p)
                d.line([(px, m * 0.5), (px, m * 1.4)], fill=c, width=w // 2 + 2)
                d.line([(px, ss - m * 1.4), (px, ss - m * 0.5)], fill=c, width=w // 2 + 2)
                d.line([(m * 0.5, px), (m * 1.4, px)], fill=c, width=w // 2 + 2)
                d.line([(ss - m * 1.4, px), (ss - m * 0.5, px)], fill=c, width=w // 2 + 2)
        elif name == "apps":
            r = ss // 10
            boxes = [
                (m, m, ss * 0.45, ss * 0.45),
                (ss * 0.55, m, ss - m, ss * 0.45),
                (m, ss * 0.55, ss * 0.45, ss - m),
                (ss * 0.55, ss * 0.55, ss - m, ss - m),
            ]
            for b in boxes:
                d.rounded_rectangle(b, radius=r, fill=c)
        elif name == "info":
            d.ellipse([m, m, ss - m, ss - m], outline=c, width=w)
            d.ellipse([ss * 0.44, ss * 0.25, ss * 0.56, ss * 0.37], fill=c)
            d.line([(ss // 2, ss * 0.45), (ss // 2, ss * 0.74)], fill=c, width=w)
        elif name == "refresh":
            d.arc([m, m, ss - m, ss - m], start=35, end=315, fill=c, width=w)
            d.polygon([(ss - m * 0.8, ss * 0.22), (ss - m * 2.2, ss * 0.22), (ss - m * 1.2, ss * 0.42)], fill=c)
        elif name == "wifi":
            d.arc([m * 0.7, m * 1.2, ss - m * 0.7, ss], start=215, end=325, fill=c, width=w)
            d.arc([m * 1.6, m * 2.2, ss - m * 1.6, ss * 0.95], start=215, end=325, fill=c, width=w)
            d.ellipse([ss * 0.43, ss * 0.68, ss * 0.57, ss * 0.82], fill=c)
        elif name == "play":
            d.polygon([(ss * 0.25, m * 1.1), (ss - m * 1.1, ss // 2), (ss * 0.25, ss - m * 1.1)], fill=c)
        elif name == "stop":
            d.rounded_rectangle([m * 1.3, m * 1.3, ss - m * 1.3, ss - m * 1.3], radius=ss // 10, fill=c)
        elif name == "trash":
            d.line([(m * 1.2, ss * 0.24), (ss - m * 1.2, ss * 0.24)], fill=c, width=w)
            d.rounded_rectangle([ss * 0.24, ss * 0.24, ss * 0.76, ss - m], radius=ss // 12, outline=c, width=w)
        elif name == "download":
            d.line([(ss // 2, m), (ss // 2, ss * 0.65)], fill=c, width=w)
            d.polygon([(ss * 0.28, ss * 0.52), (ss * 0.72, ss * 0.52), (ss // 2, ss * 0.76)], fill=c)
            d.line([(m * 1.2, ss - m), (ss - m * 1.2, ss - m)], fill=c, width=w)
        elif name == "bolt":
            pts = [(ss * 0.56, m * 0.8), (ss * 0.24, ss * 0.54), (ss * 0.48, ss * 0.54), (ss * 0.42, ss - m * 0.8), (ss * 0.76, ss * 0.44), (ss * 0.52, ss * 0.44)]
            d.polygon(pts, fill=c)
        else:
            d.ellipse([m, m, ss - m, ss - m], outline=c, width=w)

        final_img = img.resize((size, size), Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=final_img, dark_image=final_img, size=(size, size))
        self._cache[key] = ctk_img
        return ctk_img

    def render_smooth_gauge(
        self,
        size: int,
        pct: float,
        max_v: float,
        ring_rgb: Tuple[int, int, int],
        glow_rgb: Tuple[int, int, int],
    ) -> ctk.CTkImage:
        """Render a 4x supersampled anti-aliased radial ring gauge via Pillow."""
        norm = max(0.0, min(1.0, pct / max(max_v, 1.0)))
        bucket = int(round(norm * 100))
        key = f"gauge_{size}_{bucket}_{ring_rgb}"
        if key in self._cache:
            return self._cache[key]

        ss = size * 4
        img = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        pad = 24
        box = [pad, pad, ss - pad, ss - pad]

        # Background subtle track
        d.arc(box, start=135, end=405, fill=(30, 41, 59, 255), width=26)

        if bucket > 0:
            end_ang = 135 + int(270 * (bucket / 100.0))
            # Outer ambient glow arc
            d.arc(box, start=135, end=end_ang, fill=(*glow_rgb, 90), width=38)
            # Crisp inner neon arc
            d.arc(box, start=135, end=end_ang, fill=(*ring_rgb, 255), width=24)

        final_img = img.resize((size, size), Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=final_img, dark_image=final_img, size=(size, size))
        if len(self._cache) > 450:
            self._cache.clear()
        self._cache[key] = ctk_img
        return ctk_img


class ScrcpyEmulatorSideBar(ctk.CTkToplevel):
    """
    Magnetic Android Studio Emulator Side-Toolbar that docks directly alongside the Scrcpy Mirror window!
    Automatically tracks the Scrcpy window position & height in real-time (30fps) as you drag or resize Scrcpy.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        icons: ModernVectorIconFactory,
        target_title: str,
        proc: subprocess.Popen,
        on_action: Callable[[str], None],
    ) -> None:
        super().__init__(parent)
        self.icons = icons
        self.target_title = target_title
        self.proc = proc
        self.on_action = on_action
        self.alive = True
        self.bar_width = 58
        self.bar_height = 515

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=C_VOID)
        self.geometry(f"{self.bar_width}x{self.bar_height}+100+100")

        self._manual_drag_offset: Optional[Tuple[int, int]] = None
        self._drag_start_x = 0
        self._drag_start_y = 0

        self._build_toolbar()
        self.after(40, self._magnetic_dock_loop)

    def _build_toolbar(self) -> None:
        outer = ctk.CTkFrame(
            self,
            fg_color=C_CARD,
            corner_radius=14,
            border_width=1,
            border_color=C_ACCENT,
        )
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        grip = ctk.CTkLabel(
            outer,
            text="⋮⋮",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C_TEXT_MUTED,
            height=20,
            cursor="fleur",
        )
        grip.pack(fill="x", pady=(5, 2))
        grip.bind("<ButtonPress-1>", self._start_drag)
        grip.bind("<B1-Motion>", self._do_drag)
        grip.bind("<Double-Button-1>", self._snap_back)

        buttons = [
            ("Power", "power", "26", C_CRIMSON, C_CRIMSON_HOV, (255, 255, 255, 255)),
            ("Vol +", "vol_up", "24", C_SURFACE, C_SURFACE_HOVER, (226, 232, 240, 255)),
            ("Vol -", "vol_down", "25", C_SURFACE, C_SURFACE_HOVER, (226, 232, 240, 255)),
            ("Mute", "mute", "164", C_SURFACE, C_SURFACE_HOVER, (245, 158, 11, 255)),
            ("Rotate", "rotate", "cmd_rotate", C_SURFACE, C_SURFACE_HOVER, (56, 189, 248, 255)),
            ("Snap", "camera", "cmd_screen", C_EMERALD, C_EMERALD_HOV, (255, 255, 255, 255)),
            ("Alerts", "bell", "cmd_notif", C_SURFACE, C_SURFACE_HOVER, (168, 85, 247, 255)),
        ]

        for _lbl, ic_name, act, fg, hov, ic_col in buttons:
            b = ctk.CTkButton(
                outer,
                text="",
                image=self.icons.get(ic_name, 20, ic_col),
                width=42,
                height=38,
                corner_radius=9,
                fg_color=fg,
                hover_color=hov,
                command=lambda a=act: self.on_action(a),
            )
            b.pack(padx=6, pady=3)

        sep = ctk.CTkFrame(outer, height=2, fg_color=C_BORDER)
        sep.pack(fill="x", padx=8, pady=6)

        primary_nav = [
            ("BACK", "back", "4", C_SURFACE, C_SURFACE_HOVER, (56, 189, 248, 255)),
            ("HOME", "home", "3", C_PRIMARY, C_PRIMARY_HOV, (255, 255, 255, 255)),
            ("RECENT", "recents", "187", C_SURFACE, C_SURFACE_HOVER, (56, 189, 248, 255)),
        ]

        for lbl_txt, ic_name, act, fg, hov, ic_col in primary_nav:
            b = ctk.CTkButton(
                outer,
                text=lbl_txt,
                image=self.icons.get(ic_name, 22, ic_col),
                compound="top",
                width=46,
                height=52,
                corner_radius=10,
                fg_color=fg,
                hover_color=hov,
                font=ctk.CTkFont(size=8, weight="bold"),
                command=lambda a=act: self.on_action(a),
            )
            b.pack(padx=5, pady=4)

    def _start_drag(self, event: Any) -> None:
        self._drag_start_x = event.x_root - self.winfo_x()
        self._drag_start_y = event.y_root - self.winfo_y()

    def _do_drag(self, event: Any) -> None:
        nx = event.x_root - self._drag_start_x
        ny = event.y_root - self._drag_start_y
        self._manual_drag_offset = (nx, ny)
        self.geometry(f"{self.bar_width}x{self.bar_height}+{nx}+{ny}")

    def _snap_back(self, _event: Any) -> None:
        self._manual_drag_offset = None

    def _magnetic_dock_loop(self) -> None:
        if not self.alive:
            return
        if self.proc.poll() is not None:
            self.close_bar()
            return

        rect = find_window_rect_by_title(self.target_title)
        if rect is not None:
            left, top, right, _bottom, is_min = rect
            if is_min:
                self.withdraw()
            else:
                self.deiconify()
                if self._manual_drag_offset is None:
                    scr_w = self.winfo_screenwidth()
                    target_x = right + 2
                    if target_x + self.bar_width > scr_w:
                        target_x = max(0, left - self.bar_width - 2)
                    target_y = top + 32
                    cur_geom = f"{self.bar_width}x{self.bar_height}+{target_x}+{target_y}"
                    if self.geometry() != cur_geom:
                        self.geometry(cur_geom)

        self.after(35, self._magnetic_dock_loop)

    def close_bar(self) -> None:
        self.alive = False
        try:
            self.destroy()
        except Exception:
            pass


class BatchApkInstallModal(ctk.CTkToplevel):
    """
    Modern Animated Multi-APK Batch Installer Popup Modal with 60fps Shimmer Progress Bar,
    Live Step Counter, Detailed APK Status Console, and Cancellation Support.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        adb: "AdbController",
        serial: str,
        apk_paths: List[str],
        on_complete_cb: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.adb = adb
        self.serial = serial
        self.apk_paths = apk_paths
        self.on_complete_cb = on_complete_cb
        self.total_count = len(apk_paths)
        self.success_count = 0
        self.fail_count = 0
        self.cancelled = False
        self.finished = False

        self.phase = 0.0
        self.progress_target = 0.0
        self.progress_disp = 0.0

        self.title(f"Batch APK Installer — {self.total_count} Package(s) → {serial}")
        self.geometry("640x430")
        self.resizable(False, False)
        self.configure(fg_color=C_VOID)
        self.transient(parent)
        self.grab_set()

        self._build_modal_ui()
        self.after(25, self._animate_progress_60fps)
        threading.Thread(target=self._batch_install_worker, daemon=True).start()

    def _build_modal_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=14, border_width=1, border_color=C_BORDER)
        header.pack(fill="x", padx=18, pady=(18, 10))

        self.lbl_title = ctk.CTkLabel(
            header,
            text=f"📦 Batch Installing {self.total_count} APK Package(s) onto {self.serial}",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=C_ACCENT,
        )
        self.lbl_title.pack(anchor="w", padx=16, pady=(12, 2))

        self.lbl_current = ctk.CTkLabel(
            header,
            text="Preparing batch installation queue...",
            font=ctk.CTkFont(size=12),
            text_color=C_TEXT_SUB,
        )
        self.lbl_current.pack(anchor="w", padx=16, pady=(0, 12))

        prog_frame = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=14, border_width=1, border_color=C_BORDER)
        prog_frame.pack(fill="x", padx=18, pady=6)

        top_p = ctk.CTkFrame(prog_frame, fg_color="transparent")
        top_p.pack(fill="x", padx=16, pady=(10, 4))

        self.lbl_step_counter = ctk.CTkLabel(
            top_p,
            text=f"Progress: 0 / {self.total_count} (0%)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_ACCENT,
        )
        self.lbl_step_counter.pack(side="left")

        self.lbl_stats = ctk.CTkLabel(
            top_p,
            text="✅ 0 Success  •  ❌ 0 Failed",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_EMERALD,
        )
        self.lbl_stats.pack(side="right")

        self.prog_canvas = tk.Canvas(prog_frame, height=22, bg=C_VOID, highlightthickness=0)
        self.prog_canvas.pack(fill="x", padx=16, pady=(2, 14))

        self.log_box = ctk.CTkTextbox(
            self,
            height=165,
            fg_color=C_CARD,
            text_color=C_TEXT_MAIN,
            border_width=1,
            border_color=C_BORDER,
            corner_radius=12,
            font=ctk.CTkFont(family="Consolas", size=11),
        )
        self.log_box.pack(fill="both", expand=True, padx=18, pady=6)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=18, pady=(6, 16))

        self.action_btn = ctk.CTkButton(
            footer,
            text="⏹ Cancel Remaining",
            width=165,
            height=38,
            corner_radius=10,
            fg_color=C_CRIMSON,
            hover_color=C_CRIMSON_HOV,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_action_btn,
        )
        self.action_btn.pack(side="right")

    def _append_log(self, msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {msg}\n")
        self.log_box.see("end")

    def _animate_progress_60fps(self) -> None:
        if not self.winfo_exists():
            return
        self.phase += 0.16
        self.progress_disp += (self.progress_target - self.progress_disp) * 0.22

        self.prog_canvas.delete("all")
        w = max(self.prog_canvas.winfo_width(), 560)
        h = 22
        self.prog_canvas.create_rectangle(0, 0, w, h, fill=C_VOID, outline=C_BORDER)

        fill_w = int(w * max(0.0, min(1.0, self.progress_disp)))
        if fill_w > 2:
            bar_col = C_EMERALD if (self.finished and self.fail_count == 0) else C_PRIMARY
            if self.finished and self.fail_count > 0:
                bar_col = C_AMBER
            self.prog_canvas.create_rectangle(0, 0, fill_w, h, fill=bar_col, outline="")
            if not self.finished:
                shimmer_x = int((math.sin(self.phase) * 0.5 + 0.5) * max(10, fill_w - 55))
                self.prog_canvas.create_rectangle(
                    shimmer_x, 0, min(fill_w, shimmer_x + 55), h, fill=C_ACCENT, outline=""
                )

        pct = int(round(self.progress_disp * 100))
        self.prog_canvas.create_text(w // 2, h // 2, text=f"{pct}%", fill="#ffffff", font=("Segoe UI", 9, "bold"))

        self.after(25, self._animate_progress_60fps)

    def _batch_install_worker(self) -> None:
        for idx, apk_path in enumerate(self.apk_paths, start=1):
            if self.cancelled:
                self.after(0, lambda: self._append_log("⚠️ Batch installation cancelled by user."))
                break

            fname = os.path.basename(apk_path)
            size_mb = os.path.getsize(apk_path) / (1024 * 1024) if os.path.isfile(apk_path) else 0.0
            base_prog = (idx - 1) / max(self.total_count, 1)
            mid_prog = (idx - 0.35) / max(self.total_count, 1)
            self.progress_target = mid_prog

            self.after(
                0,
                lambda i=idx, fn=fname, sz=size_mb, bp=base_prog: (
                    self.lbl_current.configure(text=f"Installing ({i}/{self.total_count}): {fn} ({sz:.1f} MB)..."),
                    self.lbl_step_counter.configure(
                        text=f"Progress: {i - 1} / {self.total_count} ({int(bp * 100)}%)"
                    ),
                    self._append_log(f"▶ [{i}/{self.total_count}] Installing {fn} ({sz:.1f} MB)..."),
                ),
            )

            t0 = time.time()
            code, out, err = self.adb.run_adb(["install", "-r", "-d", apk_path], serial=self.serial, timeout=180.0)
            elapsed = time.time() - t0

            if code == 0 and "Success" in out:
                self.success_count += 1
                self.after(
                    0,
                    lambda fn=fname, el=elapsed: self._append_log(f"  ✅ SUCCESS: {fn} installed in {el:.1f}s"),
                )
            else:
                self.fail_count += 1
                reason = (err or out or "Unknown ADB install error").replace("\n", " ")
                self.after(
                    0,
                    lambda fn=fname, r=reason: self._append_log(f"  ❌ FAILED: {fn} -> {r}"),
                )

            done_prog = idx / max(self.total_count, 1)
            self.progress_target = done_prog
            s_cnt, f_cnt = self.success_count, self.fail_count
            self.after(
                0,
                lambda i=idx, dp=done_prog, sc=s_cnt, fc=f_cnt: (
                    self.lbl_step_counter.configure(
                        text=f"Progress: {i} / {self.total_count} ({int(dp * 100)}%)"
                    ),
                    self.lbl_stats.configure(
                        text=f"✅ {sc} Success  •  ❌ {fc} Failed",
                        text_color=C_EMERALD if fc == 0 else C_AMBER,
                    ),
                ),
            )

        self.finished = True
        self.progress_target = 1.0
        self.after(0, self._finalize_ui)

    def _finalize_ui(self) -> None:
        self.lbl_current.configure(
            text=f"Batch Complete: {self.success_count} installed, {self.fail_count} failed.",
            text_color=C_EMERALD if self.fail_count == 0 else C_AMBER,
        )
        self.action_btn.configure(
            text="✅ Done / Close",
            fg_color=C_EMERALD if self.fail_count == 0 else C_PRIMARY,
            hover_color=C_EMERALD_HOV if self.fail_count == 0 else C_PRIMARY_HOV,
        )
        try:
            self.on_complete_cb()
        except Exception:
            pass

    def _on_action_btn(self) -> None:
        if not self.finished:
            self.cancelled = True
            self.action_btn.configure(state="disabled", text="Cancelling...")
        else:
            self.grab_release()
            self.destroy()


class AdbController:
    """Thread-safe controller for executing hidden ADB, Scrcpy, and Autonomous Multi-Key Device Authorization."""

    def __init__(self) -> None:
        self.adb_path = ADB_BIN
        self.scrcpy_path = SCRCPY_BIN
        self.synced_devices: set[str] = set()
        self.prompted_unauth_serials: set[str] = set()
        self.last_reconnect_ts: float = 0.0
        self._init_multi_machine_adb_keys()

    def _init_multi_machine_adb_keys(self) -> None:
        """
        Install bundled Workstation + DOOMSDAY ADB RSA keypairs into ~/.android and configure ADB_VENDOR_KEYS
        so any phone previously authorized on either machine automatically authorizes without a prompt.
        """
        try:
            android_dir = os.path.join(os.path.expanduser("~"), ".android")
            os.makedirs(android_dir, exist_ok=True)
            bundle_keys_dir = os.path.join(get_bundle_dir(), "adb_keys")
            if os.path.isdir(bundle_keys_dir):
                for fname in os.listdir(bundle_keys_dir):
                    src = os.path.join(bundle_keys_dir, fname)
                    dst = os.path.join(android_dir, fname)
                    if os.path.isfile(src) and not os.path.isfile(dst):
                        shutil.copy2(src, dst)
                        if os.name != "nt" and not fname.endswith(".pub"):
                            try:
                                os.chmod(dst, 0o600)
                            except Exception:
                                pass

            key_files: List[str] = []
            for fname in os.listdir(android_dir):
                if fname.endswith("adbkey") and not fname.endswith(".pub"):
                    full_k = os.path.join(android_dir, fname)
                    if os.path.isfile(full_k):
                        key_files.append(full_k)

            if key_files:
                sep = ";" if os.name == "nt" else ":"
                os.environ["ADB_VENDOR_KEYS"] = sep.join(key_files)
        except Exception:
            pass

    def run_adb(self, args: List[str], serial: Optional[str] = None, timeout: float = 8.0) -> Tuple[int, str, str]:
        cmd = [self.adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(args)
        try:
            env = os.environ.copy()
            proc = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                **get_subprocess_kwargs(),
            )
            return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as exc:
            return -1, "", str(exc)

    def force_reconnect_unauthorized(self, serial: Optional[str] = None) -> str:
        """
        Actively dispatch ADB RSA handshake and reconnect offline/unauthorized transports
        so the connected phone immediately pops up or accepts the RSA key authorization.
        """
        self._init_multi_machine_adb_keys()
        self.run_adb(["reconnect", "offline"], timeout=4.0)
        if serial:
            self.run_adb(["-s", serial, "reconnect"], timeout=4.0)
        else:
            self.run_adb(["reconnect"], timeout=4.0)
        self.last_reconnect_ts = time.time()
        return "Dispatched RSA key handshake & ADB reconnect to all connected devices."

    def sync_trusted_pubkeys_to_device(self, serial: str) -> None:
        """
        Once a device is authorized ('device' state), attempt to append all bundled public keys
        (Workstation + ASUS DOOMSDAY) to /data/misc/adb/adb_keys (if root/su is available)
        so the phone is permanently pre-authorized across every PC/Laptop in the fleet.
        """
        if serial in self.synced_devices:
            return
        self.synced_devices.add(serial)
        try:
            android_dir = os.path.join(os.path.expanduser("~"), ".android")
            pub_keys: List[str] = []
            if os.path.isdir(android_dir):
                for fname in os.listdir(android_dir):
                    if fname.endswith(".pub"):
                        with open(os.path.join(android_dir, fname), "r", encoding="utf-8", errors="ignore") as f:
                            k = f.read().strip()
                            if k:
                                pub_keys.append(k)
            if not pub_keys:
                return
            joined = "\\n".join(pub_keys)
            cmd = (
                f"su -c 'mkdir -p /data/misc/adb && "
                f"printf \"{joined}\\n\" >> /data/misc/adb/adb_keys && "
                f"sort -u /data/misc/adb/adb_keys -o /data/misc/adb/adb_keys && "
                f"chmod 0640 /data/misc/adb/adb_keys' 2>/dev/null || true"
            )
            self.run_adb(["shell", cmd], serial=serial, timeout=4.0)
        except Exception:
            pass

    def list_devices(self, auto_heal: bool = True) -> List[Dict[str, str]]:
        code, out, _ = self.run_adb(["devices", "-l"], timeout=5.0)
        devices: List[Dict[str, str]] = []
        if code != 0 or not out:
            return devices
        has_unauth = False
        for line in out.splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                state = parts[1]
                meta = {}
                for token in parts[2:]:
                    if ":" in token:
                        k, v = token.split(":", 1)
                        meta[k] = v
                if state in ("unauthorized", "offline"):
                    has_unauth = True
                elif state == "device":
                    threading.Thread(target=self.sync_trusted_pubkeys_to_device, args=(serial,), daemon=True).start()
                devices.append(
                    {
                        "serial": serial,
                        "state": state,
                        "model": meta.get("model", "Unknown"),
                        "device": meta.get("device", "Unknown"),
                        "transport_id": meta.get("transport_id", ""),
                    }
                )

        # Trigger `adb reconnect offline` ONCE per newly plugged unauthorized/offline serial so we pop up
        # the RSA dialog on the phone without ever resetting the USB transport while the user taps "Allow"
        if auto_heal and has_unauth:
            current_serials = {d["serial"] for d in devices}
            self.prompted_unauth_serials.intersection_update(current_serials)
            unprompted = [
                d["serial"]
                for d in devices
                if d["state"] in ("unauthorized", "offline") and d["serial"] not in self.prompted_unauth_serials
            ]
            if unprompted:
                for s in unprompted:
                    self.prompted_unauth_serials.add(s)
                self.last_reconnect_ts = time.time()
                self.run_adb(["reconnect", "offline"], timeout=3.0)
                time.sleep(0.9)
                # Re-query device list immediately after the 0.9s USB re-enumeration so the dropdown never flickers empty
                code2, out2, _ = self.run_adb(["devices", "-l"], timeout=5.0)
                if code2 == 0 and out2:
                    refreshed: List[Dict[str, str]] = []
                    for line in out2.splitlines()[1:]:
                        line = line.strip()
                        if not line or line.startswith("*"):
                            continue
                        parts = line.split()
                        if len(parts) >= 2:
                            meta = {t.split(":", 1)[0]: t.split(":", 1)[1] for t in parts[2:] if ":" in t}
                            refreshed.append(
                                {
                                    "serial": parts[0],
                                    "state": parts[1],
                                    "model": meta.get("model", "Unknown"),
                                    "device": meta.get("device", "Unknown"),
                                    "transport_id": meta.get("transport_id", ""),
                                }
                            )
                    if refreshed:
                        return refreshed

        return devices

    def send_keyevent(self, serial: str, keycode: str) -> bool:
        code, _, _ = self.run_adb(["shell", "input", "keyevent", str(keycode)], serial=serial, timeout=3.0)
        return code == 0

    def get_device_info(self, serial: str) -> Dict[str, str]:
        script = (
            "echo '===PROPS==='; "
            "getprop ro.product.manufacturer; "
            "getprop ro.product.model; "
            "getprop ro.product.device; "
            "getprop ro.build.version.release; "
            "getprop ro.build.version.sdk; "
            "getprop ro.build.display.id; "
            "getprop ro.build.version.security_patch; "
            "getprop ro.product.cpu.abi; "
            "getprop ro.soc.manufacturer; "
            "getprop ro.soc.model; "
            "getprop gsm.version.baseband; "
            "uname -r; "
            "uptime -p 2>/dev/null || uptime; "
            "echo '===WM==='; wm size; wm density; "
            "echo '===BAT==='; dumpsys battery; "
            "echo '===MEM==='; cat /proc/meminfo | head -n 6; "
            "echo '===DF==='; df -h /data 2>/dev/null | tail -n 1; "
            "echo '===IP==='; ip -4 addr show wlan0 2>/dev/null | grep inet"
        )
        code, out, err = self.run_adb(["shell", script], serial=serial, timeout=8.0)
        info: Dict[str, str] = {"Serial": serial}
        if code != 0:
            info["Error"] = err or "Failed to query device"
            return info

        sections = re.split(r"===(PROPS|WM|BAT|MEM|DF|IP)===", out)
        sec_map: Dict[str, str] = {}
        for i in range(1, len(sections) - 1, 2):
            sec_map[sections[i]] = sections[i + 1].strip()

        props = [line.strip() for line in sec_map.get("PROPS", "").splitlines()]
        prop_keys = [
            "Manufacturer",
            "Model",
            "Codename",
            "Android Version",
            "SDK Level",
            "Build ID",
            "Security Patch",
            "CPU ABI",
            "SoC Vendor",
            "SoC Model",
            "Baseband",
            "Kernel Version",
            "System Uptime",
        ]
        for idx, k in enumerate(prop_keys):
            info[k] = props[idx] if idx < len(props) and props[idx] else "N/A"

        wm_raw = sec_map.get("WM", "")
        res_match = re.search(r"Physical size:\s*(\S+)", wm_raw)
        den_match = re.search(r"Physical density:\s*(\S+)", wm_raw)
        info["Display Resolution"] = res_match.group(1) if res_match else "N/A"
        info["Display Density"] = f"{den_match.group(1)} dpi" if den_match else "N/A"

        bat_raw = sec_map.get("BAT", "")
        lvl_m = re.search(r"level:\s*(\d+)", bat_raw)
        temp_m = re.search(r"temperature:\s*(\d+)", bat_raw)
        volt_m = re.search(r"voltage:\s*(\d+)", bat_raw)
        tech_m = re.search(r"technology:\s*(\S+)", bat_raw)
        info["Battery Level"] = f"{lvl_m.group(1)}%" if lvl_m else "N/A"
        info["Battery Temp"] = f"{int(temp_m.group(1)) / 10.0:.1f} °C" if temp_m else "N/A"
        info["Battery Voltage"] = f"{volt_m.group(1)} mV" if volt_m else "N/A"
        info["Battery Tech"] = tech_m.group(1) if tech_m else "Li-ion"

        mem_raw = sec_map.get("MEM", "")
        mt_m = re.search(r"MemTotal:\s*(\d+)", mem_raw)
        ma_m = re.search(r"MemAvailable:\s*(\d+)", mem_raw)
        if mt_m and ma_m:
            total_mb = int(mt_m.group(1)) // 1024
            avail_mb = int(ma_m.group(1)) // 1024
            used_mb = total_mb - avail_mb
            info["System RAM"] = f"{used_mb} MB / {total_mb} MB ({avail_mb} MB Free)"
        else:
            info["System RAM"] = "N/A"

        df_raw = sec_map.get("DF", "")
        df_parts = df_raw.split()
        if len(df_parts) >= 5:
            info["Internal Storage (/data)"] = f"{df_parts[2]} used / {df_parts[1]} total ({df_parts[4]})"
        else:
            info["Internal Storage (/data)"] = "N/A"

        ip_raw = sec_map.get("IP", "")
        ip_m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", ip_raw)
        info["Wi-Fi LAN IP (wlan0)"] = ip_m.group(1) if ip_m else "Disconnected / N/A"

        return info


class SystemMonitorEngine:
    """Thread-safe live system monitor & task manager engine for connected Android devices."""

    def __init__(self, adb: AdbController) -> None:
        self.adb = adb
        self.lock = threading.Lock()
        self.running = True
        self.active_serial: Optional[str] = None
        self.paused = False

        self.cpu_total_pct: float = 0.0
        self.ram_used_mb: float = 0.0
        self.ram_total_mb: float = 12288.0
        self.ram_pct: float = 0.0
        self.swap_used_mb: float = 0.0
        self.swap_total_mb: float = 1.0
        self.battery_level: int = 0
        self.battery_temp_c: float = 0.0
        self.tasks_total: int = 0
        self.tasks_running: int = 0

        self.history_cpu = deque([0.0] * 60, maxlen=60)
        self.history_ram = deque([0.0] * 60, maxlen=60)
        self.history_temp = deque([0.0] * 60, maxlen=60)

        self.processes: List[Dict[str, Any]] = []

    def poll_once(self) -> None:
        serial = self.active_serial
        if not serial or self.paused:
            return

        cmd_str = "top -b -n 1 -m 45; echo '===BAT==='; dumpsys battery | grep -E 'level:|temperature:'"
        code, out, _ = self.adb.run_adb(["shell", cmd_str], serial=serial, timeout=5.0)
        if code != 0 or not out:
            return

        parts = out.split("===BAT===")
        top_raw = parts[0]
        bat_raw = parts[1] if len(parts) > 1 else ""

        tasks_tot, tasks_run = 0, 0
        mem_tot, mem_used = 1.0, 0.0
        swap_tot, swap_used = 1.0, 0.0
        cpu_pct = 0.0
        proc_list: List[Dict[str, Any]] = []

        lines = top_raw.splitlines()
        in_table = False

        for line in lines:
            s = line.strip()
            if not s:
                continue
            if s.startswith("Tasks:"):
                m_t = re.search(r"(\d+)\s+total,\s+(\d+)\s+running", s)
                if m_t:
                    tasks_tot = int(m_t.group(1))
                    tasks_run = int(m_t.group(2))
            elif s.startswith("Mem:"):
                m_m = re.search(r"(\d+)([KMG]?)\s+total,\s+(\d+)([KMG]?)\s+used", s)
                if m_m:
                    mem_tot = self._to_mb(int(m_m.group(1)), m_m.group(2))
                    mem_used = self._to_mb(int(m_m.group(3)), m_m.group(4))
            elif s.startswith("Swap:"):
                m_s = re.search(r"(\d+)([KMG]?)\s+total,\s+(\d+)([KMG]?)\s+used", s)
                if m_s:
                    swap_tot = self._to_mb(int(m_s.group(1)), m_s.group(2))
                    swap_used = self._to_mb(int(m_s.group(3)), m_s.group(4))
            elif "%cpu" in s and "%idle" in s:
                m_c = re.search(r"(\d+)%cpu.*?(\d+)%idle", s)
                if m_c:
                    total_cap = max(float(m_c.group(1)), 100.0)
                    idle_cap = float(m_c.group(2))
                    cpu_pct = max(0.0, min(100.0, ((total_cap - idle_cap) / total_cap) * 100.0))
            elif s.startswith("PID ") and "ARGS" in s:
                in_table = True
            elif in_table:
                tokens = s.split(None, 11)
                if len(tokens) >= 12 and tokens[0].isdigit():
                    pid = int(tokens[0])
                    user = tokens[1]
                    res_str = tokens[5]
                    state = tokens[7]
                    try:
                        p_cpu = float(tokens[8])
                    except ValueError:
                        p_cpu = 0.0
                    try:
                        p_mem = float(tokens[9])
                    except ValueError:
                        p_mem = 0.0
                    time_str = tokens[10]
                    args_str = tokens[11].strip()
                    if args_str.startswith("top -b"):
                        continue
                    proc_list.append(
                        {
                            "pid": pid,
                            "user": user,
                            "res": res_str,
                            "state": state,
                            "cpu": p_cpu,
                            "mem": p_mem,
                            "time": time_str,
                            "name": args_str,
                        }
                    )

        bat_lvl = 0
        bat_temp = 0.0
        m_bl = re.search(r"level:\s*(\d+)", bat_raw)
        m_bt = re.search(r"temperature:\s*(\d+)", bat_raw)
        if m_bl:
            bat_lvl = int(m_bl.group(1))
        if m_bt:
            bat_temp = int(m_bt.group(1)) / 10.0

        ram_percentage = (mem_used / max(mem_tot, 1.0)) * 100.0

        with self.lock:
            self.tasks_total = tasks_tot
            self.tasks_running = tasks_run
            self.ram_total_mb = mem_tot
            self.ram_used_mb = mem_used
            self.ram_pct = ram_percentage
            self.swap_total_mb = swap_tot
            self.swap_used_mb = swap_used
            self.cpu_total_pct = cpu_pct
            self.battery_level = bat_lvl
            self.battery_temp_c = bat_temp
            self.processes = proc_list

            self.history_cpu.append(cpu_pct)
            self.history_ram.append(ram_percentage)
            self.history_temp.append(bat_temp)

    @staticmethod
    def _to_mb(val: int, unit: str) -> float:
        u = unit.upper()
        if u == "G":
            return val * 1024.0
        if u == "K":
            return val / 1024.0
        return float(val)

    def background_loop(self) -> None:
        while self.running:
            self.poll_once()
            time.sleep(2.0)


class AdbScrcpyStudioApp(ctk.CTk):
    """Flagship v3.0 Obsidian Glass Workstation for ADB, Task Manager, Scrcpy & PC DeX Mode."""

    def __init__(self) -> None:
        super().__init__()

        self.title(f"J.A.R.V.I.S. Android & Scrcpy DeX Studio — v{APP_VERSION}")
        self.geometry("1340x840")
        self.minsize(1160, 740)
        self.configure(fg_color=C_VOID)

        ico_candidate = os.path.join(get_bundle_dir(), "assets", "android_scrcpy_dex.ico")
        if os.name == "nt" and os.path.isfile(ico_candidate):
            try:
                self.iconbitmap(ico_candidate)
            except Exception:
                pass

        self.icons = ModernVectorIconFactory()
        self.adb = AdbController()
        self.monitor = SystemMonitorEngine(self.adb)
        self.current_serial: Optional[str] = None
        self.current_state: str = "disconnected"
        self.devices_cache: List[Dict[str, str]] = []
        self.packages_cache: List[str] = []
        self.last_device_info: Dict[str, str] = {}
        self._last_bus_sig: str = ""

        # Managed child processes & magnetic emulator side-toolbar
        self.scrcpy_mirror_proc: Optional[subprocess.Popen] = None
        self.scrcpy_dex_proc: Optional[subprocess.Popen] = None
        self.emulator_sidebar: Optional[ScrcpyEmulatorSideBar] = None
        self.parent_pid = os.getpid()
        self._rotation_state = 0

        # Smooth Animation State (60fps Lerp Engine)
        self.anim_phase: float = 0.0
        self.disp_cpu: float = 0.0
        self.target_cpu: float = 0.0
        self.disp_ram: float = 0.0
        self.target_ram: float = 0.0
        self.disp_temp: float = 0.0
        self.target_temp: float = 0.0

        self._configure_treeview_style()
        self._build_shell_layout()

        # Start telemetry daemon thread
        self.monitor_thread = threading.Thread(target=self.monitor.background_loop, daemon=True)
        self.monitor_thread.start()

        # Start parent-coupled lifecycle watchdog (Rule #6)
        self.watchdog_thread = threading.Thread(target=self._lifecycle_watchdog_loop, daemon=True)
        self.watchdog_thread.start()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Initial device discovery, autonomous authorization watchdog & 60fps animation loop
        self.refresh_devices()
        self.after(30, self._animation_tick_60fps)
        self.after(1500, self._periodic_table_sync)
        self.after(2500, self._auto_bus_auth_watchdog_loop)

    def _configure_treeview_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Studio.Treeview",
            background=C_CARD,
            foreground=C_TEXT_MAIN,
            fieldbackground=C_CARD,
            rowheight=34,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Studio.Treeview.Heading",
            background=C_SURFACE,
            foreground=C_ACCENT,
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            padding=(10, 7),
            relief="flat",
        )
        style.map(
            "Studio.Treeview",
            background=[("selected", C_PRIMARY)],
            foreground=[("selected", "#ffffff")],
        )

    # =========================================================================
    # FLAGSHIP 2-PANE WORKSTATION SHELL (LEFT NAVIGATION RAIL + MAIN STAGE)
    # =========================================================================
    def _build_shell_layout(self) -> None:
        # 1. Left Sidebar Navigation Rail
        self.sidebar = ctk.CTkFrame(
            self,
            fg_color=C_SIDEBAR,
            width=252,
            corner_radius=0,
            border_width=0,
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Brand Hero Card inside Sidebar
        brand_box = ctk.CTkFrame(
            self.sidebar,
            fg_color=C_CARD,
            corner_radius=14,
            border_width=1,
            border_color=C_BORDER,
        )
        brand_box.pack(fill="x", padx=14, pady=(16, 14))

        png_candidate = os.path.join(get_bundle_dir(), "assets", "android_scrcpy_dex.png")
        if os.path.isfile(png_candidate):
            try:
                pil_logo = Image.open(png_candidate)
                self.brand_logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(42, 42))
                ctk.CTkLabel(brand_box, text="", image=self.brand_logo_img).pack(side="left", padx=(12, 10), pady=12)
            except Exception:
                pass

        b_txt = ctk.CTkFrame(brand_box, fg_color="transparent")
        b_txt.pack(side="left", fill="both", expand=True, pady=10)
        ctk.CTkLabel(
            b_txt,
            text="J.A.R.V.I.S.",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=C_ACCENT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            b_txt,
            text=f"Android DeX Studio v{APP_VERSION}",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=C_TEXT_SUB,
        ).pack(anchor="w")

        # Navigation Section Title
        ctk.CTkLabel(
            self.sidebar,
            text="WORKSTATION MODULES",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=C_TEXT_MUTED,
        ).pack(anchor="w", padx=20, pady=(4, 6))

        self.nav_buttons: List[ctk.CTkButton] = []
        nav_defs = [
            ("  Scrcpy Mirror Studio", "mirror", 0),
            ("  PC DeX Workstation", "dex", 1),
            ("  System Task Manager", "cpu", 2),
            ("  APK Package Manager", "apps", 3),
            ("  Hardware Telemetry", "info", 4),
        ]

        for label, ic, idx in nav_defs:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                image=self.icons.get(ic, 20, (56, 189, 248, 255)),
                anchor="w",
                height=44,
                corner_radius=11,
                fg_color=C_PRIMARY if idx == 0 else "transparent",
                hover_color=C_SURFACE,
                text_color="#ffffff" if idx == 0 else C_TEXT_SUB,
                font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda i=idx: self._switch_view(i),
            )
            btn.pack(fill="x", padx=14, pady=4)
            self.nav_buttons.append(btn)

        # Sidebar Live Device Mini Telemetry Card
        self.side_tele_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=C_CARD,
            corner_radius=14,
            border_width=1,
            border_color=C_BORDER,
        )
        self.side_tele_card.pack(fill="x", padx=14, pady=(18, 8))

        st_head = ctk.CTkFrame(self.side_tele_card, fg_color="transparent")
        st_head.pack(fill="x", padx=12, pady=(10, 4))

        self.led_canvas = tk.Canvas(st_head, width=22, height=22, bg=C_CARD, highlightthickness=0)
        self.led_canvas.pack(side="left")

        self.lbl_side_status = ctk.CTkLabel(
            st_head,
            text="SCANNING BUS...",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C_ACCENT,
        )
        self.lbl_side_status.pack(side="left", padx=6)

        self.lbl_side_model = ctk.CTkLabel(
            self.side_tele_card,
            text="No Active Device",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C_TEXT_MAIN,
        )
        self.lbl_side_model.pack(anchor="w", padx=14, pady=(0, 2))

        self.lbl_side_specs = ctk.CTkLabel(
            self.side_tele_card,
            text="Android -- • Battery --%\nCPU: 0.0% • RAM: 0.0%",
            font=ctk.CTkFont(size=11),
            text_color=C_TEXT_SUB,
            justify="left",
        )
        self.lbl_side_specs.pack(anchor="w", padx=14, pady=(0, 12))

        # Wireless Quick Connect Card at Bottom of Sidebar
        wifi_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=C_CARD,
            corner_radius=14,
            border_width=1,
            border_color=C_BORDER,
        )
        wifi_card.pack(side="bottom", fill="x", padx=14, pady=14)

        ctk.CTkLabel(
            wifi_card,
            text="WIRELESS ADB BRIDGE",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=C_TEXT_MUTED,
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.wireless_entry = ctk.CTkEntry(
            wifi_card,
            placeholder_text="192.168.8.246:5555",
            height=32,
            fg_color=C_VOID,
            border_color=C_BORDER,
            font=ctk.CTkFont(size=12),
        )
        self.wireless_entry.pack(fill="x", padx=12, pady=(0, 6))

        w_btns = ctk.CTkFrame(wifi_card, fg_color="transparent")
        w_btns.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            w_btns,
            text="Pair IP",
            image=self.icons.get("wifi", 15, (255, 255, 255, 255)),
            height=30,
            corner_radius=8,
            fg_color=C_EMERALD,
            hover_color=C_EMERALD_HOV,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._connect_wireless_adb,
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(
            w_btns,
            text=":5555",
            width=58,
            height=30,
            corner_radius=8,
            fg_color=C_SURFACE,
            hover_color=C_SURFACE_HOVER,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._enable_tcpip_5555,
        ).pack(side="right")

        # 2. Right Main Stage Container
        self.main_stage = ctk.CTkFrame(self, fg_color=C_VOID, corner_radius=0)
        self.main_stage.pack(side="right", fill="both", expand=True)

        self._build_top_header_banner()
        self._build_views()
        self._build_status_footer()

    # =========================================================================
    # TOP DEVICE TELEMETRY HEADER BANNER
    # =========================================================================
    def _build_top_header_banner(self) -> None:
        self.top_bar = ctk.CTkFrame(
            self.main_stage,
            fg_color=C_CARD,
            corner_radius=14,
            border_width=1,
            border_color=C_BORDER,
            height=64,
        )
        self.top_bar.pack(fill="x", padx=16, pady=(16, 10))

        self.view_title_lbl = ctk.CTkLabel(
            self.top_bar,
            text="Scrcpy 4.0 Mirror & Magnetic Side-Toolbar Studio",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=C_TEXT_MAIN,
        )
        self.view_title_lbl.pack(side="left", padx=(18, 12), pady=14)

        # Right side: Device selector + Scan + Re-Trigger Auth buttons
        self.refresh_dev_btn = ctk.CTkButton(
            self.top_bar,
            text="Scan USB / LAN",
            image=self.icons.get("refresh", 17, (56, 189, 248, 255)),
            width=130,
            height=36,
            corner_radius=10,
            fg_color=C_SURFACE,
            hover_color=C_SURFACE_HOVER,
            border_width=1,
            border_color=C_BORDER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.refresh_devices,
        )
        self.refresh_dev_btn.pack(side="right", padx=(4, 16), pady=12)

        self.reauth_btn = ctk.CTkButton(
            self.top_bar,
            text="Auto-Auth",
            image=self.icons.get("bolt", 16, (255, 255, 255, 255)),
            width=108,
            height=36,
            corner_radius=10,
            fg_color=C_AMBER,
            hover_color=C_AMBER_HOV,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._manual_retrigger_auth,
        )
        self.reauth_btn.pack(side="right", padx=4, pady=12)

        self.device_combo = ctk.CTkOptionMenu(
            self.top_bar,
            values=["Scanning..."],
            command=self._on_device_selected,
            width=265,
            height=36,
            corner_radius=10,
            fg_color=C_SURFACE,
            button_color=C_PRIMARY,
            button_hover_color=C_PRIMARY_HOV,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.device_combo.pack(side="right", padx=6, pady=12)

        ctk.CTkLabel(
            self.top_bar,
            text="ACTIVE TARGET:",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=C_TEXT_MUTED,
        ).pack(side="right", padx=(8, 4))

    def _build_views(self) -> None:
        self.view_host = ctk.CTkFrame(
            self.main_stage,
            fg_color="transparent",
            corner_radius=0,
        )
        self.view_host.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        self.views: List[ctk.CTkFrame] = []
        for _ in range(5):
            f = ctk.CTkFrame(self.view_host, fg_color="transparent")
            self.views.append(f)

        self.tab_mirror = self.views[0]
        self.tab_dex = self.views[1]
        self.tab_monitor = self.views[2]
        self.tab_apps = self.views[3]
        self.tab_info = self.views[4]

        self._init_tab_scrcpy_mirror()
        self._init_tab_dex_desktop()
        self._init_tab_system_monitor()
        self._init_tab_app_manager()
        self._init_tab_device_info()

        self.active_view_idx = 0
        self.views[0].pack(fill="both", expand=True)

    def _switch_view(self, index: int) -> None:
        if index == self.active_view_idx:
            return
        self.views[self.active_view_idx].pack_forget()
        self.active_view_idx = index
        self.views[index].pack(fill="both", expand=True)

        titles = [
            "Scrcpy 4.0 Mirror & Magnetic Side-Toolbar Studio",
            "PC as Samsung DeX / Android Desktop Workstation",
            "Live Android System Monitor & Process Task Manager",
            "APK Package Manager & Multi-App Batch Installer",
            "Complete Device Hardware, SoC & Thermal Telemetry",
        ]
        self.view_title_lbl.configure(text=titles[index])

        for idx, btn in enumerate(self.nav_buttons):
            if idx == index:
                btn.configure(fg_color=C_PRIMARY, text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color=C_TEXT_SUB)

    # =========================================================================
    # 60FPS SMOOTH ANIMATION & 4X SUPERSAMPLED PILLOW GAUGE RENDERER
    # =========================================================================
    def _animation_tick_60fps(self) -> None:
        self.anim_phase += 0.12

        # Breathing Status LED in Sidebar
        self.led_canvas.delete("all")
        pulse = (math.sin(self.anim_phase) + 1.0) * 0.5
        if not self.current_serial:
            base_col, halo_col = C_CRIMSON, "#4c0519"
        elif self.current_state in ("unauthorized", "offline"):
            base_col, halo_col = C_AMBER, "#451a03"
        else:
            base_col, halo_col = C_EMERALD, "#064e3b"
        r_outer = 6 + pulse * 3.5
        self.led_canvas.create_oval(11 - r_outer, 11 - r_outer, 11 + r_outer, 11 + r_outer, fill=halo_col, outline="")
        self.led_canvas.create_oval(7, 7, 15, 15, fill=base_col, outline="#ffffff", width=1)

        with self.monitor.lock:
            self.target_cpu = self.monitor.cpu_total_pct
            self.target_ram = self.monitor.ram_pct
            self.target_temp = self.monitor.battery_temp_c
            bat_lvl = self.monitor.battery_level

        self.disp_cpu += (self.target_cpu - self.disp_cpu) * 0.2
        self.disp_ram += (self.target_ram - self.disp_ram) * 0.2
        self.disp_temp += (self.target_temp - self.disp_temp) * 0.2

        # Update Sidebar Mini Telemetry Summary
        if self.current_serial and self.current_state == "device":
            ver = self.last_device_info.get("Android Version", "--")
            self.lbl_side_specs.configure(
                text=f"Android {ver}  •  Battery {bat_lvl}%\nCPU: {self.disp_cpu:.1f}%  •  RAM: {self.disp_ram:.1f}%"
            )

        # Render 4x Supersampled Anti-Aliased Radial Gauges when Monitor Tab is Active
        if self.active_view_idx == 2:
            img_cpu = self.icons.render_smooth_gauge(76, self.disp_cpu, 100.0, (56, 189, 248), (2, 132, 199))
            img_ram = self.icons.render_smooth_gauge(76, self.disp_ram, 100.0, (168, 85, 247), (126, 34, 206))
            img_tmp = self.icons.render_smooth_gauge(76, self.disp_temp, 60.0, (16, 185, 129), (5, 150, 105))
            self.lbl_gauge_cpu.configure(image=img_cpu, text=f"{self.disp_cpu:.0f}%")
            self.lbl_gauge_ram.configure(image=img_ram, text=f"{self.disp_ram:.0f}%")
            self.lbl_gauge_temp.configure(image=img_tmp, text=f"{self.disp_temp:.0f}°")

        self.after(30, self._animation_tick_60fps)

    # -------------------------------------------------------------------------
    # TAB 1: SCRCPY MIRROR & MAGNETIC SIDE-TOOLBAR CONFIGURATION
    # -------------------------------------------------------------------------
    def _init_tab_scrcpy_mirror(self) -> None:
        container = ctk.CTkFrame(self.tab_mirror, fg_color="transparent")
        container.pack(fill="both", expand=True)

        # Left Card: Stream Profiles & Parameters
        left_panel = ctk.CTkFrame(
            container, fg_color=C_CARD, corner_radius=14, border_width=1, border_color=C_BORDER
        )
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # 1-Click Quick Profile Presets Bar
        preset_bar = ctk.CTkFrame(left_panel, fg_color=C_SURFACE, corner_radius=11)
        preset_bar.pack(fill="x", padx=18, pady=(16, 12))

        ctk.CTkLabel(
            preset_bar,
            text="⚡ QUICK STREAM PRESETS:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C_ACCENT,
        ).pack(side="left", padx=(14, 10), pady=10)

        presets = [
            ("Ultra Low-Latency (120Hz)", "1080 (FHD)", "12M", "120", "h264"),
            ("Cinema 2K Studio (35M)", "2560 (QHD+)", "35M", "60", "h265"),
            ("Esports 240Hz Max", "1080 (FHD)", "24M", "240", "h264"),
            ("Wi-Fi Saver (720p)", "1280 (720p)", "4M", "60", "h264"),
        ]
        for p_name, p_res, p_bit, p_fps, p_cod in presets:
            ctk.CTkButton(
                preset_bar,
                text=p_name,
                height=28,
                corner_radius=7,
                fg_color=C_CARD,
                hover_color=C_PRIMARY,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda r=p_res, b=p_bit, f=p_fps, c=p_cod: self._apply_mirror_preset(r, b, f, c),
            ).pack(side="left", padx=4, pady=8)

        # Two-Column Parameter Grid
        grid = ctk.CTkFrame(left_panel, fg_color="transparent")
        grid.pack(fill="x", padx=18, pady=4)
        grid.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(grid, text="Max Resolution:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXT_SUB).grid(
            row=0, column=0, sticky="w", pady=8, padx=(0, 10)
        )
        self.mirror_res_var = ctk.StringVar(value="1080 (FHD)")
        ctk.CTkOptionMenu(
            grid,
            variable=self.mirror_res_var,
            values=["Native (Uncapped)", "2560 (QHD+)", "1920 (FHD+)", "1600 (HD+)", "1280 (720p)", "1080 (FHD)", "800 (Low Latency)"],
            fg_color=C_SURFACE,
            height=34,
            corner_radius=8,
        ).grid(row=0, column=1, sticky="ew", pady=8, padx=(0, 16))

        ctk.CTkLabel(grid, text="Video Bitrate:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXT_SUB).grid(
            row=0, column=2, sticky="w", pady=8, padx=(0, 10)
        )
        self.mirror_vbit_var = ctk.StringVar(value="12M")
        ctk.CTkOptionMenu(
            grid,
            variable=self.mirror_vbit_var,
            values=["2M", "4M", "8M", "12M", "16M", "24M", "35M", "50M (Ultra HQ)"],
            fg_color=C_SURFACE,
            height=34,
            corner_radius=8,
        ).grid(row=0, column=3, sticky="ew", pady=8)

        ctk.CTkLabel(grid, text="Target Frame Rate:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXT_SUB).grid(
            row=1, column=0, sticky="w", pady=8, padx=(0, 10)
        )
        self.mirror_fps_var = ctk.StringVar(value="60")
        ctk.CTkOptionMenu(
            grid,
            variable=self.mirror_fps_var,
            values=["30", "60", "90", "120", "144", "240"],
            fg_color=C_SURFACE,
            height=34,
            corner_radius=8,
        ).grid(row=1, column=1, sticky="ew", pady=8, padx=(0, 16))

        ctk.CTkLabel(grid, text="Video Hardware Codec:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXT_SUB).grid(
            row=1, column=2, sticky="w", pady=8, padx=(0, 10)
        )
        self.mirror_vcodec_var = ctk.StringVar(value="h264")
        ctk.CTkOptionMenu(
            grid,
            variable=self.mirror_vcodec_var,
            values=["h264", "h265", "av1"],
            fg_color=C_SURFACE,
            height=34,
            corner_radius=8,
        ).grid(row=1, column=3, sticky="ew", pady=8)

        ctk.CTkLabel(grid, text="Audio Bitrate:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXT_SUB).grid(
            row=2, column=0, sticky="w", pady=8, padx=(0, 10)
        )
        self.mirror_abit_var = ctk.StringVar(value="128K")
        ctk.CTkOptionMenu(
            grid,
            variable=self.mirror_abit_var,
            values=["64K", "96K", "128K", "192K", "256K", "320K (Studio)"],
            fg_color=C_SURFACE,
            height=34,
            corner_radius=8,
        ).grid(row=2, column=1, sticky="ew", pady=8, padx=(0, 16))

        ctk.CTkLabel(grid, text="Audio Codec:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXT_SUB).grid(
            row=2, column=2, sticky="w", pady=8, padx=(0, 10)
        )
        self.mirror_acodec_var = ctk.StringVar(value="opus")
        ctk.CTkOptionMenu(
            grid,
            variable=self.mirror_acodec_var,
            values=["opus", "aac", "flac", "raw"],
            fg_color=C_SURFACE,
            height=34,
            corner_radius=8,
        ).grid(row=2, column=3, sticky="ew", pady=8)

        # Hardware Behavior Toggles Card
        toggles_frame = ctk.CTkFrame(
            left_panel, fg_color=C_VOID, corner_radius=12, border_width=1, border_color=C_BORDER
        )
        toggles_frame.pack(fill="x", padx=18, pady=14)

        self.mirror_attach_sidebar = ctk.CTkSwitch(
            toggles_frame,
            text="Attach Magnetic Android Emulator Navigation Side-Toolbar Alongside Mirrored Display",
            progress_color=C_PRIMARY,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_ACCENT,
        )
        self.mirror_attach_sidebar.select()
        self.mirror_attach_sidebar.pack(anchor="w", padx=16, pady=(12, 6))

        self.mirror_turn_screen_off = ctk.CTkSwitch(
            toggles_frame,
            text="Turn Physical Phone OLED Screen Off While Mirroring (-S)",
            progress_color=C_PRIMARY,
        )
        self.mirror_turn_screen_off.pack(anchor="w", padx=16, pady=6)

        self.mirror_stay_awake = ctk.CTkSwitch(
            toggles_frame,
            text="Keep Device Awake While Plugged In (-w)",
            progress_color=C_PRIMARY,
        )
        self.mirror_stay_awake.select()
        self.mirror_stay_awake.pack(anchor="w", padx=16, pady=6)

        self.mirror_always_top = ctk.CTkSwitch(
            toggles_frame,
            text="Always on Top Mirror Window (--always-on-top)",
            progress_color=C_PRIMARY,
        )
        self.mirror_always_top.pack(anchor="w", padx=16, pady=6)

        self.mirror_no_audio = ctk.CTkSwitch(
            toggles_frame,
            text="Mute / Disable Audio Forwarding (--no-audio)",
            progress_color=C_PRIMARY,
        )
        self.mirror_no_audio.pack(anchor="w", padx=16, pady=6)

        self.mirror_show_touches = ctk.CTkSwitch(
            toggles_frame,
            text="Show Physical Finger Touches (-t)",
            progress_color=C_PRIMARY,
        )
        self.mirror_show_touches.pack(anchor="w", padx=16, pady=(6, 12))

        # Action Launch Buttons
        btn_row = ctk.CTkFrame(left_panel, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=(8, 16))

        self.launch_mirror_btn = ctk.CTkButton(
            btn_row,
            text="  LAUNCH SCRCPY MIRROR + SIDE-TOOLBAR",
            image=self.icons.get("play", 20, (255, 255, 255, 255)),
            height=48,
            corner_radius=12,
            fg_color=C_PRIMARY,
            hover_color=C_PRIMARY_HOV,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.start_scrcpy_mirror,
        )
        self.launch_mirror_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.stop_mirror_btn = ctk.CTkButton(
            btn_row,
            text="  STOP MIRROR",
            image=self.icons.get("stop", 18, (255, 255, 255, 255)),
            height=48,
            width=165,
            corner_radius=12,
            fg_color=C_CRIMSON,
            hover_color=C_CRIMSON_HOV,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.stop_scrcpy_mirror,
        )
        self.stop_mirror_btn.pack(side="left")

        # Right Column: Side-Toolbar Preview & Direct Utilities
        right_panel = ctk.CTkFrame(
            container, fg_color=C_CARD, corner_radius=14, border_width=1, border_color=C_BORDER, width=325
        )
        right_panel.pack(side="right", fill="y", padx=(8, 0))
        right_panel.pack_propagate(False)

        ctk.CTkLabel(
            right_panel,
            text="Magnetic Emulator Dock",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=C_ACCENT,
        ).pack(anchor="w", padx=18, pady=(16, 4))

        side_info = (
            "Automatically attaches flush alongside\n"
            "the right edge of the Scrcpy window:\n\n"
            "• ⏻  Power / Lock Screen\n"
            "• 🔊  Volume + / - / Mute\n"
            "• 🔄  Rotate Orientation (90° step)\n"
            "• 📸  Instant PNG Screenshot\n"
            "• 🔔  Expand Notifications Shade\n"
            "• ◀  BACK   • ● HOME   • ■ RECENT\n\n"
            "Tracks window movement at 30fps.\n"
            "Double-click the top ⋮⋮ grip to re-snap."
        )
        ctk.CTkLabel(
            right_panel,
            text=side_info,
            font=ctk.CTkFont(size=12),
            text_color=C_TEXT_SUB,
            justify="left",
        ).pack(anchor="w", padx=18, pady=6)

        txt_box = ctk.CTkFrame(right_panel, fg_color=C_VOID, corner_radius=12, border_width=1, border_color=C_BORDER)
        txt_box.pack(fill="x", padx=16, pady=(14, 10))

        ctk.CTkLabel(
            txt_box,
            text="KEYBOARD TEXT INJECTION",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=C_TEXT_MUTED,
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.inject_text_entry = ctk.CTkEntry(
            txt_box,
            placeholder_text="Paste or type text to send...",
            height=34,
            fg_color=C_CARD,
            border_color=C_BORDER,
        )
        self.inject_text_entry.pack(fill="x", padx=12, pady=4)

        ctk.CTkButton(
            txt_box,
            text="Send Text to Phone",
            height=34,
            corner_radius=8,
            fg_color=C_EMERALD,
            hover_color=C_EMERALD_HOV,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._send_text_to_device,
        ).pack(fill="x", padx=12, pady=(4, 12))

    def _apply_mirror_preset(self, res: str, vbit: str, fps: str, codec: str) -> None:
        self.mirror_res_var.set(res)
        self.mirror_vbit_var.set(vbit)
        self.mirror_fps_var.set(fps)
        self.mirror_vcodec_var.set(codec)
        self.set_status(f"Applied Stream Preset: {res} @ {fps} FPS ({vbit} {codec.upper()})", C_ACCENT)

    # -------------------------------------------------------------------------
    # TAB 2: PC DEX / DESKTOP WORKSTATION MODE
    # -------------------------------------------------------------------------
    def _init_tab_dex_desktop(self) -> None:
        container = ctk.CTkFrame(self.tab_dex, fg_color="transparent")
        container.pack(fill="both", expand=True)

        left_card = ctk.CTkFrame(
            container, fg_color=C_CARD, corner_radius=14, border_width=1, border_color=C_BORDER
        )
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # 1-Click DeX Workstation Display Presets
        dex_preset_bar = ctk.CTkFrame(left_card, fg_color=C_SURFACE, corner_radius=11)
        dex_preset_bar.pack(fill="x", padx=18, pady=(16, 12))

        ctk.CTkLabel(
            dex_preset_bar,
            text="🖥️ DEX MONITOR PRESETS:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C_ACCENT,
        ).pack(side="left", padx=(14, 10), pady=10)

        dex_presets = [
            ("1080p 60Hz Standard", "1920x1080", "160 (Desktop Native)", "60", "20M"),
            ("1440p 120Hz QHD Pro", "2560x1440", "200 (Balanced Desktop)", "120", "35M"),
            ("4K UHD Studio", "3840x2160", "240 (Large Desktop / Tablet)", "60", "50M"),
            ("Ultrawide 21:9", "2560x1080 (Ultrawide)", "160 (Desktop Native)", "120", "30M"),
        ]
        for d_name, d_res, d_dpi, d_fps, d_bit in dex_presets:
            ctk.CTkButton(
                dex_preset_bar,
                text=d_name,
                height=28,
                corner_radius=7,
                fg_color=C_CARD,
                hover_color=C_PRIMARY,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda r=d_res, dp=d_dpi, f=d_fps, b=d_bit: self._apply_dex_preset(r, dp, f, b),
            ).pack(side="left", padx=4, pady=8)

        form = ctk.CTkFrame(left_card, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=4)
        form.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(form, text="Virtual Display Size:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXT_SUB).grid(
            row=0, column=0, sticky="w", pady=8, padx=(0, 10)
        )
        self.dex_res_var = ctk.StringVar(value="1920x1080")
        ctk.CTkOptionMenu(
            form,
            variable=self.dex_res_var,
            values=["1920x1080", "2560x1440", "3840x2160", "1600x900", "1366x768", "2560x1080 (Ultrawide)"],
            fg_color=C_SURFACE,
            height=34,
            corner_radius=8,
        ).grid(row=0, column=1, sticky="ew", pady=8, padx=(0, 16))

        ctk.CTkLabel(form, text="Desktop UI Density:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXT_SUB).grid(
            row=0, column=2, sticky="w", pady=8, padx=(0, 10)
        )
        self.dex_dpi_var = ctk.StringVar(value="160 (Desktop Native)")
        ctk.CTkOptionMenu(
            form,
            variable=self.dex_dpi_var,
            values=[
                "120 (Ultra Compact Desktop)",
                "140 (Compact Desktop)",
                "160 (Desktop Native)",
                "200 (Balanced Desktop)",
                "240 (Large Desktop / Tablet)",
                "320 (High DPI)",
            ],
            fg_color=C_SURFACE,
            height=34,
            corner_radius=8,
        ).grid(row=0, column=3, sticky="ew", pady=8)

        ctk.CTkLabel(form, text="Refresh Rate (FPS):", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXT_SUB).grid(
            row=1, column=0, sticky="w", pady=8, padx=(0, 10)
        )
        self.dex_fps_var = ctk.StringVar(value="60")
        ctk.CTkOptionMenu(
            form,
            variable=self.dex_fps_var,
            values=["60", "90", "120", "144", "240"],
            fg_color=C_SURFACE,
            height=34,
            corner_radius=8,
        ).grid(row=1, column=1, sticky="ew", pady=8, padx=(0, 16))

        ctk.CTkLabel(form, text="Desktop Bitrate:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXT_SUB).grid(
            row=1, column=2, sticky="w", pady=8, padx=(0, 10)
        )
        self.dex_vbit_var = ctk.StringVar(value="20M")
        ctk.CTkOptionMenu(
            form,
            variable=self.dex_vbit_var,
            values=["12M", "16M", "20M", "30M", "35M", "50M", "60M"],
            fg_color=C_SURFACE,
            height=34,
            corner_radius=8,
        ).grid(row=1, column=3, sticky="ew", pady=8)

        ctk.CTkLabel(form, text="Auto-Launch Package:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXT_SUB).grid(
            row=2, column=0, sticky="w", pady=8, padx=(0, 10)
        )
        self.dex_start_app_entry = ctk.CTkEntry(
            form,
            placeholder_text="Optional: Leave blank for Desktop Launcher, or e.g. com.android.chrome",
            height=34,
            fg_color=C_VOID,
            border_color=C_BORDER,
        )
        self.dex_start_app_entry.grid(row=2, column=1, columnspan=3, sticky="ew", pady=8)

        dex_flags = ctk.CTkFrame(
            left_card, fg_color=C_VOID, corner_radius=12, border_width=1, border_color=C_BORDER
        )
        dex_flags.pack(fill="x", padx=18, pady=14)

        self.dex_force_settings = ctk.CTkSwitch(
            dex_flags,
            text="Enable Android Global Desktop Mode & Freeform Multi-Window Flags (force_desktop_mode_on_external_displays)",
            progress_color=C_PRIMARY,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_ACCENT,
        )
        self.dex_force_settings.select()
        self.dex_force_settings.pack(anchor="w", padx=16, pady=(12, 6))

        self.dex_keep_content = ctk.CTkSwitch(
            dex_flags,
            text="Preserve Running Apps on Main Screen When Closing Desktop Session (--no-vd-destroy-content)",
            progress_color=C_PRIMARY,
        )
        self.dex_keep_content.select()
        self.dex_keep_content.pack(anchor="w", padx=16, pady=6)

        self.dex_fullscreen = ctk.CTkSwitch(
            dex_flags,
            text="Launch PC Desktop Session in Fullscreen Monitor Mode (--fullscreen)",
            progress_color=C_PRIMARY,
        )
        self.dex_fullscreen.pack(anchor="w", padx=16, pady=(6, 12))

        dex_btns = ctk.CTkFrame(left_card, fg_color="transparent")
        dex_btns.pack(fill="x", padx=18, pady=(8, 16))

        ctk.CTkButton(
            dex_btns,
            text="  LAUNCH PC DEX / DESKTOP WORKSTATION",
            image=self.icons.get("dex", 20, (255, 255, 255, 255)),
            height=48,
            corner_radius=12,
            fg_color=C_PRIMARY,
            hover_color=C_PRIMARY_HOV,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.start_dex_desktop_mode,
        ).pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            dex_btns,
            text="  STOP DESKTOP",
            image=self.icons.get("stop", 18, (255, 255, 255, 255)),
            height=48,
            width=165,
            corner_radius=12,
            fg_color=C_CRIMSON,
            hover_color=C_CRIMSON_HOV,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.stop_dex_desktop_mode,
        ).pack(side="left")

        right_card = ctk.CTkFrame(
            container, fg_color=C_CARD, corner_radius=14, border_width=1, border_color=C_BORDER, width=325
        )
        right_card.pack(side="right", fill="y", padx=(8, 0))
        right_card.pack_propagate(False)

        ctk.CTkLabel(
            right_card,
            text="DeX & Freeform Engine",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=C_ACCENT,
        ).pack(anchor="w", padx=18, pady=(16, 6))

        info_text = (
            "Creates an independent virtual display\n"
            "while your phone screen stays separate:\n\n"
            "• Pixel 8 / 9 Desktop Taskbar Mode\n"
            "• Samsung Galaxy DeX Virtual Display\n"
            "• Motorola Ready For / Smart Connect\n"
            "• Xiaomi / OnePlus Freeform Windows"
        )
        ctk.CTkLabel(
            right_card,
            text=info_text,
            font=ctk.CTkFont(size=12),
            text_color=C_TEXT_SUB,
            justify="left",
        ).pack(anchor="w", padx=18, pady=4)

        ctk.CTkButton(
            right_card,
            text="Apply Android Desktop Flags Now",
            height=36,
            corner_radius=9,
            fg_color=C_EMERALD,
            hover_color=C_EMERALD_HOV,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._set_android_desktop_flags(True),
        ).pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkButton(
            right_card,
            text="Reset Desktop Flags to Default",
            height=36,
            corner_radius=9,
            fg_color=C_SURFACE,
            hover_color=C_SURFACE_HOVER,
            font=ctk.CTkFont(size=12),
            command=lambda: self._set_android_desktop_flags(False),
        ).pack(fill="x", padx=16, pady=4)

        self.dex_status_box = ctk.CTkTextbox(
            right_card,
            height=210,
            fg_color=C_VOID,
            text_color=C_ACCENT,
            border_width=1,
            border_color=C_BORDER,
            corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=11),
        )
        self.dex_status_box.pack(fill="both", expand=True, padx=16, pady=(10, 16))
        self._log_dex("Ready to spawn Virtual External Desktop Display.")

    def _apply_dex_preset(self, res: str, dpi: str, fps: str, vbit: str) -> None:
        self.dex_res_var.set(res)
        self.dex_dpi_var.set(dpi)
        self.dex_fps_var.set(fps)
        self.dex_vbit_var.set(vbit)
        self._log_dex(f"Preset applied: {res} @ {dpi.split()[0]} DPI ({fps} FPS, {vbit})")

    # -------------------------------------------------------------------------
    # TAB 3: LIVE SYSTEM MONITOR & TASK MANAGER (4X SUPERSAMPLED GAUGES)
    # -------------------------------------------------------------------------
    def _init_tab_system_monitor(self) -> None:
        cards_row = ctk.CTkFrame(self.tab_monitor, fg_color="transparent")
        cards_row.pack(fill="x", pady=(0, 8))
        cards_row.grid_columnconfigure((0, 1, 2), weight=1)

        # Card 1: CPU Load
        cpu_card = ctk.CTkFrame(cards_row, fg_color=C_CARD, corner_radius=14, border_width=1, border_color=C_BORDER)
        cpu_card.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        top_c1 = ctk.CTkFrame(cpu_card, fg_color="transparent")
        top_c1.pack(fill="x", padx=12, pady=(8, 0))
        self.lbl_gauge_cpu = ctk.CTkLabel(
            top_c1,
            text="0%",
            image=self.icons.render_smooth_gauge(76, 0, 100, (56, 189, 248), (2, 132, 199)),
            compound="center",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_TEXT_MAIN,
        )
        self.lbl_gauge_cpu.pack(side="left", padx=(2, 10))
        c1_txt = ctk.CTkFrame(top_c1, fg_color="transparent")
        c1_txt.pack(side="left", fill="both", expand=True, pady=12)
        self.lbl_cpu_val = ctk.CTkLabel(
            c1_txt, text="CPU Load: 0.0%", font=ctk.CTkFont(size=14, weight="bold"), text_color=C_ACCENT
        )
        self.lbl_cpu_val.pack(anchor="w")
        self.lbl_tasks_val = ctk.CTkLabel(
            c1_txt, text="Tasks: 0 Total (0 Running)", font=ctk.CTkFont(size=11), text_color=C_TEXT_SUB
        )
        self.lbl_tasks_val.pack(anchor="w")
        self.canvas_cpu = tk.Canvas(cpu_card, height=48, bg=C_VOID, highlightthickness=0)
        self.canvas_cpu.pack(fill="x", padx=12, pady=(2, 10))

        # Card 2: RAM & ZRAM Swap
        ram_card = ctk.CTkFrame(cards_row, fg_color=C_CARD, corner_radius=14, border_width=1, border_color=C_BORDER)
        ram_card.grid(row=0, column=1, sticky="ew", padx=6)
        top_c2 = ctk.CTkFrame(ram_card, fg_color="transparent")
        top_c2.pack(fill="x", padx=12, pady=(8, 0))
        self.lbl_gauge_ram = ctk.CTkLabel(
            top_c2,
            text="0%",
            image=self.icons.render_smooth_gauge(76, 0, 100, (168, 85, 247), (126, 34, 206)),
            compound="center",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_TEXT_MAIN,
        )
        self.lbl_gauge_ram.pack(side="left", padx=(2, 10))
        c2_txt = ctk.CTkFrame(top_c2, fg_color="transparent")
        c2_txt.pack(side="left", fill="both", expand=True, pady=12)
        self.lbl_ram_val = ctk.CTkLabel(
            c2_txt, text="RAM: 0 / 0 MB (0%)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#c084fc"
        )
        self.lbl_ram_val.pack(anchor="w")
        self.lbl_swap_val = ctk.CTkLabel(
            c2_txt, text="ZRAM Swap: 0 / 0 MB", font=ctk.CTkFont(size=11), text_color=C_TEXT_SUB
        )
        self.lbl_swap_val.pack(anchor="w")
        self.canvas_ram = tk.Canvas(ram_card, height=48, bg=C_VOID, highlightthickness=0)
        self.canvas_ram.pack(fill="x", padx=12, pady=(2, 10))

        # Card 3: Battery & Thermal
        bat_card = ctk.CTkFrame(cards_row, fg_color=C_CARD, corner_radius=14, border_width=1, border_color=C_BORDER)
        bat_card.grid(row=0, column=2, sticky="ew", padx=(6, 0))
        top_c3 = ctk.CTkFrame(bat_card, fg_color="transparent")
        top_c3.pack(fill="x", padx=12, pady=(8, 0))
        self.lbl_gauge_temp = ctk.CTkLabel(
            top_c3,
            text="0°",
            image=self.icons.render_smooth_gauge(76, 0, 60, (16, 185, 129), (5, 150, 105)),
            compound="center",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_TEXT_MAIN,
        )
        self.lbl_gauge_temp.pack(side="left", padx=(2, 10))
        c3_txt = ctk.CTkFrame(top_c3, fg_color="transparent")
        c3_txt.pack(side="left", fill="both", expand=True, pady=12)
        self.lbl_bat_val = ctk.CTkLabel(
            c3_txt, text="Battery: --% • -- °C", font=ctk.CTkFont(size=14, weight="bold"), text_color=C_EMERALD
        )
        self.lbl_bat_val.pack(anchor="w")
        self.lbl_mon_state = ctk.CTkLabel(
            c3_txt, text="Live Telemetry: Active (2.0s)", font=ctk.CTkFont(size=11), text_color=C_TEXT_SUB
        )
        self.lbl_mon_state.pack(anchor="w")
        self.canvas_temp = tk.Canvas(bat_card, height=48, bg=C_VOID, highlightthickness=0)
        self.canvas_temp.pack(fill="x", padx=12, pady=(2, 10))

        # Action Toolbar for Task Manager
        tm_bar = ctk.CTkFrame(self.tab_monitor, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        tm_bar.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            tm_bar,
            text="Filter Process / Package:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_TEXT_SUB,
        ).pack(side="left", padx=(16, 8), pady=10)

        self.proc_filter_var = ctk.StringVar(value="")
        self.proc_filter_entry = ctk.CTkEntry(
            tm_bar,
            textvariable=self.proc_filter_var,
            placeholder_text="Search PID, user, or package (e.g. com.android, system_server)...",
            width=290,
            height=34,
            fg_color=C_VOID,
            border_color=C_BORDER,
        )
        self.proc_filter_entry.pack(side="left", padx=4, pady=10)

        self.pause_mon_btn = ctk.CTkButton(
            tm_bar,
            text="Pause Live Poll",
            image=self.icons.get("stop", 15, (255, 255, 255, 255)),
            width=140,
            height=34,
            corner_radius=9,
            fg_color=C_SURFACE,
            hover_color=C_SURFACE_HOVER,
            command=self._toggle_monitor_pause,
        )
        self.pause_mon_btn.pack(side="left", padx=8, pady=10)

        ctk.CTkButton(
            tm_bar,
            text="Force-Stop Process",
            image=self.icons.get("stop", 15, (255, 255, 255, 255)),
            width=180,
            height=34,
            corner_radius=9,
            fg_color=C_CRIMSON,
            hover_color=C_CRIMSON_HOV,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._force_stop_selected_process,
        ).pack(side="right", padx=(6, 14), pady=10)

        ctk.CTkButton(
            tm_bar,
            text="Trim RAM Caches",
            image=self.icons.get("bolt", 16, (255, 255, 255, 255)),
            width=160,
            height=34,
            corner_radius=9,
            fg_color=C_PRIMARY,
            hover_color=C_PRIMARY_HOV,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._trim_device_memory,
        ).pack(side="right", padx=6, pady=10)

        table_frame = ctk.CTkFrame(
            self.tab_monitor, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER
        )
        table_frame.pack(fill="both", expand=True)

        cols = ("pid", "user", "cpu", "mem", "res", "state", "time", "name")
        self.proc_tree = ttk.Treeview(table_frame, columns=cols, show="headings", style="Studio.Treeview")
        self.proc_tree.tag_configure("odd", background="#0c1018")
        self.proc_tree.tag_configure("even", background="#101622")
        headings = [
            ("pid", "PID", 70, "center"),
            ("user", "USER", 100, "w"),
            ("cpu", "CPU %", 85, "e"),
            ("mem", "MEM %", 85, "e"),
            ("res", "RSS RAM", 95, "e"),
            ("state", "STATE", 65, "center"),
            ("time", "CPU TIME", 100, "e"),
            ("name", "PACKAGE / PROCESS IDENTIFIER", 440, "w"),
        ]
        for col_id, title_txt, width, anchor in headings:
            self.proc_tree.heading(col_id, text=title_txt)
            self.proc_tree.column(col_id, width=width, anchor=anchor)

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.proc_tree.yview)
        self.proc_tree.configure(yscrollcommand=scroll_y.set)
        self.proc_tree.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)
        scroll_y.pack(side="right", fill="y", pady=2)

    # -------------------------------------------------------------------------
    # TAB 4: APP MANAGER (MULTI-APK BATCH INSTALLER / LAUNCH / BACKUP)
    # -------------------------------------------------------------------------
    def _init_tab_app_manager(self) -> None:
        top_controls = ctk.CTkFrame(
            self.tab_apps, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER
        )
        top_controls.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            top_controls, text="Category:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXT_SUB
        ).pack(side="left", padx=(16, 6), pady=12)

        self.app_type_var = ctk.StringVar(value="User / 3rd-Party Apps (-3)")
        self.app_type_menu = ctk.CTkOptionMenu(
            top_controls,
            variable=self.app_type_var,
            values=["User / 3rd-Party Apps (-3)", "System Packages (-s)", "All Installed Packages"],
            command=lambda _: self.refresh_packages_list(),
            width=215,
            height=34,
            corner_radius=9,
            fg_color=C_SURFACE,
        )
        self.app_type_menu.pack(side="left", padx=6, pady=12)

        self.app_search_var = ctk.StringVar(value="")
        self.app_search_var.trace_add("write", lambda *_: self._filter_packages_tree())
        self.app_search_entry = ctk.CTkEntry(
            top_controls,
            textvariable=self.app_search_var,
            placeholder_text="Instant filter by package identifier...",
            width=265,
            height=34,
            fg_color=C_VOID,
            border_color=C_BORDER,
        )
        self.app_search_entry.pack(side="left", padx=8, pady=12)

        ctk.CTkButton(
            top_controls,
            text="Refresh List",
            image=self.icons.get("refresh", 16, (56, 189, 248, 255)),
            width=125,
            height=34,
            corner_radius=9,
            fg_color=C_SURFACE,
            hover_color=C_SURFACE_HOVER,
            command=self.refresh_packages_list,
        ).pack(side="left", padx=6, pady=12)

        ctk.CTkButton(
            top_controls,
            text="  Batch Install APK(s)...",
            image=self.icons.get("download", 18, (255, 255, 255, 255)),
            width=195,
            height=36,
            corner_radius=10,
            fg_color=C_PRIMARY,
            hover_color=C_PRIMARY_HOV,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._install_apk_dialog,
        ).pack(side="right", padx=14, pady=12)

        act_bar = ctk.CTkFrame(
            self.tab_apps, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER
        )
        act_bar.pack(fill="x", pady=(0, 8))

        self.lbl_pkg_count = ctk.CTkLabel(
            act_bar,
            text="Packages Loaded: 0",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_ACCENT,
        )
        self.lbl_pkg_count.pack(side="left", padx=16, pady=10)

        ctk.CTkButton(
            act_bar,
            text="Uninstall",
            image=self.icons.get("trash", 16, (255, 255, 255, 255)),
            width=125,
            height=34,
            corner_radius=9,
            fg_color=C_CRIMSON,
            hover_color=C_CRIMSON_HOV,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._uninstall_selected_package,
        ).pack(side="right", padx=(5, 14), pady=10)

        ctk.CTkButton(
            act_bar,
            text="Wipe Data",
            width=115,
            height=34,
            corner_radius=9,
            fg_color=C_AMBER,
            hover_color=C_AMBER_HOV,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._clear_selected_package_data,
        ).pack(side="right", padx=5, pady=10)

        ctk.CTkButton(
            act_bar,
            text="Force Stop",
            width=105,
            height=34,
            corner_radius=9,
            fg_color=C_SURFACE,
            hover_color=C_SURFACE_HOVER,
            command=self._force_stop_selected_package,
        ).pack(side="right", padx=5, pady=10)

        ctk.CTkButton(
            act_bar,
            text="Backup APK",
            image=self.icons.get("download", 16, (255, 255, 255, 255)),
            width=135,
            height=34,
            corner_radius=9,
            fg_color=C_EMERALD,
            hover_color=C_EMERALD_HOV,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._pull_selected_apk,
        ).pack(side="right", padx=5, pady=10)

        ctk.CTkButton(
            act_bar,
            text="Launch on Phone",
            image=self.icons.get("play", 16, (255, 255, 255, 255)),
            width=148,
            height=34,
            corner_radius=9,
            fg_color=C_PRIMARY,
            hover_color=C_PRIMARY_HOV,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._launch_selected_package,
        ).pack(side="right", padx=5, pady=10)

        ctk.CTkButton(
            act_bar,
            text="Launch in DeX",
            image=self.icons.get("dex", 16, (255, 255, 255, 255)),
            width=148,
            height=34,
            corner_radius=9,
            fg_color=C_VIOLET,
            hover_color=C_VIOLET_HOV,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._launch_selected_package_in_dex,
        ).pack(side="right", padx=5, pady=10)

        pkg_frame = ctk.CTkFrame(
            self.tab_apps, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER
        )
        pkg_frame.pack(fill="both", expand=True)

        self.pkg_tree = ttk.Treeview(
            pkg_frame,
            columns=("package", "type"),
            show="headings",
            style="Studio.Treeview",
        )
        self.pkg_tree.tag_configure("odd", background="#0c1018")
        self.pkg_tree.tag_configure("even", background="#101622")
        self.pkg_tree.heading("package", text="APPLICATION PACKAGE IDENTIFIER")
        self.pkg_tree.column("package", width=720, anchor="w")
        self.pkg_tree.heading("type", text="INSTALL SCOPE")
        self.pkg_tree.column("type", width=180, anchor="center")

        pkg_scroll = ttk.Scrollbar(pkg_frame, orient="vertical", command=self.pkg_tree.yview)
        self.pkg_tree.configure(yscrollcommand=pkg_scroll.set)
        self.pkg_tree.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)
        pkg_scroll.pack(side="right", fill="y", pady=2)

    # -------------------------------------------------------------------------
    # TAB 5: DEVICE HARDWARE & OS INFO
    # -------------------------------------------------------------------------
    def _init_tab_device_info(self) -> None:
        bar = ctk.CTkFrame(
            self.tab_info, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER
        )
        bar.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            bar,
            text="  Live SoC, Kernel, Display, Battery & Storage Specification Matrix",
            image=self.icons.get("info", 20, (56, 189, 248, 255)),
            compound="left",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C_ACCENT,
        ).pack(side="left", padx=16, pady=12)

        ctk.CTkButton(
            bar,
            text="Query Hardware",
            image=self.icons.get("refresh", 16, (255, 255, 255, 255)),
            width=165,
            height=34,
            corner_radius=9,
            fg_color=C_PRIMARY,
            hover_color=C_PRIMARY_HOV,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.refresh_device_info,
        ).pack(side="right", padx=14, pady=12)

        ctk.CTkButton(
            bar,
            text="Copy JSON Report",
            width=145,
            height=34,
            corner_radius=9,
            fg_color=C_SURFACE,
            hover_color=C_SURFACE_HOVER,
            command=self._copy_device_info_clipboard,
        ).pack(side="right", padx=6, pady=12)

        info_frame = ctk.CTkFrame(
            self.tab_info, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER
        )
        info_frame.pack(fill="both", expand=True)

        self.info_tree = ttk.Treeview(
            info_frame,
            columns=("prop", "val"),
            show="headings",
            style="Studio.Treeview",
        )
        self.info_tree.tag_configure("odd", background="#0c1018")
        self.info_tree.tag_configure("even", background="#101622")
        self.info_tree.heading("prop", text="HARDWARE / SYSTEM PROPERTY")
        self.info_tree.column("prop", width=310, anchor="w")
        self.info_tree.heading("val", text="LIVE TELEMETRY VALUE")
        self.info_tree.column("val", width=680, anchor="w")

        info_scroll = ttk.Scrollbar(info_frame, orient="vertical", command=self.info_tree.yview)
        self.info_tree.configure(yscrollcommand=info_scroll.set)
        self.info_tree.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)
        info_scroll.pack(side="right", fill="y", pady=2)

    # =========================================================================
    # STATUS FOOTER
    # =========================================================================
    def _build_status_footer(self) -> None:
        self.footer = ctk.CTkFrame(
            self.main_stage, fg_color=C_CARD, corner_radius=10, border_width=1, border_color=C_BORDER, height=34
        )
        self.footer.pack(fill="x", padx=16, pady=(4, 12))

        self.status_label = ctk.CTkLabel(
            self.footer,
            text=f"Ready  •  ADB Engine: {os.path.basename(self.adb.adb_path)}  •  Scrcpy Engine: {os.path.basename(self.adb.scrcpy_path)}",
            font=ctk.CTkFont(size=11),
            text_color=C_TEXT_SUB,
        )
        self.status_label.pack(side="left", padx=14, pady=4)

    def set_status(self, msg: str, color: str = C_ACCENT) -> None:
        self.status_label.configure(text=msg, text_color=color)

    # =========================================================================
    # DEVICE DISCOVERY, AUTONOMOUS AUTHORIZATION & WIRELESS ADB
    # =========================================================================
    def _auto_bus_auth_watchdog_loop(self) -> None:
        """
        Continuously monitor the USB/LAN ADB bus every 2.5 seconds.
        - Automatically detects newly plugged devices without manual clicking.
        - If any connected device is 'unauthorized' or 'offline', automatically dispatches
          RSA handshake retries (`adb reconnect offline` / `adb -s <serial> reconnect`).
        - Immediately refreshes UI telemetry the instant you tap 'Allow' on the phone screen!
        """
        def worker() -> None:
            devs = self.adb.list_devices(auto_heal=True)
            sig = "|".join(f"{d['serial']}:{d['state']}:{d['model']}" for d in devs)
            if sig != self._last_bus_sig:
                self._last_bus_sig = sig
                self.after(0, lambda: self._update_device_dropdown(devs))

        threading.Thread(target=worker, daemon=True).start()
        self.after(2500, self._auto_bus_auth_watchdog_loop)

    def _manual_retrigger_auth(self) -> None:
        self.set_status("Dispatching Multi-Key RSA Handshake & ADB Reconnect to all devices...", C_AMBER)

        def worker() -> None:
            msg = self.adb.force_reconnect_unauthorized(self.current_serial)
            time.sleep(1.0)
            devs = self.adb.list_devices(auto_heal=False)
            self._last_bus_sig = "|".join(f"{d['serial']}:{d['state']}:{d['model']}" for d in devs)
            self.after(0, lambda: self._update_device_dropdown(devs))
            self.after(0, lambda: self.set_status(f"{msg} Check phone screen to tap 'Allow'!", C_AMBER))

        threading.Thread(target=worker, daemon=True).start()

    def refresh_devices(self) -> None:
        def worker() -> None:
            devs = self.adb.list_devices(auto_heal=True)
            self._last_bus_sig = "|".join(f"{d['serial']}:{d['state']}:{d['model']}" for d in devs)
            self.after(0, lambda: self._update_device_dropdown(devs))

        threading.Thread(target=worker, daemon=True).start()

    def _update_device_dropdown(self, devs: List[Dict[str, str]]) -> None:
        self.devices_cache = devs
        if not devs:
            self.device_combo.configure(values=["No ADB Devices Connected"])
            self.device_combo.set("No ADB Devices Connected")
            self.current_serial = None
            self.current_state = "disconnected"
            self.monitor.active_serial = None
            self.lbl_side_status.configure(text="DISCONNECTED", text_color=C_CRIMSON)
            self.lbl_side_model.configure(text="No Device Found")
            self.set_status("No active ADB devices found. Connect via USB or Wi-Fi ADB.", C_CRIMSON)
            return

        # Sort so authorized ('device') phones appear first, or keep currently selected serial if still present
        labels = [f"{d['serial']} ({d['model']} - {d['state']})" for d in devs]
        self.device_combo.configure(values=labels)

        chosen_label = labels[0]
        if self.current_serial:
            for lbl in labels:
                if lbl.startswith(f"{self.current_serial} "):
                    chosen_label = lbl
                    break
        self.device_combo.set(chosen_label)
        self._on_device_selected(chosen_label)

    def _on_device_selected(self, selection: str) -> None:
        if not self.devices_cache or selection == "No ADB Devices Connected":
            return
        serial = selection.split()[0].strip()
        self.current_serial = serial

        dev_meta = next((d for d in self.devices_cache if d["serial"] == serial), None)
        state = dev_meta["state"] if dev_meta else "device"
        self.current_state = state

        if state in ("unauthorized", "offline"):
            self.monitor.active_serial = None
            self.lbl_side_status.configure(text="AWAITING PHONE AUTH...", text_color=C_AMBER)
            self.lbl_side_model.configure(text=f"{serial} ({state})")
            self.lbl_side_specs.configure(
                text="📲 Auto-sent RSA Key Popup!\nUnlock phone & tap 'Allow'\n(Check 'Always allow')"
            )
            self.set_status(
                f"⚡ Auto-Authorizing {serial}: RSA key handshake sent! Unlock phone screen and tap 'Allow USB debugging'.",
                C_AMBER,
            )
            return

        self.monitor.active_serial = serial
        model_name = selection.split("(")[1].split("-")[0].strip() if "(" in selection else serial
        self.lbl_side_status.configure(text="ONLINE • AUTHORIZED", text_color=C_EMERALD)
        self.lbl_side_model.configure(text=model_name.replace("_", " "))
        self.set_status(f"Connected & Authorized Target Device: {selection}", C_EMERALD)
        self.refresh_device_info()
        self.refresh_packages_list()

    def _connect_wireless_adb(self) -> None:
        addr = self.wireless_entry.get().strip()
        if not addr:
            messagebox.showwarning("Wireless ADB", "Enter target device IP:Port (e.g., 192.168.8.246:5555)")
            return
        if ":" not in addr:
            addr += ":5555"

        def worker() -> None:
            _code, out, err = self.adb.run_adb(["connect", addr], timeout=6.0)
            msg = out or err
            self.after(0, lambda: self.set_status(f"Wi-Fi Connect ({addr}): {msg}", C_ACCENT))
            self.refresh_devices()

        threading.Thread(target=worker, daemon=True).start()

    def _enable_tcpip_5555(self) -> None:
        if not self.current_serial:
            return

        def worker() -> None:
            _code, out, err = self.adb.run_adb(["tcpip", "5555"], serial=self.current_serial, timeout=5.0)
            msg = out or err or "TCP/IP port 5555 enabled"
            self.after(0, lambda: self.set_status(f"ADB TCP/IP: {msg}", C_EMERALD))

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    # EMULATOR NAVIGATION & HARDWARE BUTTON DISPATCH (FROM SIDE-TOOLBAR)
    # =========================================================================
    def _handle_nav_button(self, action: str) -> None:
        serial = self.current_serial
        if not serial:
            self.set_status("No device connected for navigation input.", C_CRIMSON)
            return

        def worker() -> None:
            if action == "cmd_notif":
                self.adb.run_adb(["shell", "cmd", "statusbar", "expand-notifications"], serial=serial)
                self.after(0, lambda: self.set_status("Expanded notifications shade on device.", C_ACCENT))
            elif action == "cmd_qsettings":
                self.adb.run_adb(["shell", "cmd", "statusbar", "expand-settings"], serial=serial)
                self.after(0, lambda: self.set_status("Expanded quick settings panel on device.", C_ACCENT))
            elif action == "cmd_screen":
                self._capture_device_screenshot(serial)
            elif action == "cmd_rotate":
                self._rotation_state = (self._rotation_state + 1) % 4
                self.adb.run_adb(
                    [
                        "shell",
                        f"settings put system accelerometer_rotation 0; settings put system user_rotation {self._rotation_state}",
                    ],
                    serial=serial,
                )
                self.after(0, lambda: self.set_status(f"Rotated screen orientation ({self._rotation_state * 90}°)", C_ACCENT))
            else:
                self.adb.send_keyevent(serial, action)
                self.after(0, lambda: self.set_status(f"Dispatched Android KeyEvent {action} to {serial}", C_ACCENT))

        threading.Thread(target=worker, daemon=True).start()

    def _capture_device_screenshot(self, serial: str) -> None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(os.path.expanduser("~"), "Pictures", "AndroidScrcpyStudio")
        os.makedirs(out_dir, exist_ok=True)
        local_path = os.path.join(out_dir, f"screen_{serial}_{ts}.png")
        remote_tmp = "/sdcard/jarvis_screen_tmp.png"
        code, _, _ = self.adb.run_adb(["shell", "screencap", "-p", remote_tmp], serial=serial, timeout=6.0)
        if code == 0:
            self.adb.run_adb(["pull", remote_tmp, local_path], serial=serial, timeout=6.0)
            self.adb.run_adb(["shell", "rm", "-f", remote_tmp], serial=serial, timeout=3.0)
            self.after(0, lambda: self.set_status(f"Screenshot saved: {local_path}", C_EMERALD))

    def _send_text_to_device(self) -> None:
        serial = self.current_serial
        text = self.inject_text_entry.get()
        if not serial or not text:
            return
        escaped = text.replace(" ", "%s").replace("'", r"\'").replace('"', r"\"")

        def worker() -> None:
            self.adb.run_adb(["shell", "input", "text", escaped], serial=serial, timeout=4.0)
            self.after(0, lambda: self.set_status(f"Injected keyboard text to {serial}", C_EMERALD))

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    # SCRCPY MIRROR ENGINE + MAGNETIC EMULATOR SIDE-TOOLBAR
    # =========================================================================
    def start_scrcpy_mirror(self) -> None:
        if not self.current_serial:
            messagebox.showwarning("Scrcpy Mirror", "Connect and select an ADB device first.")
            return

        self.stop_scrcpy_mirror()

        win_title = f"Scrcpy Mirror — {self.current_serial}"
        cmd = [self.adb.scrcpy_path, "-s", self.current_serial]

        res_choice = self.mirror_res_var.get()
        m_res = re.search(r"^(\d+)", res_choice)
        if m_res:
            cmd.extend([f"--max-size={m_res.group(1)}"])

        vbit = self.mirror_vbit_var.get().split()[0]
        cmd.extend([f"--video-bit-rate={vbit}"])

        fps = self.mirror_fps_var.get()
        cmd.extend([f"--max-fps={fps}"])

        vcodec = self.mirror_vcodec_var.get()
        cmd.extend([f"--video-codec={vcodec}"])

        if self.mirror_no_audio.get():
            cmd.append("--no-audio")
        else:
            abit = self.mirror_abit_var.get().split()[0]
            acodec = self.mirror_acodec_var.get()
            cmd.extend([f"--audio-bit-rate={abit}", f"--audio-codec={acodec}"])

        if self.mirror_turn_screen_off.get():
            cmd.append("--turn-screen-off")
        if self.mirror_stay_awake.get():
            cmd.append("--stay-awake")
        if self.mirror_always_top.get():
            cmd.append("--always-on-top")
        if self.mirror_show_touches.get():
            cmd.append("--show-touches")

        cmd.append(f"--window-title={win_title}")

        try:
            env = os.environ.copy()
            env["ADB"] = self.adb.adb_path
            scrcpy_dir = os.path.dirname(self.adb.scrcpy_path)
            srv_candidate = os.path.join(scrcpy_dir, "scrcpy-server")
            if os.path.isfile(srv_candidate):
                env["SCRCPY_SERVER_PATH"] = srv_candidate
            self.scrcpy_mirror_proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **get_subprocess_kwargs(),
            )

            if self.mirror_attach_sidebar.get():
                self.emulator_sidebar = ScrcpyEmulatorSideBar(
                    self,
                    self.icons,
                    win_title,
                    self.scrcpy_mirror_proc,
                    self._handle_nav_button,
                )

            self.set_status(
                f"Scrcpy Mirror Active (PID {self.scrcpy_mirror_proc.pid}) with Magnetic Emulator Side-Toolbar",
                C_EMERALD,
            )
        except Exception as exc:
            messagebox.showerror("Scrcpy Launch Error", f"Failed to launch scrcpy:\n{exc}")

    def stop_scrcpy_mirror(self) -> None:
        if self.emulator_sidebar is not None:
            self.emulator_sidebar.close_bar()
            self.emulator_sidebar = None
        if self.scrcpy_mirror_proc and self.scrcpy_mirror_proc.poll() is None:
            try:
                self.scrcpy_mirror_proc.terminate()
            except Exception:
                pass
            self.scrcpy_mirror_proc = None
            self.set_status("Scrcpy Mirror stopped.", C_AMBER)

    # =========================================================================
    # PC DEX / DESKTOP WORKSTATION ENGINE
    # =========================================================================
    def _log_dex(self, text: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self.dex_status_box.insert("end", f"[{ts}] {text}\n")
        self.dex_status_box.see("end")

    def _set_android_desktop_flags(self, enable: bool) -> None:
        serial = self.current_serial
        if not serial:
            return
        val = "1" if enable else "0"

        def worker() -> None:
            cmds = [
                f"settings put global force_desktop_mode_on_external_displays {val}",
                f"settings put global enable_freeform_support {val}",
                f"settings put global force_resizable_activities {val}",
                f"settings put global enable_non_resizable_multi_window {val}",
            ]
            self.adb.run_adb(["shell", "; ".join(cmds)], serial=serial, timeout=5.0)
            state_str = "ENABLED" if enable else "RESET"
            self.after(0, lambda: self._log_dex(f"Android Desktop & Freeform window flags {state_str} on {serial}."))

        threading.Thread(target=worker, daemon=True).start()

    def start_dex_desktop_mode(self, start_package: Optional[str] = None) -> None:
        if not self.current_serial:
            messagebox.showwarning("PC DeX Mode", "Connect and select an ADB device first.")
            return

        self.stop_dex_desktop_mode()

        if self.dex_force_settings.get():
            self._set_android_desktop_flags(True)

        res = self.dex_res_var.get().split()[0]
        dpi = self.dex_dpi_var.get().split()[0]
        fps = self.dex_fps_var.get()
        vbit = self.dex_vbit_var.get()

        cmd = [
            self.adb.scrcpy_path,
            "-s",
            self.current_serial,
            f"--new-display={res}/{dpi}",
            f"--max-fps={fps}",
            f"--video-bit-rate={vbit}",
            f"--window-title=J.A.R.V.I.S. DeX Desktop Mode — {self.current_serial} ({res} @ {dpi} DPI)",
        ]

        if self.dex_keep_content.get():
            cmd.append("--no-vd-destroy-content")
        if self.dex_fullscreen.get():
            cmd.append("--fullscreen")

        pkg = start_package or self.dex_start_app_entry.get().strip()
        if pkg:
            cmd.append(f"--start-app=+{pkg}")

        try:
            env = os.environ.copy()
            env["ADB"] = self.adb.adb_path
            scrcpy_dir = os.path.dirname(self.adb.scrcpy_path)
            srv_candidate = os.path.join(scrcpy_dir, "scrcpy-server")
            if os.path.isfile(srv_candidate):
                env["SCRCPY_SERVER_PATH"] = srv_candidate
            self.scrcpy_dex_proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **get_subprocess_kwargs(),
            )
            self._log_dex(f"Launched Virtual Desktop Display: {res}/{dpi} DPI @ {fps} FPS (PID {self.scrcpy_dex_proc.pid})")
            self.set_status(f"PC DeX Desktop Session Active (PID {self.scrcpy_dex_proc.pid})", C_EMERALD)
        except Exception as exc:
            self._log_dex(f"ERROR launching DeX Desktop: {exc}")
            messagebox.showerror("DeX Mode Error", str(exc))

    def stop_dex_desktop_mode(self) -> None:
        if self.scrcpy_dex_proc and self.scrcpy_dex_proc.poll() is None:
            try:
                self.scrcpy_dex_proc.terminate()
            except Exception:
                pass
            self.scrcpy_dex_proc = None
            self._log_dex("Stopped Virtual Desktop Display session.")
            self.set_status("PC DeX Desktop session stopped.", C_AMBER)

    # =========================================================================
    # LIVE SYSTEM TASK MANAGER & GRID-BACKED GLOW SPARKLINE RENDERER
    # =========================================================================
    def _draw_sparkline(
        self, canvas: tk.Canvas, data: deque, stroke_color: str, fill_color: str, max_val: float = 100.0
    ) -> None:
        canvas.delete("all")
        w = max(canvas.winfo_width(), 200)
        h = max(canvas.winfo_height(), 46)

        # Subtle background gridlines
        for gy in (int(h * 0.25), int(h * 0.5), int(h * 0.75)):
            canvas.create_line(0, gy, w, gy, fill="#111827", width=1)

        pts = list(data)
        if len(pts) < 2:
            return

        step_x = w / (len(pts) - 1)
        coords: List[float] = []
        for idx, val in enumerate(pts):
            x = idx * step_x
            norm = max(0.0, min(1.0, val / max(max_val, 1.0)))
            y = h - (norm * (h - 10)) - 5
            coords.extend([x, y])

        poly_coords = [0, h] + coords + [w, h]
        canvas.create_polygon(poly_coords, fill=fill_color, outline="")
        canvas.create_line(coords, fill=stroke_color, width=2, smooth=True)

        # Glowing live endpoint dot
        ex, ey = coords[-2], coords[-1]
        canvas.create_oval(ex - 4, ey - 4, ex + 4, ey + 4, fill=stroke_color, outline="#ffffff", width=1)

    def _periodic_table_sync(self) -> None:
        with self.monitor.lock:
            cpu_pct = self.monitor.cpu_total_pct
            ram_used = self.monitor.ram_used_mb
            ram_tot = self.monitor.ram_total_mb
            ram_pct = self.monitor.ram_pct
            swap_used = self.monitor.swap_used_mb
            swap_tot = self.monitor.swap_total_mb
            bat_lvl = self.monitor.battery_level
            bat_temp = self.monitor.battery_temp_c
            t_tot = self.monitor.tasks_total
            t_run = self.monitor.tasks_running
            procs = list(self.monitor.processes)
            h_cpu = deque(self.monitor.history_cpu)
            h_ram = deque(self.monitor.history_ram)
            h_temp = deque(self.monitor.history_temp)

        self.lbl_cpu_val.configure(text=f"CPU Load: {cpu_pct:.1f}%")
        self.lbl_tasks_val.configure(text=f"Tasks: {t_tot} Total ({t_run} Running)")
        self.lbl_ram_val.configure(text=f"RAM: {ram_used:.0f} / {ram_tot:.0f} MB ({ram_pct:.1f}%)")
        self.lbl_swap_val.configure(text=f"ZRAM Swap: {swap_used:.0f} / {swap_tot:.0f} MB")
        self.lbl_bat_val.configure(text=f"Battery: {bat_lvl}%  •  {bat_temp:.1f} °C")

        self._draw_sparkline(self.canvas_cpu, h_cpu, C_ACCENT, "#0a2239", 100.0)
        self._draw_sparkline(self.canvas_ram, h_ram, "#c084fc", "#23123b", 100.0)
        self._draw_sparkline(self.canvas_temp, h_temp, C_EMERALD, "#08291f", 60.0)

        selected_pid = None
        sel = self.proc_tree.selection()
        if sel:
            item_vals = self.proc_tree.item(sel[0], "values")
            if item_vals:
                selected_pid = str(item_vals[0])

        flt = self.proc_filter_var.get().strip().lower()
        self.proc_tree.delete(*self.proc_tree.get_children())
        row_idx = 0
        for p in procs:
            if flt and flt not in p["name"].lower() and flt not in str(p["pid"]) and flt not in p["user"].lower():
                continue
            tag = "even" if (row_idx % 2 == 0) else "odd"
            row_idx += 1
            iid = self.proc_tree.insert(
                "",
                "end",
                tags=(tag,),
                values=(
                    p["pid"],
                    p["user"],
                    f"{p['cpu']:.1f}%",
                    f"{p['mem']:.1f}%",
                    p["res"],
                    p["state"],
                    p["time"],
                    p["name"],
                ),
            )
            if selected_pid and str(p["pid"]) == selected_pid:
                self.proc_tree.selection_set(iid)

        self.after(2000, self._periodic_table_sync)

    def _toggle_monitor_pause(self) -> None:
        self.monitor.paused = not self.monitor.paused
        if self.monitor.paused:
            self.pause_mon_btn.configure(text="Resume Live Poll", fg_color=C_PRIMARY)
            self.lbl_mon_state.configure(text="Live Telemetry: PAUSED", text_color=C_AMBER)
        else:
            self.pause_mon_btn.configure(text="Pause Live Poll", fg_color=C_SURFACE)
            self.lbl_mon_state.configure(text="Live Telemetry: Active (2.0s)", text_color=C_TEXT_SUB)

    def _force_stop_selected_process(self) -> None:
        if not self.current_serial:
            return
        sel = self.proc_tree.selection()
        if not sel:
            messagebox.showinfo("Task Manager", "Select a process row in the table first.")
            return
        vals = self.proc_tree.item(sel[0], "values")
        pid, proc_name = vals[0], vals[7]
        pkg_candidate = proc_name.split(":")[0].split()[0]

        def worker() -> None:
            if "." in pkg_candidate and not pkg_candidate.startswith("/"):
                self.adb.run_adb(["shell", "am", "force-stop", pkg_candidate], serial=self.current_serial)
                msg = f"Force-stopped package {pkg_candidate} (PID {pid})"
            else:
                self.adb.run_adb(["shell", "kill", "-9", str(pid)], serial=self.current_serial)
                msg = f"Sent SIGKILL to PID {pid} ({proc_name})"
            self.after(0, lambda: self.set_status(msg, C_CRIMSON))
            self.monitor.poll_once()

        threading.Thread(target=worker, daemon=True).start()

    def _trim_device_memory(self) -> None:
        if not self.current_serial:
            return

        def worker() -> None:
            self.adb.run_adb(
                ["shell", "am", "send-trim-memory", "--user", "0", "RUNNING_CRITICAL"], serial=self.current_serial
            )
            self.after(0, lambda: self.set_status("Dispatched memory trim request to running user processes.", C_EMERALD))

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    # APP MANAGER (MULTI-APK BATCH INSTALL / UNINSTALL / LIST / BACKUP / LAUNCH)
    # =========================================================================
    def refresh_packages_list(self) -> None:
        serial = self.current_serial
        if not serial:
            return

        mode = self.app_type_var.get()
        flag = "-3"
        category = "User Installed"
        if "-s" in mode:
            flag = "-s"
            category = "System Package"
        elif "All" in mode:
            flag = ""
            category = "All Packages"

        def worker() -> None:
            args = ["shell", "pm", "list", "packages"]
            if flag:
                args.append(flag)
            code, out, _ = self.adb.run_adb(args, serial=serial, timeout=8.0)
            pkgs: List[str] = []
            if code == 0 and out:
                for line in out.splitlines():
                    line = line.strip()
                    if line.startswith("package:"):
                        pkgs.append(line.replace("package:", "").strip())
            pkgs.sort()
            self.packages_cache = pkgs
            self.after(0, lambda: self._populate_packages_tree(category))

        threading.Thread(target=worker, daemon=True).start()

    def _populate_packages_tree(self, category: str) -> None:
        self._filter_packages_tree(category)

    def _filter_packages_tree(self, category: str = "User Installed") -> None:
        query = self.app_search_var.get().strip().lower()
        self.pkg_tree.delete(*self.pkg_tree.get_children())
        count = 0
        for pkg in self.packages_cache:
            if query and query not in pkg.lower():
                continue
            tag = "even" if (count % 2 == 0) else "odd"
            self.pkg_tree.insert("", "end", tags=(tag,), values=(pkg, category))
            count += 1
        self.lbl_pkg_count.configure(text=f"Packages Loaded: {count}")

    def _get_selected_package(self) -> Optional[str]:
        sel = self.pkg_tree.selection()
        if not sel:
            messagebox.showinfo("App Manager", "Select an application package from the list first.")
            return None
        vals = self.pkg_tree.item(sel[0], "values")
        return vals[0] if vals else None

    def _install_apk_dialog(self) -> None:
        if not self.current_serial:
            messagebox.showwarning("App Manager", "Connect and select an ADB device first.")
            return
        apk_paths = filedialog.askopenfilenames(
            title="Select One or Multiple Android APK Files to Install",
            filetypes=[("Android Package", "*.apk"), ("All Files", "*.*")],
        )
        if not apk_paths:
            return

        apk_list = list(apk_paths)
        self.set_status(f"Batch installing {len(apk_list)} APK(s) onto {self.current_serial}...", C_ACCENT)

        def on_batch_done() -> None:
            self.set_status(f"Completed batch APK installation ({len(apk_list)} package(s)).", C_EMERALD)
            self.refresh_packages_list()

        BatchApkInstallModal(self, self.adb, self.current_serial, apk_list, on_batch_done)

    def _uninstall_selected_package(self) -> None:
        pkg = self._get_selected_package()
        if not pkg or not self.current_serial:
            return
        if not messagebox.askyesno("Confirm Uninstall", f"Uninstall package '{pkg}' from {self.current_serial}?"):
            return

        def worker() -> None:
            code, out, err = self.adb.run_adb(["uninstall", pkg], serial=self.current_serial, timeout=20.0)
            if code == 0 and "Success" in out:
                self.after(0, lambda: self.set_status(f"Uninstalled {pkg}", C_EMERALD))
                self.refresh_packages_list()
            else:
                _code2, out2, err2 = self.adb.run_adb(
                    ["shell", "pm", "uninstall", "-k", "--user", "0", pkg], serial=self.current_serial, timeout=20.0
                )
                msg = out2 or err2 or out or err
                self.after(0, lambda: self.set_status(f"Uninstall result for {pkg}: {msg}", C_ACCENT))
                self.refresh_packages_list()

        threading.Thread(target=worker, daemon=True).start()

    def _force_stop_selected_package(self) -> None:
        pkg = self._get_selected_package()
        if not pkg or not self.current_serial:
            return

        def worker() -> None:
            self.adb.run_adb(["shell", "am", "force-stop", pkg], serial=self.current_serial)
            self.after(0, lambda: self.set_status(f"Force-stopped {pkg}", C_AMBER))

        threading.Thread(target=worker, daemon=True).start()

    def _clear_selected_package_data(self) -> None:
        pkg = self._get_selected_package()
        if not pkg or not self.current_serial:
            return
        if not messagebox.askyesno("Clear App Data", f"Wipe all data and cache for '{pkg}'?"):
            return

        def worker() -> None:
            code, out, _ = self.adb.run_adb(["shell", "pm", "clear", pkg], serial=self.current_serial)
            self.after(0, lambda: self.set_status(f"Clear Data ({pkg}): {out}", C_EMERALD if code == 0 else C_CRIMSON))

        threading.Thread(target=worker, daemon=True).start()

    def _launch_selected_package(self) -> None:
        pkg = self._get_selected_package()
        if not pkg or not self.current_serial:
            return

        def worker() -> None:
            self.adb.run_adb(
                ["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"],
                serial=self.current_serial,
            )
            self.after(0, lambda: self.set_status(f"Launched {pkg} on device.", C_EMERALD))

        threading.Thread(target=worker, daemon=True).start()

    def _launch_selected_package_in_dex(self) -> None:
        pkg = self._get_selected_package()
        if not pkg:
            return
        self._switch_view(1)
        self.dex_start_app_entry.delete(0, "end")
        self.dex_start_app_entry.insert(0, pkg)
        self.start_dex_desktop_mode(start_package=pkg)

    def _pull_selected_apk(self) -> None:
        pkg = self._get_selected_package()
        if not pkg or not self.current_serial:
            return

        save_dir = filedialog.askdirectory(title="Select Destination Folder for Pulled APK")
        if not save_dir:
            return

        def worker() -> None:
            code, out, _ = self.adb.run_adb(["shell", "pm", "path", pkg], serial=self.current_serial)
            if code == 0 and out:
                first_line = out.splitlines()[0].strip()
                remote_apk = first_line.replace("package:", "").strip()
                local_apk = os.path.join(save_dir, f"{pkg}.apk")
                c2, _, _ = self.adb.run_adb(["pull", remote_apk, local_apk], serial=self.current_serial, timeout=60.0)
                if c2 == 0:
                    self.after(0, lambda: self.set_status(f"Pulled APK to {local_apk}", C_EMERALD))
                    return
            self.after(0, lambda: self.set_status(f"Failed to pull APK for {pkg}", C_CRIMSON))

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    # DEVICE HARDWARE & SYSTEM TELEMETRY INFO
    # =========================================================================
    def refresh_device_info(self) -> None:
        serial = self.current_serial
        if not serial:
            return

        def worker() -> None:
            info = self.adb.get_device_info(serial)
            self.after(0, lambda: self._populate_device_info(info))

        threading.Thread(target=worker, daemon=True).start()

    def _populate_device_info(self, info: Dict[str, str]) -> None:
        self.last_device_info = info
        self.info_tree.delete(*self.info_tree.get_children())
        for idx, (k, v) in enumerate(info.items()):
            tag = "even" if (idx % 2 == 0) else "odd"
            self.info_tree.insert("", "end", tags=(tag,), values=(k, v))

    def _copy_device_info_clipboard(self) -> None:
        info = getattr(self, "last_device_info", {})
        if not info:
            return
        self.clipboard_clear()
        self.clipboard_append(json.dumps(info, indent=2))
        self.set_status("Copied Device Hardware JSON report to clipboard.", C_EMERALD)

    # =========================================================================
    # PARENT-COUPLED LIFECYCLE WATCHDOG (RULE #6)
    # =========================================================================
    def _cleanup_child_engines(self) -> None:
        self.monitor.running = False
        self.stop_scrcpy_mirror()
        self.stop_dex_desktop_mode()

    def _lifecycle_watchdog_loop(self) -> None:
        while self.monitor.running:
            if not psutil.pid_exists(self.parent_pid):
                self._cleanup_child_engines()
                os._exit(0)
            time.sleep(2.0)

    def _on_close(self) -> None:
        self._cleanup_child_engines()
        self.destroy()


if __name__ == "__main__":
    app = AdbScrcpyStudioApp()
    app.mainloop()
