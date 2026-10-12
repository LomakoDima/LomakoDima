"""Renders the profile card: an ASCII portrait next to a neofetch-style panel.

The portrait comes from assets/src/avatar.json (made once by avatar_ascii.py).
The numbers in the panel (repositories, stars, followers, time on GitHub,
contributions and streaks) are fetched from the GitHub GraphQL API each time
this runs, so the daily workflow keeps them current. Writes assets/card.svg
and assets/card-mobile.svg (portrait above the panel, for narrow screens).

Standard library only. Needs GITHUB_TOKEN (or GH_TOKEN).

    python assets/src/card.py --login LomakoDima
    python assets/src/card.py --input response.json      # render a saved API response

On any API error or incomplete response the script exits non-zero and leaves
the existing card untouched.
"""

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contributions as cal  # noqa: E402  (fetching, validation and streaks are shared)

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent
QUERY = """
query($login: String!) {
  user(login: $login) {
    login createdAt
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100) {
      totalCount nodes { stargazerCount }
    }
    contributionsCollection { %s }
  }
}
""" % cal.CALENDAR

BG, LINE, TEXT, MUTED, DIM, ACCENT = cal.BG, cal.LINE, "#F4F5F7", cal.MUTED, cal.DIM, cal.ACCENT
TONES = {"0": "#4A4E55", "1": "#63676F", "2": "#80858D", "3": "#A2A6AD", "4": "#C7CACF", "5": "#F4F5F7", "c": ACCENT}
MONO = cal.MONO

# Fixed facts, taken from the README and the repositories themselves.
PROFILE = [
    ("OS", "Windows 11"),
    ("Host", "Kazakhstan · UTC+5"),
    ("Focus", "engines · Windows utilities · Minecraft systems"),
    ("Building", "StoryModEngine"),
    ("Languages", "Java · Kotlin · C# · Python · TypeScript"),
    ("Stack", "Forge · .NET / WPF · React · FastAPI"),
]


def uptime(since, today):
    """Years, months and days between two dates, like `uptime` for the account."""
    y, m, d = today.year - since.year, today.month - since.month, today.day - since.day
    if d < 0:
        m -= 1
        prev_month = (today.replace(day=1) - dt.timedelta(days=1))
        d += prev_month.day
    if m < 0:
        y -= 1
        m += 12
    return f"{cal.plural(y, 'year')}, {cal.plural(m, 'month')}, {cal.plural(d, 'day')}"


def parse(payload):
    try:
        user = payload["data"]["user"]
        created = dt.datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00")).date()
        followers = user["followers"]["totalCount"]
        repos = user["repositories"]
        stars = sum(n["stargazerCount"] for n in repos["nodes"])
        repo_count = repos["totalCount"]
    except (KeyError, TypeError, ValueError, AttributeError):
        raise cal.CalendarError("response is missing user statistics")
    if not all(isinstance(v, int) and v >= 0 for v in (followers, stars, repo_count)):
        raise cal.CalendarError("invalid user statistics")
    days, total = cal.parse(payload)
    return {"login": user["login"], "created": created, "followers": followers, "stars": stars,
            "repos": repo_count, "days": days, "total": total}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap(value, width):
    """Splits a value into lines of at most `width` characters, at spaces."""
    lines, cur = [], ""
    for word in value.split(" "):
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    return lines + [cur]


