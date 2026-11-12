"""Render assets/stats.svg from live GitHub data. Standard library only.

Env: GITHUB_TOKEN (required), GH_USER (default CyberTron957).
Run daily by .github/workflows/stats.yml.
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "CyberTron957")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT = Path(__file__).resolve().parent.parent / "assets" / "stats.svg"
SKIP_LANGS = {"HTML", "CSS", "SCSS", "Less", "Dockerfile", "Makefile", "Procfile", "Batchfile"}

QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection { contributionCalendar { totalContributions } }
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def gql(variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if body.get("errors"):
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]


def fetch():
    stars, langs, after, first = 0, {}, None, None
    while True:
        u = gql({"login": USER, "after": after})
        first = first or u
        repos = u["repositories"]
        for n in repos["nodes"]:
            stars += n["stargazerCount"]
            for e in n["languages"]["edges"]:
                name = e["node"]["name"]
                if name in SKIP_LANGS:
                    continue
                size, color = langs.get(name, (0, None))
                langs[name] = (size + e["size"], e["node"]["color"] or "#8b949e")
        if not repos["pageInfo"]["hasNextPage"]:
            break
        after = repos["pageInfo"]["endCursor"]
    return {
        "stars": stars,
        "repos": first["repositories"]["totalCount"],
        "followers": first["followers"]["totalCount"],
        "contribs": first["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "langs": langs,
    }


def render(s):
    total = sum(v[0] for v in s["langs"].values()) or 1
    ranked = sorted(s["langs"].items(), key=lambda kv: -kv[1][0])
    top = [(n, c, sz / total) for n, (sz, c) in ranked[:5]]
    rest = 1 - sum(p for _, _, p in top)
    if rest > 0.001:
        top.append(("Other", "#3d4757", rest))

    metrics = [
        (f"{s['stars']:,}", "stars earned"),
        (f"{s['contribs']:,}", "contributions (1y)"),
        (f"{s['repos']:,}", "public repos"),
        (f"{s['followers']:,}", "followers"),
    ]
    m_svg = []
    for i, (val, label) in enumerate(metrics):
        x = 48 + i * 172
        m_svg.append(
            '<g>'
            f'<text x="{x}" y="132" class="sans" font-size="44" font-weight="700" fill="#f0f6fc">{val}</text>'
            f'<text x="{x}" y="162" class="mono" font-size="14" fill="#8b949e">{label}</text></g>'
        )

    bar_x, bar_w, bar_y = 776, 376, 78
    segs, x = [], bar_x
    for name, color, p in top:
        w = bar_w * p
        segs.append(f'<rect x="{x:.2f}" y="{bar_y}" width="{w:.2f}" height="10" fill="{color}"/>')
        x += w
    legend = []
    for i, (name, color, p) in enumerate(top):
        col, row = i % 2, i // 2
        lx, ly = bar_x + col * 210, 126 + row * 30
        legend.append(
            f'<circle cx="{lx + 5}" cy="{ly - 5}" r="5" fill="{color}"/>'
            f'<text x="{lx + 18}" y="{ly}" class="mono" font-size="14" fill="#c9d1d9">{escape(name)}'
            f' <tspan fill="#6e7681">{p * 100:.1f}%</tspan></text>'
        )

    today = dt.date.today().isoformat()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="230" viewBox="0 0 1200 230" role="img" aria-labelledby="t">
  <title id="t">GitHub stats for {USER}: {s["stars"]} stars, {s["contribs"]} contributions in the last year, {s["repos"]} public repos, {s["followers"]} followers</title>
  <defs>
    <pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.2" fill="#18202d"/></pattern>
    <clipPath id="card"><rect width="1200" height="230" rx="20"/></clipPath>
    <clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="10" rx="5"/></clipPath>
    <style>
      .mono{{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace}}
      .sans{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif}}
    </style>
  </defs>
  <g clip-path="url(#card)">
    <rect width="1200" height="230" fill="#0b0f17"/>
    <rect width="1200" height="230" fill="url(#dots)"/>
  </g>
  <rect x="0.5" y="0.5" width="1199" height="229" rx="20" fill="none" stroke="#1f2937"/>
  <text x="48" y="56" class="mono" font-size="15" fill="#34d399">~ $ <tspan fill="#e6edf3">gh stats {USER}</tspan></text>
  {"".join(m_svg)}
  <text x="48" y="202" class="mono" font-size="12" fill="#4b5563">refreshed daily · {today}</text>
  <line x1="736" y1="40" x2="736" y2="190" stroke="#1f2937"/>
  <text x="{bar_x}" y="56" class="mono" font-size="15" fill="#8b949e">top languages</text>
  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="10" rx="5" fill="#161b22"/>
  <g clip-path="url(#bar)">{"".join(segs)}</g>
  {"".join(legend)}
</svg>
'''


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("GITHUB_TOKEN is not set")
    OUT.write_text(render(fetch()))
    print(f"wrote {OUT}")
