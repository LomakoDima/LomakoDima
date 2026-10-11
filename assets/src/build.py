"""Generates the profile's SVG assets (hero, StoryModEngine plate, footer).

Standard library only. Run from the repository root:

    python assets/src/build.py

The particle layout is seeded, so the output is reproducible; change SEED for a new variation.
"""

import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent
SEED = 1107

# Design tokens
BG = "#0A0A0B"
LINE = "#25272C"
LINE_SOFT = "#17181B"
TEXT = "#F4F5F7"
MUTED = "#8B9099"
DIM = "#5A5E66"
ACCENT = "#3FD0FF"

MONO = "'JetBrains Mono','SFMono-Regular',ui-monospace,Menlo,Consolas,'Liberation Mono',monospace"
SANS = "'Inter','Helvetica Neue',Helvetica,Arial,'Segoe UI',sans-serif"


def f(v):
    """Compact number formatting for path data."""
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


# ---------------------------------------------------------------------------
# Wordmark: a custom monoline geometric "DimaLab." built from strokes, so it
# renders identically everywhere without depending on installed fonts.
# ---------------------------------------------------------------------------

CAP = 118.0   # cap height
XH = 84.0     # x-height
W = 19.0      # stroke weight
GAP = 13.0    # space between glyph outer edges


def wordmark(x0, baseline, scale=1.0, color=TEXT, accent=ACCENT):
    """Returns (svg_group, width) for the wordmark with its baseline at `baseline`."""
    h = W / 2
    top = -CAP
    xt = -XH
    paths = []
    x = 0.0

    # D
    r = (CAP - W) / 2
    sx = x + h
    k = sx + 12
    paths.append(f"M{f(sx)} {f(top)}V0")
    paths.append(f"M{f(sx)} {f(top + h)}H{f(k)}A{f(r)} {f(r)} 0 0 1 {f(k)} {f(-h)}H{f(sx)}")
    x = k + r + h + GAP

    # i (square tittle)
    sx = x + h
    paths.append(f"M{f(sx)} {f(xt)}V0")
    dots = [(x, top, W)]
    x += W + GAP

    # m (flat-topped first stem, two round arches)
    rm = 20.0
    sx = x + h
    cy = xt + h + rm
    paths.append(f"M{f(sx)} 0V{f(xt)}")
    paths.append(f"M{f(sx)} {f(cy)}A{f(rm)} {f(rm)} 0 0 1 {f(sx + 2 * rm)} {f(cy)}V0")
    paths.append(f"M{f(sx + 2 * rm)} {f(cy)}A{f(rm)} {f(rm)} 0 0 1 {f(sx + 4 * rm)} {f(cy)}V0")
    x = sx + 4 * rm + h + GAP

    def bowl(cx):
        ra = (XH - W) / 2
        cyb = -XH / 2
        return (f"M{f(cx - ra)} {f(cyb)}A{f(ra)} {f(ra)} 0 1 0 {f(cx + ra)} {f(cyb)}"
                f"A{f(ra)} {f(ra)} 0 1 0 {f(cx - ra)} {f(cyb)}Z"), ra

    # a (single storey: bowl + right stem)
    ra = (XH - W) / 2
    cx = x + h + ra
    p, _ = bowl(cx)
    paths.append(p)
    paths.append(f"M{f(cx + ra)} {f(xt)}V0")
    x = cx + ra + h + GAP

    # L
    sx = x + h
    paths.append(f"M{f(sx)} {f(top)}V{f(-h)}H{f(sx + 46)}")
    x = sx + 46 + GAP - 4  # optical kern: the L's open counter

    # a
    cx = x + h + ra
    p, _ = bowl(cx)
    paths.append(p)
    paths.append(f"M{f(cx + ra)} {f(xt)}V0")
    x = cx + ra + h + GAP

    # b
    sx = x + h
    cx = sx + ra
    p, _ = bowl(cx)
    paths.append(f"M{f(sx)} {f(top)}V0")
    paths.append(p)
    x = cx + ra + h + GAP - 2

    # period, in the accent colour
    period = (x, -W, W)
    width = x + W

    rects = "".join(f'<rect x="{f(a)}" y="{f(b)}" width="{f(s)}" height="{f(s)}"/>' for a, b, s in dots)
    g = (f'<g transform="translate({f(x0)} {f(baseline)}) scale({scale})">'
         f'<path d="{"".join(paths)}" fill="none" stroke="{color}" stroke-width="{f(W)}" stroke-linejoin="miter"/>'
         f'<g fill="{color}">{rects}</g>'
         f'<rect x="{f(period[0])}" y="{f(period[1])}" width="{f(W)}" height="{f(W)}" fill="{accent}"/>'
         f'</g>')
    return g, width * scale


