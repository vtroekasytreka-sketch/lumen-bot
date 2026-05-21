"""Neon sign preview generator using Pillow."""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def hex_to_rgb(h: str) -> tuple:
    """Convert hex color to RGB tuple."""
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def generate_neon(text: str, color: str = "#B040FF",
                  output_path: str = "previews/neon.png") -> str:
    """
    Generate neon sign preview image.

    Args:
        text: Mission text to display
        color: Hex color for neon glow
        output_path: Path to save the image

    Returns:
        Path to generated image
    """
    os.makedirs("previews", exist_ok=True)

    W, H = 900, 350
    bg_color = "#080810"
    img = Image.new("RGB", (W, H), bg_color)

    font = None
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "arial.ttf"
    ]

    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, 72)
            break
        except (OSError, IOError):
            continue

    if font is None:
        font = ImageFont.load_default()

    dummy = ImageDraw.Draw(img)
    bbox = dummy.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (W - tw) // 2
    y = (H - th) // 2 - bbox[1]

    cr, cg, cb = hex_to_rgb(color)

    for radius in [25, 18, 12, 6]:
        glow = Image.new("RGB", (W, H), bg_color)
        gd = ImageDraw.Draw(glow)
        alpha = 0.15 + (25 - radius) * 0.02
        r = min(255, int(cr * alpha * 3))
        g = min(255, int(cg * alpha * 3))
        b = min(255, int(cb * alpha * 3))
        gd.text((x, y), text, font=font, fill=(r, g, b))
        glow = glow.filter(ImageFilter.GaussianBlur(radius))
        img = Image.blend(img, glow, 0.5)

    draw = ImageDraw.Draw(img)

    for offset in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        draw.text((x + offset[0], y + offset[1]), text, font=font, fill=color)

    draw.text((x, y), text, font=font, fill=(255, 255, 255))

    img.save(output_path, quality=95)
    return output_path


def generate_neon_for_user(user_id: int, text: str, color: str = "#B040FF") -> str:
    """Generate neon preview for specific user."""
    output_path = f"previews/neon_{user_id}.png"
    return generate_neon(text, color, output_path)
