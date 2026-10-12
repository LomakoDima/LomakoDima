"""Renders the animated ASCII hero banner: assets/hero.gif.

The artwork is a liquid structure that becomes a self-portrait. Three linked
masses and four droplets flow, split and fuse; then they gather into one mass,
the portrait (made by avatar_ascii.py from the avatar photo) crystallises out of
the characters from the centre outwards, holds while a scan line passes, and
dissolves back into liquid.

Every frame is ray-marched in 3D and shaded into characters on a fixed
monospace grid: brightness picks a glyph from a density ramp and a grey level,
depth fades both. Nothing is drawn except text characters; the typography
around the artwork reuses the wordmark geometry from build.py.

All motion is periodic over one loop, so the GIF repeats without a jump.

Requires Pillow (pip install pillow). Run from the repository root:

    python assets/src/ascii_hero.py
    python assets/src/ascii_hero.py --frames 4 --png    # quick preview frames only

Fonts: JetBrains Mono for the character grid and labels, Arial (or a similar
sans) for the descriptor. Both are searched in the usual system locations;
pass --mono / --sans to point at specific files.
"""

import argparse
import glob
import math
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import avatar_ascii  # noqa: E402  (photo -> ASCII portrait)
import build  # noqa: E402  (design tokens and wordmark geometry)

OUT = Path(__file__).resolve().parent.parent

W_PX, H_PX = 1200, 480
LOOP_FRAMES = 150
FRAME_MS = 70  # GIF delays are in 10 ms steps; 150 x 70 ms = 10.5 s per loop
RAMP = " .,:;irsXA253hMHGS#9B&@"
GRID_FONT_PX = 10
AVATAR = OUT / "github_avatar_under_1mb.jpg"
FIELD = (676, 84, 1150, 412)  # x0, y0, x1, y1 of the character grid
FIG = (690, 96, 1144, 398)    # registration frame around the artwork


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


BG, LINE, TEXT, MUTED, DIM, ACCENT = (hexrgb(c) for c in
                                      (build.BG, build.LINE, build.TEXT, build.MUTED, build.DIM, build.ACCENT))


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

def find_font(names):
    roots = [os.environ.get("WINDIR", r"C:\Windows") + r"\Fonts",
             os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
             os.path.expanduser("~/Library/Fonts"), "/Library/Fonts", "/System/Library/Fonts",
             os.path.expanduser("~/.local/share/fonts"), "/usr/share/fonts", "/usr/local/share/fonts"]
    # JetBrains IDEs bundle JetBrains Mono with their runtime.
    roots += glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Programs\*\jbr\lib\fonts"))
    roots += glob.glob(r"C:\Program Files\JetBrains\*\jbr\lib\fonts")
    for name in names:
        for root in roots:
            hits = glob.glob(os.path.join(root, "**", name), recursive=True)
            if hits:
                return hits[0]
    return None


# ---------------------------------------------------------------------------
# Static layer: typography, rules and the figure frame, drawn at 3x and
# downsampled for clean anti-aliasing.
# ---------------------------------------------------------------------------

SS = 3


def spaced(draw, x, y, s, font, fill, spacing=0.0, anchor="ls"):
    """Draws text with letter-spacing (in final px) at a baseline, like the SVG version."""
    x, y, spacing = x * SS, y * SS, spacing * SS
    widths = [font.getlength(ch) for ch in s]
    total = sum(widths) + spacing * (len(s) - 1)
    if anchor[0] == "r":
        x -= total
    elif anchor[0] == "m":
        x -= total / 2
    for ch, w in zip(s, widths):
        draw.text((x, y), ch, font=font, fill=fill, anchor="ls")
        x += w + spacing


