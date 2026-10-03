"""
MediTrack ERP - Asset & Icon Generator
Creates professional, high-resolution application icons for Windows Desktop and Mobile PWA.
"""

import os
from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MOBILE_DIR = os.path.join(BASE_DIR, "mobile")

os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(MOBILE_DIR, exist_ok=True)

def create_meditrack_icon(size: int = 512) -> Image.Image:
    """Draws a professional, vector-like MediTrack emblem icon."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Background Rounded Box (Deep Emerald #166534)
    padding = int(size * 0.04)
    radius = int(size * 0.22)
    box = [padding, padding, size - padding, size - padding]
    
    # Outer background
    draw.rounded_rectangle(box, radius=radius, fill="#166534")

    # Inner subtle glow border
    inner_box = [padding + 4, padding + 4, size - padding - 4, size - padding - 4]
    draw.rounded_rectangle(inner_box, radius=radius - 2, outline="#15803D", width=int(size * 0.015))

    # 2. Medical Cross (Clean, symmetrical)
    cx, cy = size // 2, size // 2
    cross_w = int(size * 0.18)
    cross_h = int(size * 0.52)
    cross_r = int(cross_w * 0.35)

    # Vertical bar
    v_box = [cx - cross_w // 2, cy - cross_h // 2, cx + cross_w // 2, cy + cross_h // 2]
    # Horizontal bar
    h_box = [cx - cross_h // 2, cy - cross_w // 2, cx + cross_h // 2, cy + cross_w // 2]

    # Draw Cross in Pure White
    draw.rounded_rectangle(v_box, radius=cross_r, fill="#FFFFFF")
    draw.rounded_rectangle(h_box, radius=cross_r, fill="#FFFFFF")

    # 3. Medical Heart / Pill Accents in Center
    center_pill_w = int(cross_w * 0.6)
    center_pill_h = int(cross_h * 0.3)
    pill_box = [cx - center_pill_w // 2, cy - center_pill_h // 2, cx + center_pill_w // 2, cy + center_pill_h // 2]
    draw.rounded_rectangle(pill_box, radius=int(center_pill_w * 0.5), fill="#DCFCE7")

    return img

def main():
    print("Generating MediTrack application assets...")
    img_512 = create_meditrack_icon(512)
    img_192 = img_512.resize((192, 192), Image.Resampling.LANCZOS)
    img_32 = img_512.resize((32, 32), Image.Resampling.LANCZOS)

    # 1. Save PNG icons
    img_512.save(os.path.join(ASSETS_DIR, "icon.png"), "PNG")
    img_512.save(os.path.join(MOBILE_DIR, "icon.png"), "PNG")
    img_192.save(os.path.join(MOBILE_DIR, "icon-192.png"), "PNG")

    # 2. Save ICO file for Windows Desktop
    ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img_512.save(os.path.join(ASSETS_DIR, "icon.ico"), format="ICO", sizes=ico_sizes)
    img_32.save(os.path.join(MOBILE_DIR, "favicon.ico"), format="ICO", sizes=[(32, 32), (16, 16)])

    print("Successfully generated:")
    print("  -> assets/icon.png")
    print("  -> assets/icon.ico")
    print("  -> mobile/icon.png")
    print("  -> mobile/icon-192.png")
    print("  -> mobile/favicon.ico")

if __name__ == "__main__":
    main()
