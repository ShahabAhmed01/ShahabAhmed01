#!/usr/bin/env python3
"""Generate profile stat SVG cards from the GitHub API (no third-party image hosts)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

USER = os.environ.get("GITHUB_USER", "ShahabAhmed01")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = Path(os.environ.get("OUTPUT_DIR", "assets/cards"))


def api(url: str) -> dict | list:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
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
            "Authorization": f"Bearer {TOKEN}",
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


def stats_svg(stats: dict) -> str:
    rows = [
        ("TOTAL STARS", str(stats["stars"])),
        ("PUBLIC REPOS", str(stats["repos"])),
        ("FOLLOWERS", str(stats["followers"])),
        ("CONTRIBUTIONS", str(stats["commits"])),
    ]
    y = 75
    lines = []
    for label, value in rows:
        lines.append(
            f'<text x="20" y="{y}" fill="#8b949e" font-size="12" font-weight="600" letter-spacing="1.5" font-family="-apple-system, sans-serif">{label}</text>'
        )
        lines.append(
            f'<text x="420" y="{y}" text-anchor="end" fill="#e6edf3" font-size="14" font-weight="700" font-family="Consolas, monospace">{value}</text>'
        )
        lines.append(
            f'<line x1="20" y1="{y + 12}" x2="420" y2="{y + 12}" stroke="#30363d" stroke-width="0.5" stroke-dasharray="2 4"/>'
        )
        y += 42

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="450" height="260" viewBox="0 0 450 260" role="img" aria-label="GitHub stats">
  <defs>
    <linearGradient id="fade" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#58a6ff" stop-opacity="1" />
      <stop offset="100%" stop-color="#58a6ff" stop-opacity="0" />
    </linearGradient>
  </defs>
  <text x="20" y="30" fill="#e6edf3" font-size="16" font-weight="800" letter-spacing="2" font-family="-apple-system, sans-serif">GITHUB STATS</text>
  <rect x="20" y="45" width="150" height="1" fill="url(#fade)"/>
  {''.join(lines)}
</svg>"""


def langs_svg(stats: dict) -> str:
    langs = stats["langs"] or [("No data", 1)]
    total = sum(c for _, c in langs) or 1
    colors = ["#58a6ff", "#388bfd", "#1f6feb", "#0969da", "#033d8b"]
    y = 75
    bars = []
    for i, (lang, count) in enumerate(langs):
        pct = count / total
        width = max(int(240 * pct), 8)
        color = colors[i % len(colors)]
        
        bars.append(
            f'<text x="20" y="{y}" fill="#8b949e" font-size="12" font-weight="600" letter-spacing="1" font-family="-apple-system, sans-serif">{lang.upper()}</text>'
        )
        bars.append(
            f'<text x="420" y="{y}" text-anchor="end" fill="#8b949e" font-size="12" font-family="Consolas, monospace">{int(pct * 100)}%</text>'
        )
        bars.append(
            f'<rect x="130" y="{y - 5}" width="240" height="4" rx="2" fill="#21262d"/>'
        )
        bars.append(
            f'<rect x="130" y="{y - 5}" width="{width}" height="4" rx="2" fill="{color}"/>'
        )
        bars.append(
            f'<circle cx="{130 + width}" cy="{y - 3}" r="3" fill="#ffffff" opacity="0.8"/>'
        )
        y += 37

    height = max(260, y + 20)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="450" height="{height}" viewBox="0 0 450 {height}" role="img" aria-label="Top languages">
  <defs>
    <linearGradient id="fade2" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#58a6ff" stop-opacity="1" />
      <stop offset="100%" stop-color="#58a6ff" stop-opacity="0" />
    </linearGradient>
  </defs>
  <text x="20" y="30" fill="#e6edf3" font-size="16" font-weight="800" letter-spacing="2" font-family="-apple-system, sans-serif">TOP LANGUAGES</text>
  <rect x="20" y="45" width="150" height="1" fill="url(#fade2)"/>
  {''.join(bars)}
</svg>"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stats = fetch_stats()
    (OUT / "github-stats.svg").write_text(stats_svg(stats), encoding="utf-8")
    (OUT / "top-langs.svg").write_text(langs_svg(stats), encoding="utf-8")
    print(f"Wrote cards to {OUT}")


if __name__ == "__main__":
    main()