def stroke_wordmark(draw, x0, baseline):
    """Strokes the wordmark from build.wordmark()'s own SVG path data."""
    svg, _ = build.wordmark(0, 0)
    d = re.search(r'<path d="([^"]+)"', svg).group(1)
    w = build.W * SS

    def P(x, y):
        return ((x0 + x) * SS, (baseline + y) * SS)

    for sub in re.findall(r"M[^M]+", d):
        toks = re.findall(r"[MVHAZ]|-?\d*\.?\d+", sub)
        i, cur, start, segs = 0, None, None, []
        while i < len(toks):
            cmd = toks[i]
            if cmd == "M":
                cur = start = (float(toks[i + 1]), float(toks[i + 2])); i += 3
            elif cmd in "VH":
                v = float(toks[i + 1])
                nxt = (cur[0], v) if cmd == "V" else (v, cur[1])
                segs.append(("L", cur, nxt)); cur = nxt; i += 2
            elif cmd == "A":
                # Every arc in the wordmark is a semicircle: centre is the chord midpoint.
                sweep, ex, ey = int(toks[i + 5]), float(toks[i + 6]), float(toks[i + 7])
                segs.append(("A", cur, (ex, ey), sweep)); cur = (ex, ey); i += 8
            else:
                i += 1
        for k, seg in enumerate(segs):
            if seg[0] == "L":
                draw.line([P(*seg[1]), P(*seg[2])], fill=TEXT, width=round(w))
                # square (mitred) corner where this straight stroke meets another straight stroke
                if k + 1 < len(segs) and segs[k + 1][0] == "L":
                    px, py = P(*seg[2])
                    draw.rectangle((px - w / 2, py - w / 2, px + w / 2, py + w / 2), fill=TEXT)
            else:
                (x1, y1), (x2, y2), sweep = seg[1], seg[2], seg[3]
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                r = math.hypot(x1 - cx, y1 - cy)
                a0 = math.degrees(math.atan2(y1 - cy, x1 - cx))
                lo, hi = (a0, a0 + 180) if sweep else (a0 - 180, a0)
                px, py = P(cx, cy)
                ro = r * SS + w / 2  # Pillow strokes arcs inward from the bounding box
                draw.arc((px - ro, py - ro, px + ro, py + ro), lo, hi, fill=TEXT, width=round(w))
    for m in re.finditer(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="[\d.]+"(?: fill="([^"]+)")?', svg):
        x, y, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
        fill = hexrgb(m.group(4)) if m.group(4) and m.group(4).startswith("#") else TEXT
        a, b = P(x, y)
        draw.rectangle((a, b, a + s * SS - 1, b + s * SS - 1), fill=fill)


def static_layers(mono_path, sans_path):
    """Returns (base RGB image, overlay RGBA image drawn above the character grid)."""
    big = Image.new("RGB", (W_PX * SS, H_PX * SS), BG)
    d = ImageDraw.Draw(big)
    mono13 = ImageFont.truetype(mono_path, 13 * SS)
    sans26 = ImageFont.truetype(sans_path, 26 * SS)
    L, R = 56, 1144

    spaced(d, L, 46, "DIMALAB / ENGINEERING", mono13, MUTED, 2.6)
    spaced(d, 600, 46, "PROFILE — Nº 01", mono13, DIM, 2.6, "ms")
    spaced(d, R, 46, "KZ / UTC+5", mono13, MUTED, 2.6, "rs")
    d.rectangle((L * SS, 66 * SS - 1, R * SS, 66 * SS + 1), fill=LINE)
    spaced(d, L, 130, "INDEPENDENT DEVELOPER", mono13, ACCENT, 2.6)
    stroke_wordmark(d, L, 282)
    spaced(d, L - 1, 334, "Software developer.", sans26, TEXT)
    spaced(d, L - 1, 368, "Building tools, engines & experiments.", sans26, MUTED)
    d.rectangle((L * SS, 420 * SS - 1, R * SS, 420 * SS + 1), fill=LINE)
    for x, n, label in ((L, "01", "ENGINE TOOLING"), (L + 363, "02", "WINDOWS UTILITIES"),
                        (L + 726, "03", "MINECRAFT SYSTEMS")):
        spaced(d, x, 452, n, mono13, ACCENT, 2.6)
        spaced(d, x + 34, 452, label, mono13, MUTED, 2.6)
    base = big.resize((W_PX, H_PX), Image.LANCZOS)

    over = Image.new("RGBA", (W_PX * SS, H_PX * SS), (0, 0, 0, 0))
    o = ImageDraw.Draw(over)
    fx0, fy0, fx1, fy1 = FIG
    for x, y in ((fx0, fy0), (fx1, fy0), (fx0, fy1), (fx1, fy1)):
        o.rectangle(((x - 7) * SS, (y - 7) * SS, (x + 7) * SS, (y + 7) * SS), fill=BG + (255,))
        o.rectangle(((x - 5) * SS, y * SS - 1, (x + 5) * SS, y * SS + 1), fill=DIM + (255,))
        o.rectangle((x * SS - 1, (y - 5) * SS, x * SS + 1, (y + 5) * SS), fill=DIM + (255,))
    return base, over.resize((W_PX, H_PX), Image.LANCZOS)


