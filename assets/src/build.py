"""Generates the profile's SVG assets (StoryModEngine plate, footer) and the shared
wordmark geometry and design tokens. The animated hero is rendered by ascii_hero.py.

Standard library only. Run from the repository root:

    python assets/src/build.py
"""

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent
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
    for name, fn in (("storymodengine.svg", storymodengine), ("footer.svg", footer)):
        data = fn()
        (OUT / name).write_text(data, encoding="utf-8")
        print(f"{name}: {len(data.encode()) / 1024:.1f} KB")
