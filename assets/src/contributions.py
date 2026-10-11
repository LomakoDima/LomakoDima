"""Renders a GitHub-style contribution calendar from real data.

Fetches the last year of daily contribution counts from the GitHub GraphQL API
and writes two SVGs:

    assets/activity.svg         full year (desktop)
    assets/activity-mobile.svg  last 26 weeks, larger cells (narrow screens)

Standard library only. Needs a token in GITHUB_TOKEN (or GH_TOKEN); in GitHub
Actions the built-in token is enough because the data is public.

    python assets/src/contributions.py --login LomakoDima
    python assets/src/contributions.py --input calendar.json   # render saved API output

If the request fails or the response does not look like a complete calendar,
the script exits non-zero and leaves the existing SVGs untouched.
"""

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent
API = "https://api.github.com/graphql"
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date weekday contributionCount contributionLevel } }
      }
    }
  }
}
"""

# Same design tokens as build.py, plus GitHub's dark-theme contribution greens.
BG = "#0A0A0B"
LINE = "#25272C"
TEXT = "#F4F5F7"
MUTED = "#8B9099"
DIM = "#5A5E66"
ACCENT = "#3FD0FF"
LEVELS = {
    "NONE": "#151B23",
    "FIRST_QUARTILE": "#033A16",
    "SECOND_QUARTILE": "#196C2E",
    "THIRD_QUARTILE": "#2EA043",
    "FOURTH_QUARTILE": "#56D364",
}
MONO = "'JetBrains Mono','SFMono-Regular',ui-monospace,Menlo,Consolas,'Liberation Mono',monospace"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


class CalendarError(Exception):
    pass


def fetch(login, token, attempts=3):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": f"{login}-profile-calendar",
    })
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            # 4xx other than rate limiting will not get better by retrying.
            if e.code < 500 and e.code not in (403, 429) or attempt == attempts:
                raise CalendarError(f"GitHub API returned HTTP {e.code}: {e.read()[:300]!r}") from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if attempt == attempts:
                raise CalendarError(f"request failed: {e}") from e
        time.sleep(5 * attempt)


def parse(payload):
    """Validates the API response and returns (days, total). Raises CalendarError."""
    if not isinstance(payload, dict):
        raise CalendarError("response is not a JSON object")
    if payload.get("errors"):
        raise CalendarError(f"GraphQL errors: {payload['errors']}")
    try:
        cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        weeks = cal["weeks"]
        total = cal["totalContributions"]
    except (KeyError, TypeError):
        raise CalendarError("response is missing the contribution calendar (unknown user?)")
    if not isinstance(total, int) or total < 0:
        raise CalendarError(f"invalid total: {total!r}")
    if not 52 <= len(weeks) <= 54:
        raise CalendarError(f"expected about a year of weeks, got {len(weeks)}")

    days = []
    for week in weeks:
        for d in week.get("contributionDays") or []:
            try:
                date = dt.date.fromisoformat(d["date"])
                count, level, weekday = d["contributionCount"], d["contributionLevel"], d["weekday"]
            except (KeyError, TypeError, ValueError):
                raise CalendarError(f"malformed day: {d!r}")
            if not isinstance(count, int) or count < 0 or level not in LEVELS or weekday != (date.weekday() + 1) % 7:
                raise CalendarError(f"inconsistent day: {d!r}")
            days.append({"date": date, "count": count, "level": level})

    if len(days) < 360:
        raise CalendarError(f"only {len(days)} days in the calendar")
    for a, b in zip(days, days[1:]):
        if (b["date"] - a["date"]).days != 1:
            raise CalendarError(f"gap or disorder in dates between {a['date']} and {b['date']}")
    if sum(d["count"] for d in days) != total:
        raise CalendarError("daily counts do not add up to the reported total")
    return days, total


def columns(days):
    """Groups days into Sunday-first week columns, as GitHub lays them out."""
    cols = []
    for d in days:
        row = (d["date"].weekday() + 1) % 7  # Sunday = 0
        if not cols or row == 0:
            cols.append([None] * 7)
        cols[-1][row] = d
    return cols


def month_labels(cols, min_gap=3):
    """(column, label) wherever a new month starts on a week's first day, GitHub style."""
    labels = []
    prev = None
    for i, col in enumerate(cols):
        first = next(d for d in col if d)
        m = first["date"].month
        if m != prev:
            labels.append((i, MONTHS[m - 1]))
            prev = m
    # Drop a leading label that would collide with the next one.
    if len(labels) > 1 and labels[1][0] - labels[0][0] < min_gap:
        labels.pop(0)
    return labels