# ---------------------------------------------------------------------------
# Simulation: a smooth union of seven spheres (a signed distance field).
# t runs over [0, 1); every term below has an integer frequency in t, so the
# last frame flows straight back into the first.
# ---------------------------------------------------------------------------

TAU = 2 * math.pi
BLEND = 0.38     # smooth-union radius: how readily bodies fuse into one surface
RIPPLE = 0.035   # surface ripple depth


def smin(a, b, k=BLEND):
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k * 0.25


def smoothstep(a, b, x):
    x = min(1.0, max(0.0, (x - a) / (b - a)))
    return x * x * (3 - 2 * x)


def gather(t):
    """How far the bodies have pulled together into one head-sized mass (0..1)."""
    return smoothstep(0.16, 0.38, t) * (1 - smoothstep(0.80, 0.98, t))


def reveal(t):
    """How much of the portrait has crystallised out of the liquid (0..1)."""
    return smoothstep(0.30, 0.46, t) * (1 - smoothstep(0.78, 0.93, t))


def bodies(t):
    a = TAU * t
    g = gather(t)
    out = [
        # three linked masses that form the body
        ((-0.55 + 0.25 * math.sin(a), 0.20 * math.sin(2 * a), 0.15 * math.cos(a)), 0.52 + 0.04 * math.sin(2 * a)),
        ((0.50 + 0.22 * math.cos(a + 1), -0.22 * math.sin(a + 0.5), -0.12 * math.sin(a)), 0.48 + 0.05 * math.cos(2 * a + 1)),
        ((0.05 * math.sin(2 * a), 0.30 * math.sin(a + 2.4), 0.25 * math.cos(a + 0.7)), 0.38 + 0.04 * math.sin(3 * a)),
    ]
    # droplets on tilted orbits whose radius swings from inside the body to well outside it
    for r, turns, phase, tilt, beat in ((0.20, 1, 0.0, 0.25, 1), (0.17, -1, 2.1, -0.22, 2),
                                        (0.14, 2, 4.0, 0.32, 1), (0.12, -2, 1.0, 0.10, 2)):
        ang = turns * a + phase
        rad = 0.85 + 0.45 * math.sin(beat * a + phase)
        out.append(((rad * math.cos(ang) * 1.25, rad * math.sin(ang) * tilt, rad * math.sin(ang) * 0.7), r))
    if g:
        # Pull everything towards one mass where the head will appear; droplets melt in.
        head, head_r = (0.0, 0.05, 0.0), 0.72
        out = [(tuple(c + (hc - c) * g for c, hc in zip(centre, head)),
                r + ((head_r if i < 3 else 0.02) - r) * g) for i, (centre, r) in enumerate(out)]
    return out


