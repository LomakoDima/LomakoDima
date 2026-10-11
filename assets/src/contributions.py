"""Renders a GitHub-style contribution calendar from real data.

By default it mirrors the calendar on the GitHub profile page: the last year of
daily contribution counts, as returned by the GitHub GraphQL API. With --year it
renders one calendar year (January 1 to December 31, UTC) instead; days that
have not happened yet are then drawn as empty outlines, so they cannot be
mistaken for days without contributions. Two SVGs are written:

    assets/activity.svg         the whole range in one row of weeks (desktop)
    assets/activity-mobile.svg  the same range as two stacked halves (narrow screens)

Private contributions are included only if "Private contributions" is enabled in
the profile's contribution settings, which is also what GitHub shows visitors.

Standard library only. Needs a token in GITHUB_TOKEN (or GH_TOKEN); in GitHub
Actions the built-in token is enough because the data is public.

    python assets/src/contributions.py --login LomakoDima
    python assets/src/contributions.py --year 2026                     # one calendar year
    python assets/src/contributions.py --input calendar.json           # render saved API output

If the request fails or the response does not look like a complete calendar
for the year, the script exits non-zero and leaves the existing SVGs untouched.
"""

import argparse
import calendar
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
CALENDAR = ("contributionCalendar { totalContributions "
            "weeks { contributionDays { date weekday contributionCount contributionLevel } } }")
QUERY_LAST_YEAR = "query($login: String!) { user(login: $login) { contributionsCollection { %s } } }" % CALENDAR
QUERY_YEAR = ("query($login: String!, $from: DateTime!, $to: DateTime!) "
              "{ user(login: $login) { contributionsCollection(from: $from, to: $to) { %s } } }" % CALENDAR)

# Same design tokens as build.py, plus GitHub's dark-theme contribution greens.
BG = "#0A0A0B"
LINE = "#25272C"
MUTED = "#8B9099"
DIM = "#5A5E66"
ACCENT = "#3FD0FF"
FUTURE = "#1E232B"
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


