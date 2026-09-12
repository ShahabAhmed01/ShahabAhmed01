#!/usr/bin/env python3
"""Generate self-contained, theme-safe stat SVGs from the GitHub API.

No third-party image hosts, no fixed dark-only palette. Each card draws its
own rounded background + border so it reads correctly on both light and dark
profiles. The single accent (amber) is shared with the hero wordmark.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

USER = os.environ.get("GITHUB_USER", "ShahabAhmed01")
OUT = Path(os.environ.get("OUTPUT_DIR", "assets/cards"))

# single accent used across the whole profile
ACCENT = "#E3B341"
BG = "#0d1117"
BORDER = "#21262d"
TITLE = "#e6edf3"
LABEL = "#8b949e"
VALUE = "#f0f6fc"
TRACK = "#161b22"
FONT_SANS = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
FONT_MONO = "ui-monospace, SFMono-Regular, Consolas, 'Liberation Mono', monospace"

W = 440
PAD = 26
RIGHT = W - PAD


def _token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")
    return token


def api(url: str) -> dict | list:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-stats-generator",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def graphql(query: str) -> dict:
    payload = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
            "User-Agent": "profile-stats-generator",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch_stats() -> dict:
    profile = api(f"https://api.github.com/users/{USER}")
    repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100&sort=updated")
    stars = sum(r.get("stargazers_count", 0) for r in repos)
    langs = Counter()
    for repo in repos:
        if repo.get("fork") or not repo.get("language"):
            continue
        langs[repo["language"]] += 1

    commits = 0
    try:
        g = graphql(
            f'{{ user(login: "{USER}") {{ contributionsCollection {{ totalCommitContributions }} }} }}'
        )
        commits = g["user"]["contributionsCollection"]["totalCommitContributions"]
    except (urllib.error.URLError, RuntimeError, KeyError, TypeError):
        commits = 0

    return {
        "repos": profile.get("public_repos", len(repos)),
        "stars": stars,
        "followers": profile.get("followers", 0),
        "commits": commits,
        "langs": langs.most_common(5),
    }


def _card_header(title: str) -> str:
    return (
        f'<rect x="{PAD}" y="22" width="4" height="16" rx="2" fill="{ACCENT}"/>'
        f'<text x="{PAD + 14}" y="37" fill="{TITLE}" font-size="13" font-weight="700" '
        f'letter-spacing="2" font-family="{FONT_SANS}">{title}</text>'
    )


def stats_svg(stats: dict) -> str:
    rows = [
        ("TOTAL STARS", str(stats["stars"])),
        ("PUBLIC REPOS", str(stats["repos"])),
        ("FOLLOWERS", str(stats["followers"])),
        ("CONTRIBUTIONS", str(stats["commits"])),
    ]
    lines = []
    y = 72
    last = y + (len(rows) - 1) * 44
    for label, value in rows:
        lines.append(
            f'<text x="{PAD}" y="{y}" fill="{LABEL}" font-size="11" font-weight="600" '
            f'letter-spacing="1.5" font-family="{FONT_SANS}">{label}</text>'
        )
        lines.append(
            f'<text x="{RIGHT}" y="{y}" text-anchor="end" fill="{VALUE}" font-size="18" '
            f'font-weight="700" font-family="{FONT_MONO}">{value}</text>'
        )
        if y < last:
            lines.append(
                f'<line x1="{PAD}" y1="{y + 14}" x2="{RIGHT}" y2="{y + 14}" '
                f'stroke="{BORDER}" stroke-width="1"/>'
            )
        y += 44

    height = last + 22
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" aria-label="GitHub stats">
  <rect x="0" y="0" width="{W}" height="{height}" rx="16" fill="{BG}" stroke="{BORDER}" stroke-width="1"/>
  {_card_header("GITHUB STATS")}
  {''.join(lines)}
</svg>"""


def langs_svg(stats: dict) -> str:
    langs = stats["langs"] or [("No data", 1)]
    total = sum(c for _, c in langs) or 1
    bar_x = 150
    bar_w = RIGHT - bar_x
    lines = []
    y = 72
    for lang, count in langs:
        pct = count / total
        width = max(int(bar_w * pct), 6)
        lines.append(
            f'<text x="{PAD}" y="{y}" fill="{LABEL}" font-size="11" font-weight="600" '
            f'letter-spacing="1.2" font-family="{FONT_SANS}">{lang.upper()}</text>'
        )
        lines.append(
            f'<text x="{RIGHT}" y="{y}" text-anchor="end" fill="{LABEL}" font-size="11" '
            f'font-family="{FONT_MONO}">{round(pct * 100)}%</text>'
        )
        lines.append(
            f'<rect x="{bar_x}" y="{y - 4}" width="{bar_w}" height="5" rx="2.5" fill="{TRACK}"/>'
        )
        lines.append(
            f'<rect x="{bar_x}" y="{y - 4}" width="{width}" height="5" rx="2.5" fill="{ACCENT}"/>'
        )
        y += 38

    height = y - 18
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" aria-label="Top languages">
  <rect x="0" y="0" width="{W}" height="{height}" rx="16" fill="{BG}" stroke="{BORDER}" stroke-width="1"/>
  {_card_header("TOP LANGUAGES")}
  {''.join(lines)}
</svg>"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stats = fetch_stats()
    (OUT / "github-stats.svg").write_text(stats_svg(stats), encoding="utf-8")
    (OUT / "top-langs.svg").write_text(langs_svg(stats), encoding="utf-8")
    print(f"Wrote cards to {OUT}")


if __name__ == "__main__":
    main()