# ---------------------------------------------------------------------------
# Hero artwork: an accretion disc orbiting inside a spacetime gravity well.
#
# Animated with CSS keyframes only (no scripts), which GitHub keeps when it
# serves an SVG as an image. The trick that keeps it light: every orbit ring
# is a flat circle of dots inside a fixed "tilt" transform (translate, roll,
# squash), and only an inner group rotates. A rotating circle seen through a
# fixed affine squash is exactly an orbit seen in perspective-free 3D, so a
# few dozen rotating groups move thousands of particles.
#
# Seamless loop: the disc is built with exact 3-fold symmetry, and each ring
# turns k x 120 degrees per LOOP (k = 1..6, inner rings faster). After LOOP
# seconds every ring lands on a copy of its start state, so the arms wind up
# and re-form without a jump. Every other motion divides LOOP evenly.
# ---------------------------------------------------------------------------

LOOP = 12          # seconds
ARMS = 3           # disc symmetry; also the number of spiral arms
RMAX = 212         # outer disc radius (px in the disc plane)
SQUASH = 0.42      # cos(view tilt): how flat the disc looks
ROLL = -7          # disc roll on screen (degrees)
WELL_R0 = 40       # softening radius of the well
WELL_DEPTH = 78    # depth scale of the well (px on screen)
RINGS = 34


def well(r):
    """Screen-space drop of the well surface at radius r (0 at the rim)."""
    def s(x):
        return WELL_DEPTH * WELL_R0 / math.sqrt(x * x + WELL_R0 * WELL_R0)
    return s(r) - s(RMAX)


def dots(points, width, color, opacity):
    """One stroked path of round dots; vector-effect keeps them round under the squash."""
    d = "".join(f"M{p}h.01" for p in points)
    return (f'<path d="{d}" stroke="{color}" stroke-opacity="{opacity}" stroke-width="{width}" '
            f'stroke-linecap="round" vector-effect="non-scaling-stroke" fill="none"/>')


def binned(parts, color=TEXT):
    """parts: (x, y, size, alpha) -> one path per (size, alpha) pair."""
    bins = {}
    for x, y, size, alpha in parts:
        bins.setdefault((size, alpha), []).append(f"{f(x)} {f(y)}")
    return "".join(dots(p, s, color, a) for (s, a), p in sorted(bins.items()))


