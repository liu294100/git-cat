"""Generate GitCat icons (PNG / ICO / ICNS) into assets/. Requires Pillow (dev-time only)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
S = 1024


def gradient(size: int, c1: tuple, c2: tuple) -> Image.Image:
    """Diagonal gradient from c1 (top-left) to c2 (bottom-right)."""
    g = Image.new("RGBA", (size, size))
    px = g.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)) + (255,)
    return g


def build_icon() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # Tile: violet -> cyan gradient with rounded corners.
    tile = gradient(S, (124, 58, 237), (34, 211, 238))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((40, 40, S - 40, S - 40), radius=230, fill=255)
    img.paste(tile, (0, 0), mask)
    d = ImageDraw.Draw(img)

    # Cat head: ears + face in deep navy.
    navy = (15, 18, 40, 255)
    d.polygon([(230, 470), (290, 170), (450, 330)], fill=navy)
    d.polygon([(794, 470), (734, 170), (574, 330)], fill=navy)
    d.ellipse((200, 270, 824, 860), fill=navy)
    # Inner ears.
    pink = (244, 114, 182, 255)
    d.polygon([(275, 400), (305, 245), (395, 335)], fill=pink)
    d.polygon([(749, 400), (719, 245), (629, 335)], fill=pink)

    # Eyes with glow.
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for cx in (390, 634):
        gd.ellipse((cx - 70, 470, cx + 70, 610), fill=(34, 211, 238, 200))
    glow = glow.filter(ImageFilter.GaussianBlur(28))
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img)
    for cx in (390, 634):
        d.ellipse((cx - 52, 488, cx + 52, 592), fill=(103, 232, 249, 255))
        d.ellipse((cx - 14, 500, cx + 14, 580), fill=navy)

    # Git branch graph as the nose/whisker motif.
    white = (255, 255, 255, 255)
    d.line((512, 650, 512, 790), fill=white, width=26)
    d.line((512, 690, 620, 760), fill=white, width=26)
    for x, y, r in ((512, 650, 30), (512, 795, 30), (628, 765, 30)):
        d.ellipse((x - r, y - r, x + r, y + r), fill=white)
        d.ellipse((x - r + 12, y - r + 12, x + r - 12, y + r - 12), fill=(139, 92, 246, 255))
    # Whiskers.
    for y, dy in ((660, -18), (700, 0), (740, 18)):
        d.line((150, y + dy, 330, y), fill=(255, 255, 255, 170), width=12)
        d.line((694, y, 874, y + dy), fill=(255, 255, 255, 170), width=12)
    return img


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    master = build_icon()
    lanczos = Image.Resampling.LANCZOS
    master.resize((512, 512), lanczos).save(ASSETS / "gitcat.png", "PNG")
    master.resize((64, 64), lanczos).save(ASSETS / "gitcat-64.png", "PNG")
    # Individual sizes so Qt picks a crisp bitmap for title bar (16/24), taskbar (32/48) and Alt+Tab (256).
    icons = ASSETS / "icons"
    icons.mkdir(exist_ok=True)
    for size in (16, 20, 24, 32, 40, 48, 64, 96, 128, 256, 512, 1024):
        master.resize((size, size), lanczos).save(icons / f"gitcat-{size}.png", "PNG")
    master.save(ASSETS / "gitcat.ico", "ICO",
                sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    master.save(ASSETS / "gitcat.icns", "ICNS")
    for p in sorted(ASSETS.glob("gitcat*")):
        print(f"  {p.relative_to(ROOT)} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