def fetch(login, token, year=None, attempts=3):
    if year:
        query = QUERY_YEAR
        variables = {"login": login, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"}
    else:
        query, variables = QUERY_LAST_YEAR, {"login": login}
    body = json.dumps({"query": query, "variables": variables}).encode()
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


def parse(payload, year=None):
    """Validates the API response (the last year, or one calendar year) and returns (days, total)."""
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
        raise CalendarError(f"expected a year of weeks, got {len(weeks)}")

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

    if year:
        expected = 366 if calendar.isleap(year) else 365
        if len(days) != expected or days[0]["date"] != dt.date(year, 1, 1) or days[-1]["date"] != dt.date(year, 12, 31):
            first, last = (days[0]["date"], days[-1]["date"]) if days else (None, None)
            raise CalendarError(f"expected {year}-01-01..{year}-12-31 ({expected} days), got {first}..{last} ({len(days)})")
    elif not 360 <= len(days) <= 371:
        raise CalendarError(f"expected about a year of days, got {len(days)}")
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
        m = next(d for d in col if d)["date"].month
        if m != prev:
            labels.append((i, MONTHS[m - 1]))
            prev = m
    if len(labels) > 1 and labels[1][0] - labels[0][0] < min_gap:
        labels.pop(0)  # a leading label that would collide with the next one
    return labels


def plural(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def short(d):
    return f"{d:%b} {d.day}"


def text(x, y, s, size, fill, anchor=None, spacing=None):
    a = f' text-anchor="{anchor}"' if anchor else ""
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" font-family="{MONO}" font-size="{size}" fill="{fill}"{a}{ls}>{s}</text>'


def grid(out, days, today, gx, month_y, gy, step, gap, ts, label_x, col0=0):
    """Draws month labels, weekday labels and one block of week columns. Returns the column count."""
    cols = columns(days)
    cell = step - gap
    for i, name in month_labels(cols):
        out.append(text(gx + i * step, month_y, name, ts, MUTED))
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(text(label_x, gy + row * step + cell * 0.8, name, ts, DIM))
    for i, col in enumerate(cols):
        x = gx + i * step
        rects = []
        for row, d in enumerate(col):
            if d is None:
                continue  # outside the year
            y = gy + row * step
            if d["date"] > today and d["count"] == 0:
                # Not happened yet: an outline, never a "zero contributions" cell.
                rects.append(f'<rect x="{x + .5:.1f}" y="{y + .5:.1f}" width="{cell - 1:.1f}" height="{cell - 1:.1f}" '
                             f'rx="2" fill="none" stroke="{FUTURE}"/>')
            else:
                rects.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="2" '
                             f'fill="{LEVELS[d["level"]]}"/>')
        out.append(f'<g class="w" style="animation-delay:{(col0 + i) * 0.012:.3f}s">{"".join(rects)}</g>')
    return len(cols)


def legend(out, right, y, cell, gap, ts):
    """Less [] [] [] [] [] More, right-aligned on one line like GitHub's."""
    lc = cell * 0.85
    lx = right - ts * 0.6 * 4 - 6 - 5 * (lc + gap) + gap
    out.append(text(lx - 6, y, "Less", ts, DIM, "end"))
    for j, color in enumerate(LEVELS.values()):
        out.append(f'<rect x="{lx + j * (lc + gap):.1f}" y="{y - lc + 1:.1f}" width="{lc:.1f}" height="{lc:.1f}" '
                   f'rx="2" fill="{color}"/>')
    out.append(text(right, y, "More", ts, DIM, "end"))


def render(days, total, login, year, today, mobile=False):
    """year=None renders the last-year range exactly as the API returned it."""
    width, side, ts, gap, label_w = (600, 24, 15, 4, 46) if mobile else (900, 40, 11, 3.5, 34)
    L, R = side, width - side
    gx = L + label_w
    if year:
        halves = ([d for d in days if d["date"].month <= 6], [d for d in days if d["date"].month > 6])
    else:
        # Split at a week boundary so both halves keep whole Sunday-first columns.
        cols = columns(days)
        cut = next(d for d in cols[(len(cols) + 1) // 2] if d)["date"]
        halves = ([d for d in days if d["date"] < cut], [d for d in days if d["date"] >= cut])
    blocks = halves if mobile else (days,)
    ncols = max(len(columns(b)) for b in blocks)
    step = (R - gx + gap) / ncols
    cell = step - gap
    grid_h = 7 * step - gap

    out = [f'<style>@keyframes in{{from{{opacity:0}}}}.w{{animation:in .5s ease-out backwards}}'
           f'@media (prefers-reduced-motion:reduce){{.w{{animation:none}}}}</style>']
    head = 52 if mobile else 46
    rule = head + 20
    out.append(text(L, head, "ACTIVITY", ts + 2, ACCENT, spacing=2.6))
    period = f"IN {year}" if year else "IN THE LAST YEAR"
    out.append(text(R, head, f"{plural(total, 'CONTRIBUTION').upper()} {period}", ts + 2, MUTED, "end", 2.6))
    out.append(f'<path d="M{L} {rule}H{R}" stroke="{LINE}" stroke-width="1"/>')

    y = rule + (34 if mobile else 30)
    col0 = 0
    for block in blocks:
        col0 += grid(out, block, today, gx, y, y + 10, step, gap, ts, L, col0)
        y += 10 + grid_h + (40 if mobile else 0)
    foot = y + (2 if mobile else 34)

    start, end = days[0]["date"], days[-1]["date"]
    through = f"through {short(min(today, end))}"
    if mobile:
        note = f"{through} · GitHub API"
    elif year:
        note = f"Jan 1 – Dec 31, {year} · {through} · via GitHub GraphQL API"
    else:
        note = f"{short(start)}, {start.year} – {short(end)}, {end.year} · via GitHub GraphQL API"
    out.append(text(L, foot, note, ts, DIM))
    legend(out, R, foot, cell if not mobile else cell * 0.8, gap, ts)
    height = round(foot + 26)

    # Accessible summary: totals per month that has started.
    per_month = {}
    for d in days:
        if d["date"] <= today or d["count"]:
            key = MONTHS[d["date"].month - 1] + ("" if year else f" {d['date'].year}")
            per_month[key] = per_month.get(key, 0) + d["count"]
    breakdown = "; ".join(f"{k}: {v}" for k, v in per_month.items())
    if year:
        title = f"{login} GitHub contributions in {year}, {through}: {plural(total, 'contribution')}"
        desc = (f"Contribution calendar for {year}, one cell per day, darker to brighter green by activity; "
                f"days still ahead are drawn as outlines. By month: {breakdown}.")
    else:
        title = (f"{login} GitHub contributions in the last year, {start.isoformat()} to {end.isoformat()}: "
                 f"{plural(total, 'contribution')}")
        desc = f"Contribution calendar, one cell per day, darker to brighter green by activity. By month: {breakdown}."
    slug = "actm" if mobile else "act"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="{slug}-t {slug}-d">'
            f'<title id="{slug}-t">{title}</title><desc id="{slug}-d">{desc}</desc>'
            f'<rect width="{width}" height="{height}" fill="{BG}"/>{"".join(out)}</svg>\n')


def write_atomic(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)


def main():
    today_utc = dt.datetime.now(dt.timezone.utc).date()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--login", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "LomakoDima"))
    ap.add_argument("--year", type=int, help="render one calendar year instead of the last year (GitHub's default view)")
    ap.add_argument("--today", type=dt.date.fromisoformat, default=today_utc,
                    help="treat this date as today (default: current UTC date); later days render as outlines")
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
            payload = fetch(args.login, token, args.year)
        days, total = parse(payload, args.year)
        desktop = render(days, total, args.login, args.year, args.today)
        mobile = render(days, total, args.login, args.year, args.today, mobile=True)
    except CalendarError as e:
        print(f"error: {e}. Existing calendar left unchanged.", file=sys.stderr)
        return 1

    out = Path(args.out)
    write_atomic(out / "activity.svg", desktop)
    write_atomic(out / "activity-mobile.svg", mobile)
    print(f"{args.year or 'last year'} ({days[0]['date']} .. {days[-1]['date']}): {total} contributions, "
          f"{sum(1 for d in days if d['count'])} active days")
    return 0


if __name__ == "__main__":
    sys.exit(main())