def universe(rng, cx, cy):
    """Returns (defs, css, body, particle_count) for the artwork, rim centred on (cx, cy)."""
    css = [
        "@keyframes spin{to{transform:rotate(360deg)}}",
        "@keyframes rise{to{transform:translateY(-26px)}}",
        "@keyframes tw{to{opacity:.3}}",
        "@keyframes pulse{to{transform:scale(1.16);opacity:.75}}",
        ".s{animation:spin linear infinite}",
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}",
    ]
    defs = []
    body = []
    count = 0
    sector = 2 * math.pi / ARMS
    pitch = math.radians(31)

    # Depth: the far half of the disc (top of the screen) is dimmer.
    defs.append('<linearGradient id="depth" x1="0" y1="-80" x2="0" y2="120" gradientUnits="userSpaceOnUse">'
                '<stop offset="0" stop-color="#fff" stop-opacity=".38"/>'
                '<stop offset="1" stop-color="#fff"/></linearGradient>'
                '<mask id="depthmask" maskUnits="userSpaceOnUse" x="-300" y="-300" width="600" height="600">'
                '<rect x="-300" y="-300" width="600" height="600" fill="url(#depth)"/></mask>')

    body.append(f'<g transform="translate({cx} {cy}) rotate({ROLL})">')
    body.append('<g mask="url(#depthmask)">')

    # Spacetime grid: static iso-depth ellipses and meridians of the well.
    grid = []
    for r in (52, 92, 132, 172, RMAX):
        grid.append(f'<ellipse cx="0" cy="{f(well(r))}" rx="{r}" ry="{f(r * SQUASH)}"/>')
    for i in range(16):
        th = 2 * math.pi * i / 16
        pts = []
        for j in range(25):
            r = 30 + (RMAX - 30) * j / 24
            pts.append(f"{f(r * math.cos(th))} {f(r * math.sin(th) * SQUASH + well(r))}")
        grid.append(f'<path d="M{"L".join(pts)}"/>')
    body.append(f'<g fill="none" stroke="{MUTED}" stroke-opacity=".2" stroke-width=".8" '
                f'stroke-dasharray="1 4">{"".join(grid)}</g>')

    # Disc rings
    spacing = (RMAX - 14) / RINGS
    for i in range(RINGS):
        r = 14 + (RMAX - 14) * (i / (RINGS - 1)) ** 1.12
        k = max(1, min(6, round((r / RMAX) ** -0.8)))
        n = int(0.12 * r * 2 * math.pi / ARMS) + 4  # particles per sector
        arm = -math.log(r / 14) / math.tan(pitch)
        heat = (1 - r / RMAX) ** 0.7
        white, cyan = [], []
        for _ in range(n):
            on_arm = rng.random() < 0.8
            phi = arm + rng.gauss(0, 0.12 + 0.16 * r / RMAX) if on_arm else rng.uniform(0, sector)
            rr = r + rng.uniform(-0.5, 0.5) * spacing
            glow = (0.34 + 0.66 * heat) * rng.uniform(0.6, 1.0)
            alpha = glow if on_arm else glow * 0.45
            alpha = max(0.15, round(alpha * 6) / 6)
            if on_arm and rng.random() < 0.08:
                size = 2.2  # the occasional bright knot in an arm
            else:
                size = rng.choice((0.9, 1.1, 1.4)) if on_arm else rng.choice((0.8, 1.0))
            hot = on_arm and r > 50 and rng.random() < 0.008
            for m in range(ARMS):
                a = phi + m * sector
                p = (rr * math.cos(a), rr * math.sin(a), 2.0 if hot else round(size, 1), 1 if hot else alpha)
                (cyan if hot else white).append(p)
        count += len(white) + len(cyan)
        dur = f(LOOP * ARMS / k)  # seconds per full turn, i.e. k x 120 degrees per LOOP
        body.append(f'<g transform="translate(0 {f(well(r))}) scale(1 {SQUASH})">'
                    f'<g class="s" style="animation-duration:{dur}s">'
                    f'{binned(white)}{binned(cyan, ACCENT)}</g></g>')

    # Gravitational-wave ripples: cyan rings running outward along the well.
    stops = []
    for j in range(17):
        t = j / 16
        r = 16 + (RMAX + 14 - 16) * t ** 0.85
        op = 0 if j in (0, 16) else min(1, t / 0.08) * (1 - t) ** 1.5 * 0.9
        stops.append(f"{f(t * 100)}%{{transform:translate(0px,{f(well(min(r, RMAX)))}px) "
                     f"scale({f(r)},{f(r * SQUASH)});opacity:{op:.2f}}}")
    css.append("@keyframes wave{" + "".join(stops) + "}")
    css.append(f".wv{{animation:wave {LOOP // 2}s cubic-bezier(.3,.1,.5,1) infinite}}")
    ring = [f"{math.cos(a):.3f} {math.sin(a):.3f}" for a in (2 * math.pi * q / 120 for q in range(120))]
    for delay in (0, LOOP // 4):
        body.append(f'<g class="wv" style="animation-delay:-{delay}s">{dots(ring, 1.5, ACCENT, ".9")}</g>')
    body.append('</g>')  # depth mask

    # Polar jet: two strands of a helix rising out of the core. The helix is
    # periodic in its pitch, so moving it up by one pitch loops seamlessly.
    core_y = well(0)
    defs.append(f'<linearGradient id="jetfade" x1="0" y1="{f(core_y)}" x2="0" y2="-110" gradientUnits="userSpaceOnUse">'
                '<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                '<stop offset=".2" stop-color="#fff" stop-opacity=".6"/>'
                '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                '<mask id="jetmask" maskUnits="userSpaceOnUse" x="-60" y="-200" width="120" height="400">'
                '<rect x="-60" y="-200" width="120" height="400" fill="url(#jetfade)"/></mask>')
    jet = []
    pitch_px = 26
    for strand in (0, math.pi):
        th = 0.0
        while True:
            y = core_y + pitch_px - th / (2 * math.pi) * pitch_px
            if y < -110:
                break
            front = math.sin(th + strand) > 0
            jet.append((5.5 * math.cos(th + strand), y, 1.6 if front else 1.0, 0.85 if front else 0.35))
            th += 2 * math.pi / 9
    count += len(jet)
    body.append(f'<g mask="url(#jetmask)"><g style="animation:rise {LOOP // 3}s linear infinite">'
                f'{binned(jet)}</g></g>')

    # Core: a dense, slowly breathing knot with a faint glow.
    defs.append('<radialGradient id="glow"><stop offset="0" stop-color="#fff" stop-opacity=".22"/>'
                '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>')
    core = []
    for _ in range(70):
        a = rng.uniform(0, 2 * math.pi)
        rad = abs(rng.gauss(0, 4.2))
        core.append((rad * math.cos(a), rad * math.sin(a) * 0.7, rng.choice((1.2, 1.6, 2.0)),
                     rng.choice((0.5, 0.75, 1.0))))
    count += len(core)
    body.append(f'<g transform="translate(0 {f(core_y)})">'
                f'<g style="animation:pulse {LOOP // 4}s ease-in-out infinite alternate">'
                f'<circle r="22" fill="url(#glow)"/>{binned(core)}</g></g>')

    # Two probes on an inclined orbit with comet tails. The pair is two-fold
    # symmetric, so half a revolution per LOOP is seamless.
    body.append(f'<g transform="translate(0 {f(core_y - 40)}) rotate(14) scale(1 .22)">')
    body.append(f'<ellipse rx="196" ry="196" fill="none" stroke="{ACCENT}" stroke-opacity=".22" '
                f'stroke-width=".8" stroke-dasharray="1 5" vector-effect="non-scaling-stroke"/>')
    probe = []
    for side in (0, math.pi):
        for t in range(14):
            a = side - math.radians(t * 1.6)
            probe.append((196 * math.cos(a), 196 * math.sin(a), round(2.6 - t * 0.12, 1),
                          round(max(0.1, 1 - t / 13), 2)))
    count += len(probe)
    body.append(f'<g class="s" style="animation-duration:{LOOP * 2}s">{binned(probe, ACCENT)}</g></g>')
    body.append('</g>')  # frame
    return "".join(defs), "".join(css), "".join(body), count


def starfield(rng, x0, y0, x1, y1, n=240):
    """Faint background particles in three groups that twinkle out of phase."""
    groups = [[], [], []]
    for _ in range(n):
        groups[rng.randrange(3)].append((rng.uniform(x0, x1), rng.uniform(y0, y1),
                                         rng.choice((0.8, 1.0, 1.3)), rng.choice((0.15, 0.25, 0.4))))
    out = []
    for i, g in enumerate(groups):
        out.append(f'<g style="animation:tw {LOOP // 2}s ease-in-out infinite alternate;'
                   f'animation-delay:-{i * LOOP // 6}s">{binned(g)}</g>')
    return "".join(out), n


def cross(x, y, s=5, color=DIM):
    return (f'<path d="M{f(x - s)} {f(y)}H{f(x + s)}M{f(x)} {f(y - s)}V{f(y + s)}" '
            f'stroke="{color}" stroke-width="1"/>')


def text(x, y, s, size=12, color=MUTED, family=MONO, anchor="start", spacing=None, weight=None):
    attrs = [f'x="{f(x)}"', f'y="{f(y)}"', f'font-family="{family}"', f'font-size="{size}"', f'fill="{color}"']
    if anchor != "start":
        attrs.append(f'text-anchor="{anchor}"')
    if spacing is not None:
        attrs.append(f'letter-spacing="{spacing}"')
    if weight is not None:
        attrs.append(f'font-weight="{weight}"')
    return f'<text {" ".join(attrs)}>{s}</text>'


def svg(w, h, title, desc, body, slug):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="{slug}-title {slug}-desc">'
            f'<title id="{slug}-title">{title}</title><desc id="{slug}-desc">{desc}</desc>'
            f'<rect width="{w}" height="{h}" fill="{BG}"/>{body}</svg>\n')


# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

def hero():
    W_, H_ = 1200, 480
    L, R = 56, 1144
    rng = random.Random(SEED)
    b = []

    # Art first, so typography sits on top.
    fx0, fy0, fx1, fy1 = 690, 96, 1144, 398
    defs, css, art, n = universe(rng, 920, 226)
    stars, n_stars = starfield(rng, fx0, fy0, fx1, fy1)

    b.append(f'<style>{css}</style>')
    b.append(f'<defs>{defs}<clipPath id="fig"><rect x="{fx0}" y="{fy0}" width="{fx1 - fx0}" '
             f'height="{fy1 - fy0}"/></clipPath></defs>')
    b.append(f'<g clip-path="url(#fig)">{stars}{art}</g>')

    # Figure frame: registration marks and annotations
    for x, y in ((fx0, fy0), (fx1, fy0), (fx0, fy1), (fx1, fy1)):
        b.append(cross(x, y))
    b.append(text(fx0 + 12, fy0 + 4, "FIG. 01", 11, DIM, spacing=1.6))
    b.append(text(fx1 - 12, fy0 + 4, "ACCRETION FIELD", 11, DIM, anchor="end", spacing=1.6))
    b.append(text(fx0 + 12, fy1 + 4, "GRAVITY WELL · 3 ARMS", 11, DIM, spacing=1.6))
    b.append(text(fx1 - 12, fy1 + 4, f"N={n + n_stars:,} · T={LOOP}S", 11, DIM, anchor="end", spacing=1.6))

    # Top metadata row + rule
    b.append(text(L, 46, "DIMALAB / ENGINEERING", 13, MUTED, spacing=2.6))
    b.append(text(600, 46, "PROFILE — Nº 01", 13, DIM, anchor="middle", spacing=2.6))
    b.append(text(R, 46, "KZ / UTC+5", 13, MUTED, anchor="end", spacing=2.6))
    b.append(f'<path d="M{L} 66H{R}" stroke="{LINE}" stroke-width="1"/>')

    # Wordmark and descriptor
    b.append(text(L, 130, "INDEPENDENT DEVELOPER", 13, ACCENT, spacing=2.6))
    g, _ = wordmark(L, 282, 1.0)
    b.append(g)
    b.append(text(L - 1, 334, "Software developer.", 26, TEXT, SANS, weight=500))
    b.append(text(L - 1, 368, "Building tools, engines &amp; experiments.", 26, MUTED, SANS))

    # Bottom rule + three concepts on a thirds grid
    b.append(f'<path d="M{L} 420H{R}" stroke="{LINE}" stroke-width="1"/>')
    cols = [(L, "01", "ENGINE TOOLING"), (L + 363, "02", "WINDOWS UTILITIES"), (L + 726, "03", "MINECRAFT SYSTEMS")]
    for x, n, label in cols:
        b.append(text(x, 452, n, 13, ACCENT, spacing=2.6))
        b.append(text(x + 34, 452, label, 13, MUTED, spacing=2.6))

    title = "DimaLab. — Software developer"
    desc = ("Editorial banner: the DimaLab. wordmark, 'Software developer. Building tools, engines and "
            "experiments.', an animated particle universe: a three-armed accretion disc orbiting in a gravity well, with cyan ripples, a rising jet and two orbiting probes, and "
            "the themes engine tooling, Windows utilities and Minecraft systems.")
    return svg(W_, H_, title, desc, "".join(b), "hero")


