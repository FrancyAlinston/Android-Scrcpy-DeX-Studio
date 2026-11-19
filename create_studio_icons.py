#!/usr/bin/env python3
"""
Generate high-fidelity, 4x supersampled multi-resolution Windows ICO, PNG, and embedded UI icons
for J.A.R.V.I.S. Android & Scrcpy DeX Studio (v2.0).
"""

import os
import math
from PIL import Image, ImageDraw, ImageFilter


def create_studio_app_icon(out_dir: str) -> tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    ico_path = os.path.join(out_dir, "android_scrcpy_dex.ico")
    png_path = os.path.join(out_dir, "android_scrcpy_dex.png")

    dim = 1024
    img = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))

    # 1. Soft Ambient Drop Shadow
    shadow = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    pad = 72
    s_draw.rounded_rectangle([pad, pad + 26, dim - pad, dim - pad + 26], radius=220, fill=(0, 0, 0, 160))
    shadow = shadow.filter(ImageFilter.GaussianBlur(42))
    img.alpha_composite(shadow)

    # 2. Dark Obsidian Metallic Squircle Base
    body = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(body)
    for y in range(pad, dim - pad):
        prog = (y - pad) / (dim - 2 * pad)
        r = int(22 - prog * 12)
        g = int(28 - prog * 14)
        b = int(40 - prog * 20)
        b_draw.line([pad, y, dim - pad, y], fill=(r, g, b, 255))

    mask = Image.new("L", (dim, dim), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle([pad, pad, dim - pad, dim - pad], radius=220, fill=255)
    body.putalpha(mask)
    img.alpha_composite(body)

    # 3. Dual Neon Glow Underlay (Cyan DeX Left + Android Emerald Right)
    glow = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    g_draw.ellipse([140, 200, 620, 820], fill=(14, 165, 233, 95))
    g_draw.ellipse([440, 220, 880, 820], fill=(16, 185, 129, 95))
    glow = glow.filter(ImageFilter.GaussianBlur(75))
    glow.putalpha(Image.composite(glow.split()[3], Image.new("L", (dim, dim), 0), mask))
    img.alpha_composite(glow)

    # 4. Outer Glass Rim
    border = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    bd_draw = ImageDraw.Draw(border)
    bd_draw.rounded_rectangle([pad, pad, dim - pad, dim - pad], radius=220, outline=(56, 189, 248, 210), width=8)
    img.alpha_composite(border)

    # 5. Draw Desktop DeX Monitor Frame (Center-Back)
    fg = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    d = ImageDraw.Draw(fg)

    # Monitor bezel
    mon_box = [190, 230, 740, 610]
    d.rounded_rectangle(mon_box, radius=36, fill=(15, 23, 42, 240), outline=(56, 189, 248, 255), width=16)
    # Monitor Stand
    d.polygon([(425, 610), (505, 610), (535, 690), (395, 690)], fill=(56, 189, 248, 255))
    d.rounded_rectangle([350, 685, 580, 710], radius=12, fill=(56, 189, 248, 255))

    # DeX Desktop Window Elements inside Monitor
    d.rounded_rectangle([235, 275, 480, 440], radius=16, fill=(30, 41, 59, 255), outline=(14, 165, 233, 220), width=6)
    d.ellipse([255, 292, 271, 308], fill=(244, 63, 94, 255))
    d.ellipse([282, 292, 298, 308], fill=(245, 158, 11, 255))
    d.ellipse([309, 292, 325, 308], fill=(16, 185, 129, 255))
    # Sparkline wave inside DeX window
    wave_pts = [(255, 405), (300, 365), (345, 390), (395, 340), (455, 355)]
    d.line(wave_pts, fill=(56, 189, 248, 255), width=10, joint="curve")

    # 6. Draw Android Smartphone Overlapping Front-Right
    ph_box = [560, 340, 835, 795]
    d.rounded_rectangle(ph_box, radius=44, fill=(13, 19, 31, 250), outline=(16, 185, 129, 255), width=16)
    # Phone speaker / punch hole
    d.ellipse([688, 365, 708, 385], fill=(56, 189, 248, 255))

    # Android Robot Head Stylized inside Phone
    ax, ay = 697, 545
    ar = 76
    d.pieslice([ax - ar, ay - ar, ax + ar, ay + ar], start=180, end=360, fill=(16, 185, 129, 255))
    # Antennae
    d.line([(ax - 35, ay - 52), (ax - 58, ay - 88)], fill=(16, 185, 129, 255), width=10)
    d.line([(ax + 35, ay - 52), (ax + 58, ay - 88)], fill=(16, 185, 129, 255), width=10)
    # Eyes
    d.ellipse([ax - 36, ay - 42, ax - 20, ay - 26], fill=(13, 19, 31, 255))
    d.ellipse([ax + 20, ay - 42, ax + 36, ay - 26], fill=(13, 19, 31, 255))

    # Phone Navigation Bar Symbols (Back Triangle, Home Circle, Recents Square)
    ny = 745
    # Back
    d.polygon([(615, ny), (633, ny - 12), (633, ny + 12)], fill=(148, 163, 184, 255))
    # Home
    d.ellipse([685, ny - 12, 709, ny + 12], fill=(56, 189, 248, 255))
    # Recents
    d.rounded_rectangle([760, ny - 11, 782, ny + 11], radius=4, fill=(148, 163, 184, 255))

    img.alpha_composite(fg)

    # Save 256x256 PNG and Multi-Size Windows ICO
    final_256 = img.resize((256, 256), Image.Resampling.LANCZOS)
    final_256.save(png_path, format="PNG")

    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=ico_sizes)
    print(f"[+] Generated Icon Suite: {ico_path} & {png_path}")
    return ico_path, png_path


if __name__ == "__main__":
    target_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    create_studio_app_icon(target_dir)