def render(info, today, mobile=False):
    """Desktop: portrait left, panel right. Mobile: portrait on top, larger panel below."""
    art = json.loads((HERE / "avatar.json").read_text(encoding="utf-8"))
    rows = art["rows"]
    W, PAD, ts = (600, 24, 15) if mobile else (1200, 40, 13)
    fs = min(11.0, (W - 2 * PAD) / (art["cols"] * 0.6)) if mobile else 9.2  # portrait font size
    cw, lh = fs * 0.6, fs * 1.09  # cell advance and line height (portrait CELL_ASPECT 0.55)
    pw, ph = art["cols"] * cw, len(rows) * lh
    top = 62 if mobile else 56
    px = (W - pw) / 2 if mobile else PAD
    pfs, line = (17, 30) if mobile else (15, 25)

    # neofetch panel content
    st = cal.streaks(info["days"], today)
    busy = st["busiest"]
    live = [
        ("Uptime", uptime(info["created"], today)),
        ("Repos", f"{info['repos']} public"),
        ("Stars", str(info["stars"])),
        ("Followers", str(info["followers"])),
        ("Contributions", f"{info['total']:,} in the last year"),
        ("Streak", f"{cal.plural(st['current'], 'day')} · longest {cal.plural(st['longest'], 'day')}"),
        ("Busiest day", f"{cal.short(busy['date'])}, {busy['date'].year} · {busy['count']}" if busy else "—"),
    ]
    items = PROFILE[:2] + [live[0]] + PROFILE[2:] + [None] + live[1:]
    keyw = max(len(item[0]) for item in items if item) + 1  # dot leaders end in one column
    ix = PAD if mobile else px + pw + 56
    value_chars = int((W - PAD - ix) / (pfs * 0.6)) - keyw - 2
    panel = []  # (key or "", value line) per visual line, None for a gap
    for item in items:
        if item is None:
            panel.append(None)
            continue
        key, value = item
        for n, part in enumerate(wrap(value, value_chars)):
            panel.append((key if n == 0 else "", part))
    py = top + ph + 56 if mobile else top + 30
    panel_h = 50 + sum(14 if x is None else line for x in panel) + 40
    H = round(max(top + ph + PAD, py + panel_h + (10 if mobile else 0)))

    out = ["<style>"
           "@keyframes rv{from{opacity:0}}.rv{animation:rv .35s ease-out backwards}"
           "@keyframes scan{to{transform:translateY(" + str(round(ph)) + "px)}}"
           ".scan{animation:scan 7s linear infinite}"
           "@keyframes blink{50%{opacity:0}}.cur{animation:blink 1.1s steps(1) infinite}"
           "@media (prefers-reduced-motion:reduce){.rv,.scan,.cur{animation:none}}"
           "text{white-space:pre}</style>"]
    out.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    out.append(cal.text(PAD, 34 + (4 if mobile else 0), "WHOAMI", ts, ACCENT, spacing=2.6))
    out.append(cal.text(W - PAD, 34 + (4 if mobile else 0), "~$ neofetch" if mobile else "dimalab@github: ~$ neofetch",
                        ts, MUTED, "end", 1.2))
    out.append(f'<path d="M{PAD} {48 + (6 if mobile else 0)}H{W - PAD}" stroke="{LINE}" stroke-width="1"/>')

    # Portrait: one <text> per row, forced onto an exact grid with textLength so it
    # lines up the same in whichever monospace font the viewer has.
    for r, row in enumerate(rows):
        t, tone = row["text"], row["tone"]
        if not t.strip():
            continue
        runs, cur, buf = [], None, ""
        for ch, tn in zip(t, tone):
            tn = tn if ch != " " else (cur or "0")
            if tn != cur and buf:
                runs.append((cur, buf))
                buf = ""
            cur = tn
            buf += ch
        runs.append((cur, buf))
        spans = "".join(f'<tspan fill="{TONES.get(k, TONES["3"])}">{esc(v)}</tspan>' for k, v in runs)
        out.append(f'<text class="rv" style="animation-delay:{r * 0.025:.3f}s" x="{px:.1f}" y="{top + (r + 1) * lh:.1f}" '
                   f'font-family="{MONO}" font-size="{fs:.2f}" textLength="{len(t) * cw:.1f}" '
                   f'lengthAdjust="spacingAndGlyphs" xml:space="preserve">{spans}</text>')
    # A faint scan line drifting down the portrait.
    out.append(f'<defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{ACCENT}" '
               f'stop-opacity="0"/><stop offset="1" stop-color="{ACCENT}" stop-opacity=".16"/></linearGradient>'
               f'<clipPath id="pc"><rect x="{px:.1f}" y="{top}" width="{pw:.0f}" height="{ph:.0f}"/></clipPath></defs>')
    out.append(f'<g clip-path="url(#pc)"><rect class="scan" x="{px:.1f}" y="{top - 26}" width="{pw:.0f}" height="26" '
               f'fill="url(#sg)"/></g>')

    # neofetch panel
    y = py
    out.append(f'<text x="{ix}" y="{y}" font-family="{MONO}" font-size="{pfs + 5}"><tspan fill="{ACCENT}">dimalab</tspan>'
               f'<tspan fill="{TEXT}">@github</tspan></text>')
    y += 16
    out.append(f'<path d="M{ix} {y}H{ix + 14 * (pfs - 3)}" stroke="{MUTED}" stroke-dasharray="6 4" stroke-width="1"/>')
    y += 34
    for k, entry in enumerate(panel):
        if entry is None:
            y += 14
            continue
        key, value = entry
        lead = f"{key} {'.' * (keyw - len(key))} " if key else " " * (keyw + 2)
        out.append(f'<text class="rv" style="animation-delay:{0.3 + k * 0.05:.2f}s" x="{ix}" y="{y}" '
                   f'font-family="{MONO}" font-size="{pfs}" xml:space="preserve"><tspan fill="{ACCENT}">{esc(key)}</tspan>'
                   f'<tspan fill="{DIM}">{esc(lead[len(key):])}</tspan><tspan fill="{TEXT}">{esc(value)}</tspan></text>')
        y += line
    # The neofetch colour bar: the profile's own palette, then a blinking cursor.
    y += 8
    palette = ["#151B23", "#033A16", "#196C2E", "#2EA043", "#56D364", MUTED, TEXT, ACCENT]
    sw = 30 if not mobile else 36
    for j, c in enumerate(palette):
        out.append(f'<rect x="{ix + j * sw}" y="{y}" width="{sw - 4}" height="{14 if not mobile else 16}" fill="{c}"/>')
    out.append(f'<rect class="cur" x="{ix + len(palette) * sw + 8}" y="{y}" width="9" height="16" fill="{TEXT}"/>')

    title = f"{info['login']} — profile card"
    desc = (f"ASCII portrait of DimaLab next to a neofetch-style panel: "
            + "; ".join(f"{k}: {v}" for k, v in PROFILE[:2] + live + PROFILE[2:]) + ".")
    slug = "cardm" if mobile else "card"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'role="img" aria-labelledby="{slug}-t {slug}-d"><title id="{slug}-t">{esc(title)}</title>'
            f'<desc id="{slug}-d">{esc(desc)}</desc>{"".join(out)}</svg>\n')


