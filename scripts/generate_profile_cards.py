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
        ("Total Stars", str(stats["stars"])),
        ("Public Repos", str(stats["repos"])),
        ("Followers", str(stats["followers"])),
        ("Contributions", str(stats["commits"])),
    ]
    y = 58
    lines = []
    for label, value in rows:
        lines.append(
            f'<text x="28" y="{y}" fill="#8b949e" font-size="14" font-family="Segoe UI, Arial, sans-serif">{label}</text>'
        )
        lines.append(
            f'<text x="460" y="{y}" text-anchor="end" fill="#c9d1d9" font-size="14" font-family="Consolas, monospace">{value}</text>'
        )
        y += 32

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-label="GitHub stats">
  <rect width="495" height="195" rx="10" fill="#0d1117" stroke="#30363d"/>
  <text x="24" y="34" fill="#58a6ff" font-size="18" font-weight="700" font-family="Segoe UI, Arial, sans-serif">{USER}'s GitHub Stats</text>
  {''.join(lines)}
</svg>"""


def langs_svg(stats: dict) -> str:
    langs = stats["langs"] or [("No data", 1)]
    total = sum(c for _, c in langs) or 1
    colors = ["#0969da", "#58a6ff", "#79c0ff", "#a5d6ff", "#388bfd"]
    y = 58
    bars = []
    for i, (lang, count) in enumerate(langs):
        pct = count / total
        width = max(int(360 * pct), 24)
        color = colors[i % len(colors)]
        bars.append(
            f'<text x="28" y="{y}" fill="#c9d1d9" font-size="13" font-family="Consolas, monospace">{lang}</text>'
        )
        bars.append(
            f'<rect x="120" y="{y - 12}" width="{width}" height="14" rx="4" fill="{color}"/>'
        )
        bars.append(
            f'<text x="490" y="{y}" text-anchor="end" fill="#8b949e" font-size="12" font-family="Consolas, monospace">{int(pct * 100)}%</text>'
        )
        y += 28

    height = max(160, y + 20)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="{height}" viewBox="0 0 495 {height}" role="img" aria-label="Top languages">
  <rect width="495" height="{height}" rx="10" fill="#0d1117" stroke="#30363d"/>
  <text x="24" y="34" fill="#58a6ff" font-size="18" font-weight="700" font-family="Segoe UI, Arial, sans-serif">Most Used Languages</text>
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
