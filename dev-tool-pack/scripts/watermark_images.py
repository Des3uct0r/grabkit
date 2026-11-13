"""Batch watermark images with text."""
import os, sys, argparse
from PIL import Image, ImageDraw, ImageFont

def watermark_image(path, text, position="bottom-right", opacity=128, font_size=36, color=(255, 255, 255)):
    img = Image.open(path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    margin = 20
    if position == "bottom-right":
        x, y = img.width - tw - margin, img.height - th - margin
    elif position == "bottom-left":
        x, y = margin, img.height - th - margin
    elif position == "top-right":
        x, y = img.width - tw - margin, margin
    elif position == "top-left":
        x, y = margin, margin
    elif position == "center":
        x, y = (img.width - tw) // 2, (img.height - th) // 2
    else:
        x, y = img.width - tw - margin, img.height - th - margin
    draw.text((x, y), text, font=font, fill=(*color, opacity))
    result = Image.alpha_composite(img, overlay).convert("RGB")
    return result

def main():
    ap = argparse.ArgumentParser(description="Batch watermark images with text")
    ap.add_argument("folder", help="Folder with images")
    ap.add_argument("--text", required=True, help="Watermark text")
    ap.add_argument("--position", default="bottom-right", choices=["bottom-right", "bottom-left", "top-right", "top-left", "center"])
    ap.add_argument("--opacity", type=int, default=128, help="Opacity 0-255")
    ap.add_argument("--font-size", type=int, default=36, help="Font size")
    ap.add_argument("--output", default=None, help="Output folder (default: folder/watermarked)")
    ap.add_argument("--dry-run", action="store_true", help="Preview without processing")
    args = ap.parse_args()

    folder = os.path.abspath(args.folder)
    out = os.path.abspath(args.output) if args.output else os.path.join(folder, "watermarked")
    os.makedirs(out, exist_ok=True)
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    files = [f for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in exts]

    print(f"Found {len(files)} images. Watermark: '{args.text}'")
    for f in files:
        src = os.path.join(folder, f)
        dst = os.path.join(out, f)
        if args.dry_run:
            print(f"[DRY] {f}")
            continue
        try:
            result = watermark_image(src, args.text, args.position, args.opacity, args.font_size)
            result.save(dst)
            print(f"Watermarked: {f}")
        except Exception as e:
            print(f"Error on {f}: {e}")

if __name__ == "__main__":
    main()