def main():
    today_utc = dt.datetime.now(dt.timezone.utc).date()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--login", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "LomakoDima"))
    ap.add_argument("--input", help="render from a saved GraphQL JSON response")
    ap.add_argument("--today", type=dt.date.fromisoformat, default=today_utc)
    ap.add_argument("--out", default=str(ASSETS), help="output directory (default: assets/)")
    args = ap.parse_args()
    try:
        if args.input:
            try:
                payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as e:
                raise cal.CalendarError(f"cannot read {args.input}: {e}") from e
        else:
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
            if not token:
                raise cal.CalendarError("set GITHUB_TOKEN (or GH_TOKEN) to query the GitHub API")
            payload = cal.fetch(args.login, token, query=QUERY)
        if isinstance(payload, dict) and payload.get("errors"):
            raise cal.CalendarError(f"GraphQL errors: {payload['errors']}")
        info = parse(payload)
        desktop = render(info, args.today)
        mobile = render(info, args.today, mobile=True)
    except cal.CalendarError as e:
        print(f"error: {e}. Existing card left unchanged.", file=sys.stderr)
        return 1
    cal.write_atomic(Path(args.out) / "card.svg", desktop)
    cal.write_atomic(Path(args.out) / "card-mobile.svg", mobile)
    print(f"card: {info['repos']} repos, {info['stars']} stars, {info['followers']} followers, "
          f"{info['total']} contributions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