def plural(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def render(days, total, login, weeks=None, width=900, cell_gap=3.5, text_size=11, side=40, mobile=False):
    cols = columns(days)
    if weeks:
        cols = cols[-weeks:]
    shown = [d for c in cols for d in c if d]
    start, end = shown[0]["date"], shown[-1]["date"]

    L, R = side, width - side
    label_w = 34 if not mobile else 46
    gx = L + label_w
    step = (R - gx + cell_gap) / len(cols)
    cell = step - cell_gap
    head = 46 if not mobile else 52
    rule = head + 20
    month_y = rule + 30
    gy = month_y + 10
    grid_h = 7 * step - cell_gap
    foot = gy + grid_h + 34
    height = round(foot + 26)
    ts = text_size

    out = []
    out.append(f'<style>@keyframes in{{from{{opacity:0}}}}.w{{animation:in .5s ease-out backwards}}'
               f'@media (prefers-reduced-motion:reduce){{.w{{animation:none}}}}</style>')
    out.append(f'<rect width="{width}" height="{height}" fill="{BG}"/>')

    # Header row, rule
    out.append(f'<text x="{L}" y="{head}" font-family="{MONO}" font-size="{ts + 2}" fill="{ACCENT}" '
               f'letter-spacing="2.6">ACTIVITY</text>')
    right = "LAST 26 WEEKS" if mobile else f"{plural(total, 'CONTRIBUTION').upper()} IN THE LAST YEAR"
    out.append(f'<text x="{R}" y="{head}" font-family="{MONO}" font-size="{ts + 2}" fill="{MUTED}" '
               f'text-anchor="end" letter-spacing="2.6">{right}</text>')
    out.append(f'<path d="M{L} {rule}H{R}" stroke="{LINE}" stroke-width="1"/>')

    # Month and weekday labels
    for i, name in month_labels(cols):
        out.append(f'<text x="{gx + i * step:.1f}" y="{month_y}" font-family="{MONO}" font-size="{ts}" '
                   f'fill="{MUTED}">{name}</text>')
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="{L}" y="{gy + row * step + cell * 0.8:.1f}" font-family="{MONO}" '
                   f'font-size="{ts}" fill="{DIM}">{name}</text>')

    # Cells: one group per week column, revealed left to right on load.
    for i, col in enumerate(cols):
        x = gx + i * step
        rects = []
        for row, d in enumerate(col):
            if d is None:
                continue  # before the range start or in the future, as on GitHub
            rects.append(f'<rect x="{x:.1f}" y="{gy + row * step:.1f}" width="{cell:.1f}" height="{cell:.1f}" '
                         f'rx="2" fill="{LEVELS[d["level"]]}"/>')
        out.append(f'<g class="w" style="animation-delay:{i * 0.012:.3f}s">{"".join(rects)}</g>')

    # Footer: source on the left, Less -> More legend on the right
    if mobile:
        note = f"{plural(sum(d['count'] for d in shown), 'contribution')} in 26 weeks"
    else:
        note = f"{start:%b} {start.day}, {start.year} – {end:%b} {end.day}, {end.year} · via GitHub GraphQL API"
    out.append(f'<text x="{L}" y="{foot}" font-family="{MONO}" font-size="{ts}" fill="{DIM}">{note}</text>')
    # Legend, on one line like GitHub's: Less [] [] [] [] [] More
    lc = cell * (0.85 if not mobile else 0.7)
    more_x = R - ts * 0.6 * 4
    lx = more_x - 6 - 5 * (lc + cell_gap) + cell_gap
    out.append(f'<text x="{lx - 6:.1f}" y="{foot}" font-family="{MONO}" font-size="{ts}" fill="{DIM}" '
               f'text-anchor="end">Less</text>')
    for j, color in enumerate(LEVELS.values()):
        out.append(f'<rect x="{lx + j * (lc + cell_gap):.1f}" y="{foot - lc + 1:.1f}" width="{lc:.1f}" '
                   f'height="{lc:.1f}" rx="2" fill="{color}"/>')
    out.append(f'<text x="{R}" y="{foot}" font-family="{MONO}" font-size="{ts}" fill="{DIM}" '
               f'text-anchor="end">More</text>')

    # Accessible summary: totals per month, in date order.
    per_month = {}
    for d in shown:
        key = f"{d['date']:%b} {d['date'].year}"
        per_month[key] = per_month.get(key, 0) + d["count"]
    breakdown = "; ".join(f"{k}: {v}" for k, v in per_month.items())
    title = (f"{login} GitHub contributions, {start.isoformat()} to {end.isoformat()}: "
             f"{plural(sum(d['count'] for d in shown), 'contribution')}")
    desc = f"Contribution calendar, one cell per day, darker to brighter green by activity. By month: {breakdown}."
    slug = "actm" if mobile else "act"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="{slug}-t {slug}-d">'
            f'<title id="{slug}-t">{title}</title><desc id="{slug}-d">{desc}</desc>{"".join(out)}</svg>\n')


def write_atomic(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--login", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "LomakoDima"))
    ap.add_argument("--input", help="render from a saved GraphQL JSON response instead of calling the API")
    ap.add_argument("--out", default=str(ASSETS), help="output directory (default: assets/)")
    args = ap.parse_args()

    try:
        if args.input:
            try:
                payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as e:
                raise CalendarError(f"cannot read {args.input}: {e}") from e
        else:
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
            if not token:
                raise CalendarError("set GITHUB_TOKEN (or GH_TOKEN) to query the GitHub API")
            payload = fetch(args.login, token)
        days, total = parse(payload)
        desktop = render(days, total, args.login)
        mobile = render(days, total, args.login, weeks=26, width=600, cell_gap=4, text_size=15, side=24, mobile=True)
    except CalendarError as e:
        print(f"error: {e}. Existing calendar left unchanged.", file=sys.stderr)
        return 1

    out = Path(args.out)
    write_atomic(out / "activity.svg", desktop)
    write_atomic(out / "activity-mobile.svg", mobile)
    print(f"{days[0]['date']} .. {days[-1]['date']}: {total} contributions, "
          f"{sum(1 for d in days if d['count'])} active days")
    return 0


if __name__ == "__main__":
    sys.exit(main())