def make_scene(t):
    B = bodies(t)
    a = TAU * t

    def scene(x, y, z):
        d = 1e9
        for (cx, cy, cz), r in B:
            d = smin(d, math.sqrt((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2) - r)
        d += RIPPLE * math.sin(7 * x + 2 * a) * math.sin(5.6 * y - a) * math.sin(6.3 * z + 3 * a)
        return d * 0.8

    return scene


def shade(t, cols, rows, aspect):
    """Returns rows x cols cells: None for empty space, else (luminance 0..1, is_cyan)."""
    scene = make_scene(t)
    yaw = 0.30 * math.sin(TAU * t)
    cyw, syw = math.cos(yaw), math.sin(yaw)
    dist, fov = 2.55, 0.50
    ox, oy, oz = dist * syw, 0.0, dist * cyw
    lx, ly, lz = -0.55, 0.65, 0.52
    ln = math.sqrt(lx * lx + ly * ly + lz * lz); lx, ly, lz = lx / ln, ly / ln, lz / ln
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            u = (c - cols / 2 + 0.5) / (rows / 2) * aspect
            v = -(r - rows / 2 + 0.5) / (rows / 2)
            dx, dy, dz = u * fov, v * fov, -1.0
            n = math.sqrt(dx * dx + dy * dy + dz * dz); dx, dy, dz = dx / n, dy / n, dz / n
            dx, dz = dx * cyw + dz * syw, -dx * syw + dz * cyw
            b = ox * dx + oy * dy + oz * dz
            disc = b * b - (ox * ox + oy * oy + oz * oz - 2.3 ** 2)
            hit = False
            if disc > 0:
                tt, tmax = max(0.0, -b - math.sqrt(disc)), -b + math.sqrt(disc)
                for i in range(64):
                    x, y, z = ox + dx * tt, oy + dy * tt, oz + dz * tt
                    d = scene(x, y, z)
                    if d < 0.003:
                        hit = True
                        break
                    tt += max(d, 0.004)
                    if tt > tmax:
                        break
            if not hit:
                row.append(None)
                continue
            e = 0.003
            nx = scene(x + e, y, z) - scene(x - e, y, z)
            ny = scene(x, y + e, z) - scene(x, y - e, z)
            nz = scene(x, y, z + e) - scene(x, y, z - e)
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
            nx, ny, nz = nx / nl, ny / nl, nz / nl
            diff = max(0.0, nx * lx + ny * ly + nz * lz)
            diff += 0.28 * max(0.0, nx * 0.45 - ny * 0.75 + nz * 0.48)  # soft bounce light from below
            hx, hy, hz = lx - dx, ly - dy, lz - dz
            hl = math.sqrt(hx * hx + hy * hy + hz * hz) or 1
            spec = max(0.0, (nx * hx + ny * hy + nz * hz) / hl) ** 24
            rim = (1 + (nx * dx + ny * dy + nz * dz)) ** 3 * 0.18
            light = min(1.0, diff * 0.85 + spec * 0.6 + rim)
            occl = 1 - i / 64
            fog = max(0.0, min(1.0, (tt - (dist - 0.9)) / 1.9))
            lum = (0.14 + 0.86 * light) * (0.55 + 0.45 * occl) * (1 - 0.7 * fog)
            pulse = math.sin(2.6 * x - 0.9 * y + 0.6 * z - TAU * 2 * t)  # a scan band sweeping the surface
            row.append((lum, pulse > 0.985 and light > 0.3))
        grid.append(row)
    return grid


# ---------------------------------------------------------------------------
# Frames
# ---------------------------------------------------------------------------

def portrait_grid(rows):
    """The avatar as (char, tone) cells, `rows` tall, from avatar_ascii's pipeline."""
    # Head and neck only, with lighter edges and gamma tuned for this coarse grid.
    art, cols = avatar_ascii.convert(str(AVATAR), rows, keep=0.84, gamma=0.92, edge=0.22)
    return [[(ch, tn) for ch, tn in zip(row["text"].ljust(cols), row["tone"].ljust(cols))] for row in art], cols


TONE_GREY = {"0": 74, "1": 99, "2": 128, "3": 162, "4": 199, "5": 244}


def render_frame(t, base, over, font, cw, ch, cols, rows, face):
    img = base.copy()
    d = ImageDraw.Draw(img)
    x0, y0 = FIELD[0], FIELD[1]
    grid_face, face_cols = face
    fr0, fc0 = (rows - len(grid_face)) // 2, (cols - face_cols) // 2
    p = reveal(t)
    hold = smoothstep(0.46, 0.50, t) * (1 - smoothstep(0.74, 0.78, t))
    scan = (t - 0.47) / 0.28 * (rows + 6) - 3            # scan line row during the hold
    glitch = {0.56: (11, 2), 0.66: (19, -2)}             # time -> (row, shift) for one frame
    shift_row = next((v for k, v in glitch.items() if abs(t - k) < 0.004), None)
    for r, row in enumerate(shade(t, cols, rows, cw / ch)):
        for c, cell in enumerate(row):
            x, y = x0 + c * cw, y0 + r * ch
            fr, fc = r - fr0, c - fc0
            if shift_row and r == shift_row[0] + fr0:
                fc -= shift_row[1]
            in_face = 0 <= fr < len(grid_face) and 0 <= fc < face_cols
            # Crystallisation order: from the centre of the face outwards, with jitter.
            hsh = math.sin(c * 12.9898 + r * 78.233) * 43758.5453
            f = hsh - math.floor(hsh)
            radial = math.hypot((c - cols / 2) / (cols / 2), (r - rows / 2) / (rows / 2)) / 1.42
            order = 0.62 * radial + 0.38 * f
            if p > 0 and order < p:
                glyph, tone = grid_face[fr][fc] if in_face else (" ", " ")
                if p < 1 and order > p - 0.035 and (glyph != " " or cell) and f < 0.6:
                    # The crystallisation front: brief cyan sparks where there is matter.
                    d.text((x, y), RAMP[int(f * 9973) % (len(RAMP) - 1) + 1], font=font, fill=ACCENT)
                elif glyph != " ":
                    if tone == "c":
                        col = ACCENT
                    else:
                        g = TONE_GREY.get(tone, 160)
                        if hold and abs(r - scan) < 1.0:
                            g = min(255, g + 70)  # scan line brightens the row it passes
                        col = (g, g, min(255, g + 3))
                    d.text((x, y), glyph, font=font, fill=col)
                elif f > 0.975:
                    d.text((x, y), ".", font=font, fill=(52, 52, 56))
                continue
            if cell is None:
                # Dust: sparse punctuation in empty space, twinkling with the loop.
                if f > 0.965:
                    g = int(38 + 46 * (0.5 + 0.5 * math.sin(TAU * (t + f * 7))))
                    d.text((x, y), ".`'"[int(f * 1000) % 3], font=font, fill=(g, g, g + 4))
                continue
            lum, cyan = cell
            bayer = ((0, 2), (3, 1))[r % 2][c % 2] / 4 - 0.375  # breaks up flat runs of one glyph
            idx = max(1, min(len(RAMP) - 1, int(lum ** 0.85 * (len(RAMP) - 1) + 0.5 + bayer * 1.6)))
            g = int(70 + 185 * min(1.0, lum * 1.1))
            d.text((x, y), RAMP[idx], font=font, fill=ACCENT if cyan else (g, g, min(255, g + 3)))
    img.paste(over, (0, 0), over)
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mono", help="monospace .ttf (default: JetBrains Mono, Cascadia Mono or Consolas)")
    ap.add_argument("--sans", help="sans .ttf for the descriptor (default: Arial, Helvetica, Liberation Sans)")
    ap.add_argument("--frames", type=int, default=LOOP_FRAMES)
    ap.add_argument("--png", action="store_true", help="write PNG frames to --png-dir instead of the GIF")
    ap.add_argument("--png-dir", default=".")
    args = ap.parse_args()

    mono = args.mono or find_font(["JetBrainsMono-Regular.ttf", "CascadiaMono.ttf", "consola.ttf",
                                   "DejaVuSansMono.ttf", "Menlo.ttc"])
    sans = args.sans or find_font(["arial.ttf", "Arial.ttf", "Helvetica.ttc", "LiberationSans-Regular.ttf",
                                   "DejaVuSans.ttf"])
    if not mono or not sans:
        sys.exit("error: fonts not found; pass --mono and --sans")
    font = ImageFont.truetype(mono, GRID_FONT_PX)
    cw = font.getlength("M")
    ch = round(GRID_FONT_PX * 1.12)
    cols = int((FIELD[2] - FIELD[0]) // cw)
    rows = int((FIELD[3] - FIELD[1]) // ch)
    base, over = static_layers(mono, sans)
    face = portrait_grid(rows)

    frames = []
    for i in range(args.frames):
        t = i / args.frames
        frames.append(render_frame(t, base, over, font, cw, ch, cols, rows, face))
        print(f"\rframe {i + 1}/{args.frames}", end="", file=sys.stderr)
    print(file=sys.stderr)

    if args.png:
        for i, im in enumerate(frames):
            im.save(Path(args.png_dir) / f"hero_{i:03d}.png")
        print(f"{cols}x{rows} character grid, {Path(mono).name}")
        return

    # One shared palette (no dithering) keeps glyph edges clean and lets the
    # GIF encoder store only the changed region of each frame.
    sample = Image.new("RGB", (W_PX, H_PX * 3))
    for k, i in enumerate((0, len(frames) // 3, len(frames) * 3 // 5)):  # liquid, gathering, portrait
        sample.paste(frames[i], (0, k * H_PX))
    palette = sample.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal_frames = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    out = OUT / "hero.gif"
    pal_frames[0].save(out, save_all=True, append_images=pal_frames[1:], duration=FRAME_MS, loop=0,
                       optimize=False, disposal=1)
    print(f"{out.name}: {W_PX}x{H_PX}, {len(frames)} frames x {FRAME_MS} ms, "
          f"{cols}x{rows} character grid, {out.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
