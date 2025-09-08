#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
import requests

USERNAME = "Ligh7bringer"

try:
    from TOKEN import bearer_token
except Exception as e:
    import os, sys
    print(f"Failed to import TOKEN.bearer_token: {e}. Trying env var...")
    bearer_token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_GRAPHQL_PAT") or ""
    if not bearer_token:
      sys.exit("Missing GITHUB_TOKEN (or GH_GRAPHQL_PAT)")

def _normalize_token(tok):
    if not tok:
        raise RuntimeError("Missing GitHub token")
    return tok if tok.lower().startswith("bearer ") else f"Bearer {tok}"

HEADERS = {
    "Authorization": _normalize_token(bearer_token),
    "User-Agent": f"hugo-github-stats/1.0 (+https://github.com/{USERNAME})",
    "Content-Type": "application/json",
}

DATA_DIR = Path.cwd() / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

QUERY_REPOS_PAGE = """
query($login:String!, $after:String) {
  user(login:$login) {
    repositories(
      first: 100
      after: $after
      ownerAffiliations: OWNER
      isFork: false
      privacy: PUBLIC
      orderBy: { field: STARGAZERS, direction: DESC }
    ) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name
        nameWithOwner
        description
        url
        stargazerCount
        forkCount
        updatedAt
        primaryLanguage { name color }
        languages(first: 20, orderBy: { field: SIZE, direction: DESC }) {
          edges { size node { name color } }
        }
        repositoryTopics(first: 10) { nodes { topic { name } } }
      }
    }
  }
}
"""

QUERY_CONTRIBS_CAL = """
query($login:String!) {
  user(login:$login) {
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks {
          firstDay
          contributionDays {
            date
            contributionCount
            weekday
            color
          }
        }
      }
    }
  }
}
"""

def run_query(query, variables=None):
    r = requests.post(
        "https://api.github.com/graphql",
        headers=HEADERS,
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
    payload = r.json()
    if "errors" in payload:
        raise RuntimeError(f"GraphQL errors: {json.dumps(payload['errors'], indent=2)[:800]}")
    return payload["data"]

def paginate_repos(login):
    nodes = []
    after = None
    while True:
        data = run_query(QUERY_REPOS_PAGE, {"login": login, "after": after})
        conn = data["user"]["repositories"]
        nodes.extend(conn["nodes"])
        if not conn["pageInfo"]["hasNextPage"]:
            break
        after = conn["pageInfo"]["endCursor"]
    return nodes

def language_counts_by_repo(repos):
    counts = {}
    for r in repos:
        langs = r.get("languages", {}).get("edges", [])
        seen = set()
        for e in langs:
            n = e["node"]["name"]
            if n not in seen:
                counts[n] = counts.get(n, 0) + 1
                seen.add(n)
    return [{"name": k, "used": v} for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]

def language_bytes_share(repos):
    totals = {}
    for r in repos:
        langs = r.get("languages", {}).get("edges", [])
        for e in langs:
            n = e["node"]["name"]
            s = int(e.get("size") or 0)
            totals[n] = totals.get(n, 0) + s
    total_bytes = sum(totals.values()) or 1
    out = [{"name": k, "bytes": v, "percent": round(100 * v / total_bytes, 2)} for k, v in totals.items()]
    out.sort(key=lambda x: (-x["bytes"], x["name"]))
    return out

def top_repos_by_stars(repos, n=12):
    return sorted(repos, key=lambda r: (-r["stargazerCount"], r["name"]))[:n]

def contributions_heatmap(login):
    d = run_query(QUERY_CONTRIBS_CAL, {"login": login})
    cal = d["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = []
    for w in cal["weeks"]:
        days = [{"date": c["date"], "count": c["contributionCount"], "weekday": c["weekday"], "color": c["color"]} for c in w["contributionDays"]]
        weeks.append({"firstDay": w["firstDay"], "days": days})
    return {
        "totalContributions": cal["totalContributions"],
        "weeks": weeks,
        "totalCommitContributions": d["user"]["contributionsCollection"]["totalCommitContributions"],
    }

def main():
    repos = paginate_repos(USERNAME)
    (DATA_DIR / "repos_top.json").write_text(json.dumps(top_repos_by_stars(repos, 12), indent=2), encoding="utf-8")
    (DATA_DIR / "languages.json").write_text(json.dumps(language_counts_by_repo(repos), indent=2), encoding="utf-8")
    (DATA_DIR / "lang_bytes.json").write_text(json.dumps(language_bytes_share(repos), indent=2), encoding="utf-8")
    (DATA_DIR / "heatmap.json").write_text(json.dumps(contributions_heatmap(USERNAME), indent=2), encoding="utf-8")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
