#!/usr/bin/env python3
"""Turn source photos in assets/src/ into optimized web images in assets/img/.

Usage:
  python3 scripts/optimize_images.py                # convert photos in assets/src/
  python3 scripts/optimize_images.py --placeholder  # also make placeholders for missing photos
"""
import io
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "src"
OUT = ROOT / "assets" / "img"
EXTS = (".jpg", ".jpeg", ".png", ".webp")

MODELS = {
    "vf-2": "VF 2", "vf-3": "VF 3", "vf-5": "VF 5", "vf-6": "VF 6", "vf-7": "VF 7",
    "vf-8": "VF 8", "vf-9": "VF 9", "vf-mpv-7": "VF MPV 7", "limo-green": "Limo Green",
}
# stem -> (aspect w:h, output widths, byte budget per file, label for placeholder)
SPECS = {stem: ((16, 10), (480, 800, 1200), 80_000, f"VinFast {name}") for stem, name in MODELS.items()}
SPECS["hero"] = ((16, 10), (480, 800, 1200), 150_000, "VinFast Quảng Trị")
SPECS["seller"] = ((1, 1), (240, 480), 60_000, "Võ Đức Thành")
OG = ((1200, 630), 300_000, "VinFast Quảng Trị – Võ Đức Thành")


def font(size):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size=size)


def placeholder(w, h, label):
    img = Image.new("RGB", (w, h), "#dfe9e6")
    d = ImageDraw.Draw(img)
    for y in range(h):  # soft vertical gradient
        c = int(0xe7 - 0x1a * y / h)
        d.line([(0, y), (w, y)], fill=(c - 8, c + 4, c))
    f = font(max(18, w // 14))
    box = d.textbbox((0, 0), label, font=f)
    d.text(((w - box[2]) / 2, (h - box[3]) / 2), label, font=f, fill="#2f4a42")
    sub = font(max(12, w // 40))
    note = "Ảnh minh hoạ – sẽ thay ảnh thật"
    sb = d.textbbox((0, 0), note, font=sub)
    d.text(((w - sb[2]) / 2, (h + box[3]) / 2 + w // 40), note, font=sub, fill="#5a6872")
    return img


def encode(img, fmt, budget):
    """Encode, lowering quality until the file fits the byte budget."""
    for q in range(82, 15, -6):
        buf = io.BytesIO()
        img.save(buf, fmt, quality=q, method=6) if fmt == "WEBP" else img.save(buf, fmt, quality=q, optimize=True, progressive=True)
        if buf.tell() <= budget:
            return buf.getvalue()
    return buf.getvalue()


def fit_on_white(img, w, h):
    """Fit the whole image inside w x h on white with a small margin, never cropping it."""
    inner = (int(w * 0.92), int(h * 0.92))
    return ImageOps.pad(ImageOps.contain(img, inner, Image.LANCZOS), (w, h), color="#ffffff")


def is_white_studio(img):
    """True when all four corners are near-white, i.e. a render on a plain white backdrop."""
    x, y = img.width - 1, img.height - 1
    return all(min(img.getpixel(p)) >= 240 for p in ((0, 0), (x, 0), (0, y), (x, y)))


def find_source(stem):
    for ext in EXTS:
        p = SRC / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def load(stem, w, h, label, make_placeholder, keep_alpha=False):
    src = find_source(stem)
    if src:
        img = ImageOps.exif_transpose(Image.open(src))
        if img.mode in ("RGBA", "LA", "P"):
            # Cut-out car render: put it on white and fit the whole car in the frame (no cropping),
            # with a small margin so bumpers don't touch the card edge.
            img = img.convert("RGBA")
            solid = img.getchannel("A").point(lambda a: 255 if a > 40 else 0)  # ignore faint shadow/haze
            img = img.crop(solid.getbbox() or (0, 0, *img.size))
            if keep_alpha:  # hero floats on the page's gradient: keep it transparent
                car = ImageOps.contain(img, (int(w * 0.96), int(h * 0.96)), Image.LANCZOS)
                canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                canvas.paste(car, ((w - car.width) // 2, h - car.height - int(h * 0.02)))
                return canvas, str(src.name)
            bg = Image.new("RGB", img.size, "#ffffff")
            bg.paste(img, mask=img.getchannel("A"))
            return fit_on_white(bg, w, h), str(src.name)
        img = img.convert("RGB")
        if is_white_studio(img):  # studio render on plain white: same treatment as a cut-out
            content = ImageChops.difference(img, Image.new("RGB", img.size, "#ffffff")).convert("L").point(lambda v: 255 if v > 12 else 0)
            return fit_on_white(img.crop(content.getbbox() or (0, 0, *img.size)), w, h), str(src.name)
        return ImageOps.fit(img, (w, h), Image.LANCZOS), str(src.name)
    if make_placeholder:
        return placeholder(w, h, label), "placeholder"
    return None, None


def main():
    make_ph = "--placeholder" in sys.argv[1:]
    OUT.mkdir(parents=True, exist_ok=True)
    for stem, ((aw, ah), widths, budget, label) in SPECS.items():
        big_w = max(widths)
        base, origin = load(stem, big_w, big_w * ah // aw, label, make_ph, keep_alpha=(stem == "hero"))
        if base is None:
            print(f"skip {stem}: no source in assets/src/")
            continue
        for w in widths:
            img = base.resize((w, w * ah // aw), Image.LANCZOS)
            data = encode(img, "WEBP", budget)
            if len(data) > budget:
                print(f"WARNING {stem}-{w}.webp is {len(data) // 1024} KB, over the {budget // 1024} KB budget")
            (OUT / f"{stem}-{w}.webp").write_bytes(data)
            print(f"{stem}-{w}.webp  {len(data) // 1024} KB  ({origin})")
    (w, h), budget, label = OG
    # real og photo, else real hero photo, else placeholder
    base, origin = load("og", w, h, label, False)
    if base is None:
        base, origin = load("hero", w, h, label, False)
    if base is None and make_ph:
        base, origin = placeholder(w, h, label), "placeholder"
    if base is not None:
        data = encode(base, "JPEG", budget)
        (OUT / "og.jpg").write_bytes(data)
        print(f"og.jpg  {len(data) // 1024} KB  ({origin})")


if __name__ == "__main__":
    main()