# ---------------------------------------------------------------------------
# StoryModEngine plate: editors -> systems -> experience
# ---------------------------------------------------------------------------

def storymodengine():
    W_, H_ = 1200, 440
    L, R = 56, 1144
    b = []

    b.append(text(L, 46, "CURRENTLY BUILDING", 13, ACCENT, spacing=2.6))
    b.append(text(R, 46, "FORGE 1.20.1 · JAVA / KOTLIN · PRIVATE", 13, MUTED, anchor="end", spacing=2.6))
    b.append(f'<path d="M{L} 66H{R}" stroke="{LINE}" stroke-width="1"/>')
    b.append(text(L - 2, 126, "StoryModEngine", 44, TEXT, SANS, weight=600, spacing=-0.5))
    b.append(text(L, 156, "Author each system in its own editor, then assemble them into one experience.", 17, MUTED, SANS))

    top, step = 214, 30
    editors = ["VFX Editor", "Cutscene Sequencer", "Script IDE (.sme)", "Replay Editor", "Recipe Editor",
               "Video Asset Editor"]
    systems = ["Quests", "Dialogue", "NPCs", "Triggers", "Shops", "Cinematics"]

    c1, c2, c3 = L, 470, 860
    for x, label in ((c1, "A — AUTHOR"), (c2, "B — COMPOSE"), (c3, "C — PLAY")):
        b.append(text(x, 196, label, 11, DIM, spacing=2))

    hub1 = (c2 - 56, top + step * 2.5 - 4)
    hub2 = (c3 - 56, top + step * 2.5 - 4)

    for i, e in enumerate(editors):
        y = top + i * step + 14
        b.append(text(c1, y, f"E.{i + 1:02d}", 11, DIM, spacing=1))
        b.append(text(c1 + 48, y, e, 15, TEXT, SANS))
        x0 = c1 + 236
        b.append(f'<path d="M{x0} {f(y - 5)}C{x0 + 70} {f(y - 5)} {f(hub1[0] - 70)} {f(hub1[1])} {f(hub1[0])} {f(hub1[1])}" '
                 f'stroke="{LINE}" stroke-width="1" fill="none"/>')
        b.append(f'<circle cx="{x0}" cy="{f(y - 5)}" r="2" fill="{MUTED}"/>')

    for i, s in enumerate(systems):
        y = top + i * step + 14
        b.append(text(c2, y, f"S.{i + 1:02d}", 11, DIM, spacing=1))
        b.append(text(c2 + 48, y, s, 15, TEXT, SANS))
        x1 = c2 - 14
        b.append(f'<path d="M{f(hub1[0])} {f(hub1[1])}C{f(hub1[0] + 26)} {f(hub1[1])} {x1 - 26} {f(y - 5)} {x1} {f(y - 5)}" '
                 f'stroke="{LINE}" stroke-width="1" fill="none"/>')
        x0 = c2 + 190
        b.append(f'<path d="M{x0} {f(y - 5)}C{x0 + 60} {f(y - 5)} {f(hub2[0] - 60)} {f(hub2[1])} {f(hub2[0])} {f(hub2[1])}" '
                 f'stroke="{LINE}" stroke-width="1" fill="none"/>')
    b.append(f'<circle cx="{f(hub1[0])}" cy="{f(hub1[1])}" r="4" fill="{BG}" stroke="{MUTED}" stroke-width="1"/>')
    b.append(text(hub1[0], hub1[1] + 22, "FLOW", 10, DIM, anchor="middle", spacing=1.6))

    # Output node: the assembled experience
    b.append(f'<path d="M{f(hub2[0])} {f(hub2[1])}H{c3 - 12}" stroke="{ACCENT}" stroke-width="1"/>')
    b.append(f'<circle cx="{f(hub2[0])}" cy="{f(hub2[1])}" r="4" fill="{ACCENT}"/>')
    bx, by, bw, bh = c3, top - 2, R - c3, step * 6 - 8
    b.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="none" stroke="{LINE}" stroke-width="1"/>')
    for x, y in ((bx, by), (bx + bw, by), (bx, by + bh), (bx + bw, by + bh)):
        b.append(cross(x, y, 4, MUTED))
    b.append(text(bx + 22, by + 46, "One story-driven", 22, TEXT, SANS, weight=500))
    b.append(text(bx + 22, by + 76, "Minecraft experience", 22, TEXT, SANS, weight=500))
    b.append(text(bx + 22, by + 112, "scripted · in-game authored", 13, MUTED, MONO, spacing=0.6))
    b.append(text(bx + 22, by + bh - 20, "OUTPUT", 11, ACCENT, spacing=2))

    title = "StoryModEngine — editors to experience"
    desc = ("Diagram: in-game editors (VFX, cutscene sequencer, .sme script IDE, replay, recipe, video assets) "
            "feed runtime systems (quests, dialogue, NPCs, triggers, shops, cinematics) through the Flow engine, "
            "which assemble into one story-driven Minecraft experience.")
    return svg(W_, H_, title, desc, "".join(b), "sme")


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

def footer():
    W_, H_ = 1200, 120
    L, R = 56, 1144
    b = [f'<path d="M{L} 28H{R}" stroke="{LINE}" stroke-width="1"/>']
    g, _ = wordmark(L, 86, 0.3)
    b.append(g)
    b.append(text(600, 82, "TOOLS · ENGINES · EXPERIMENTS", 12, DIM, anchor="middle", spacing=2.6))
    b.append(text(R, 82, "END OF FILE", 12, MUTED, anchor="end", spacing=2.6))
    title = "DimaLab. — end of profile"
    desc = "Footer with the DimaLab. wordmark and the line tools, engines, experiments."
    return svg(W_, H_, title, desc, "".join(b), "footer")


if __name__ == "__main__":
    for name, fn in (("hero.svg", hero), ("storymodengine.svg", storymodengine), ("footer.svg", footer)):
        data = fn()
        (OUT / name).write_text(data, encoding="utf-8")
        print(f"{name}: {len(data.encode()) / 1024:.1f} KB")
