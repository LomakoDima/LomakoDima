"""Converts the avatar photo into an ASCII portrait for the profile card.

Writes assets/src/avatar.json: one entry per row with the characters and a
parallel tone string ("0"-"5" grey levels, "c" for the cyan accent). card.py
turns that into SVG text, so the daily workflow needs no image library.

Pipeline: separate the subject from the flat studio background by colour
distance (flood-filled from the borders), boost local detail with an unsharp
mask, average each character cell, and map brightness to a density ramp.
Blue irises become the cyan accent.

Requires Pillow. Run from the repository root:

    python assets/src/avatar_ascii.py [path/to/avatar.jpg] [--rows 30]
"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

HERE = Path(__file__).resolve().parent
RAMP = " .,:;irsXA253hMHGS#9B&@"
CELL_ASPECT = 0.55  # monospace advance / line height used by card.py
EDGE_WEIGHT = 0.6  # how strongly edges darken the portrait
GAMMA = 1.3  # >1 pushes mid-tones toward sparser glyphs


def subject_mask(img, tol=30):
    """Background = pixels close to the border colour that touch the border."""
    w, h = img.size
    border = [img.getpixel((x, 0)) for x in range(w)] + [img.getpixel((x, h - 1)) for x in range(w)]
    border += [img.getpixel((0, y)) for y in range(h)] + [img.getpixel((w - 1, y)) for y in range(h)]
    bg = tuple(sorted(c[i] for c in border)[len(border) // 2] for i in range(3))
    near = Image.new("L", img.size, 0)
    px, out = img.load(), near.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) < tol:
                out[x, y] = 255
    # Keep only background regions connected to the border.
    fill = near.copy()
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0)):
        if fill.getpixel(seed) == 255:
            ImageDraw.floodfill(fill, seed, 128)
    bgmask = fill.point(lambda v: 255 if v == 128 else 0)
    subject = ImageOps.invert(bgmask).filter(ImageFilter.MedianFilter(5))
    return subject, bg


def convert(path, rows):
    img = Image.open(path).convert("RGB")
    subject, bg = subject_mask(img)
    box = subject.getbbox()
    img, subject = img.crop(box), subject.crop(box)
    w, h = img.size
    cols = round(rows * (w / h) / CELL_ASPECT)

    grey = ImageOps.grayscale(img)
    # Equalise inside the subject only, so skin tones spread across the whole ramp.
    lum = ImageOps.equalize(grey, mask=subject).filter(ImageFilter.UnsharpMask(radius=3, percent=140, threshold=2))
    # Darken along edges so features (eyelids, nose, mouth) are outlined by sparser glyphs.
    edges = grey.filter(ImageFilter.GaussianBlur(1.5)).filter(ImageFilter.FIND_EDGES)
    edges = edges.point(lambda v: min(255, v * 5)).filter(ImageFilter.GaussianBlur(1.2))
    lum = Image.composite(Image.new("L", lum.size, 0), lum, edges.point(lambda v: int(v * EDGE_WEIGHT)))
    # Stretch contrast using the subject's own histogram, not the background's.
    hist = lum.histogram(mask=subject)
    total = sum(hist)
    acc, lo, hi = 0, 0, 255
    for v, n in enumerate(hist):
        acc += n
        if acc < total * 0.02:
            lo = v
        if acc < total * 0.98:
            hi = v
    small = lum.resize((cols, rows), Image.BOX)
    cover = subject.resize((cols, rows), Image.BOX)
    colour = img.resize((cols, rows), Image.BOX)

    out = []
    for r in range(rows):
        chars, tones = [], []
        for c in range(cols):
            if cover.getpixel((c, r)) < 110:
                chars.append(" ")
                tones.append(" ")
                continue
            v = (small.getpixel((c, r)) - lo) / max(1, hi - lo)
            v = min(1.0, max(0.0, v)) ** GAMMA
            idx = max(1, min(len(RAMP) - 1, round(v * (len(RAMP) - 1))))
            red, green, blue = colour.getpixel((c, r))
            iris = blue - max(red, green) > 4 and blue > 60
            chars.append(RAMP[idx])
            tones.append("c" if iris else str(min(5, int(v * 6))))
        out.append({"text": "".join(chars).rstrip(), "tone": "".join(tones)[:len("".join(chars).rstrip())]})
    return out, cols


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("image", nargs="?", default=str(HERE.parent / "github_avatar_under_1mb.jpg"))
    ap.add_argument("--rows", type=int, default=44)
    args = ap.parse_args()
    rows, cols = convert(args.image, args.rows)
    (HERE / "avatar.json").write_text(json.dumps({"cols": cols, "rows": rows}, ensure_ascii=False, indent=0),
                                      encoding="utf-8")
    for row in rows:
        print(row["text"])
    print(f"{cols}x{len(rows)} -> avatar.json")


if __name__ == "__main__":
    main()
