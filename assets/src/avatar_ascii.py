"""Converts the avatar photo into an ASCII portrait.

Used by ascii_hero.py, where the liquid structure condenses into this portrait.
Each row comes back as characters plus a parallel tone string ("0"-"5" grey
levels, "c" for the cyan accent).

Pipeline: separate the subject from the flat studio background by colour
distance (flood-filled from the borders), equalise and sharpen inside the
subject, darken along edges, average each character cell and map brightness to
a density ramp. Blue irises, found at full resolution, become the cyan accent.

Requires Pillow. Preview from the repository root:

    python assets/src/avatar_ascii.py [path/to/avatar.jpg] [--rows 44]
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

HERE = Path(__file__).resolve().parent
RAMP = " .,:;irsXA253hMHGS#9B&@"
CELL_ASPECT = 0.55  # monospace advance / line height of the character grid
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


def convert(path, rows, keep=1.0, gamma=None, edge=None, head_margin=None):
    """keep: fraction of the subject height to use from the top (e.g. 0.85 drops the shirt).

    head_margin: if set, crop the width to the head (hair and ears, measured on the upper
    part of the subject) plus this fraction of its width on each side, so wide shoulders
    do not squash the portrait.
    """
    img = Image.open(path).convert("RGB")
    subject, bg = subject_mask(img)
    box = subject.getbbox()
    box = (box[0], box[1], box[2], box[1] + round((box[3] - box[1]) * keep))
    if head_margin is not None:
        top_rows = subject.crop((0, box[1], subject.width, box[1] + round((box[3] - box[1]) * 0.62)))
        hb = top_rows.getbbox()
        pad = round((hb[2] - hb[0]) * head_margin)
        box = (max(0, hb[0] - pad), box[1], min(subject.width, hb[2] + pad), box[3])
    img, subject = img.crop(box), subject.crop(box)
    w, h = img.size
    cols = round(rows * (w / h) / CELL_ASPECT)
    # Filters are tuned for ~9 px per character cell; scale them for larger photos so the
    # fine texture of the fabric is averaged out instead of becoming noise.
    k = max(1.0, (h / rows) / 18)

    grey = ImageOps.grayscale(img)
    # Equalise inside the subject only, so skin tones spread across the whole ramp.
    lum = ImageOps.equalize(grey, mask=subject).filter(ImageFilter.UnsharpMask(radius=3 * k, percent=140, threshold=2))
    # Darken along edges so features (eyelids, nose, mouth) are outlined by sparser glyphs.
    edges = grey.filter(ImageFilter.GaussianBlur(1.5 * k)).filter(ImageFilter.FIND_EDGES)
    edges = edges.point(lambda v: min(255, int(v * 5 / k))).filter(ImageFilter.GaussianBlur(1.2 * k))
    lum = Image.composite(Image.new("L", lum.size, 0), lum, edges.point(lambda v: int(v * (EDGE_WEIGHT if edge is None else edge))))
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
    # Irises: blue-dominant pixels at full resolution, carried down as coverage so
    # small eyes survive the downsampling.
    blue_dom = Image.new("L", img.size, 0)
    src, dst = img.load(), blue_dom.load()
    for yy in range(img.size[1]):
        for xx in range(img.size[0]):
            r_, g_, b_ = src[xx, yy]
            if b_ - max(r_, g_) > 8 and b_ > 70:
                dst[xx, yy] = 255
    iris_cover = blue_dom.resize((cols, rows), Image.BOX)

    out = []
    for r in range(rows):
        chars, tones = [], []
        for c in range(cols):
            if cover.getpixel((c, r)) < 110:
                chars.append(" ")
                tones.append(" ")
                continue
            v = (small.getpixel((c, r)) - lo) / max(1, hi - lo)
            v = min(1.0, max(0.0, v)) ** (gamma or GAMMA)
            idx = max(1, min(len(RAMP) - 1, round(v * (len(RAMP) - 1))))
            iris = iris_cover.getpixel((c, r)) > 50
            chars.append(RAMP[idx])
            tones.append("c" if iris else str(min(5, int(v * 6))))
        out.append({"text": "".join(chars).rstrip(), "tone": "".join(tones)[:len("".join(chars).rstrip())]})
    return out, cols


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("image", nargs="?", default=str(HERE.parent / "github-ascii-profile.jpg"))
    ap.add_argument("--rows", type=int, default=44)
    args = ap.parse_args()
    rows, cols = convert(args.image, args.rows)
    for row in rows:
        print(row["text"])
    print(f"{cols}x{len(rows)}")


if __name__ == "__main__":
    main()
