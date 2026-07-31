"""
github_data.py
Handles all communication with the GitHub REST API and turns the raw
JSON responses into clean pandas DataFrames the dashboard can plot.

No auth token is required for light usage (60 requests/hour), but if you
add a GITHUB_TOKEN in your .env, rate limits jump to 5,000 requests/hour.
"""

import os
import requests
import pandas as pd
from datetime import datetime
from collections import Counter

GITHUB_API = "https://api.github.com"


class GitHubAPIError(Exception):
    """Raised for any GitHub API failure, with a message safe to show in the UI."""
    pass


def _headers():
    """Build request headers, using a token if one is available."""
    token = os.getenv("GITHUB_TOKEN")
    # GitHub requires a User-Agent on all requests, and rejects requests without one.
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "dev-activity-dashboard"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(url: str, params: dict | None = None):
    """Shared GET wrapper that turns common GitHub failures into friendly errors."""
    resp = requests.get(url, headers=_headers(), params=params, timeout=10)

    if resp.status_code == 403 and resp.headers.get("x-ratelimit-remaining") == "0":
        raise GitHubAPIError(
            "GitHub API rate limit hit. Add a GITHUB_TOKEN to your .env file to raise "
            "the limit from 60 to 5,000 requests/hour (see .env.example for instructions)."
        )
    if resp.status_code == 404:
        raise GitHubAPIError("That GitHub username doesn't exist. Double-check the spelling.")
    resp.raise_for_status()
    return resp


def fetch_user_profile(username: str) -> dict:
    """Basic profile info: avatar, bio, followers, public repo count, etc."""
    return _get(f"{GITHUB_API}/users/{username}").json()


def fetch_repos(username: str) -> list[dict]:
    """All public repos for a user, sorted by most recently pushed."""
    repos = []
    page = 1
    while True:
        batch = _get(
            f"{GITHUB_API}/users/{username}/repos",
            params={"per_page": 100, "page": page, "sort": "pushed"},
        ).json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
        if page > 5:  # safety cap: 500 repos is plenty for a dashboard
            break
    return repos


def repos_to_dataframe(repos: list[dict]) -> pd.DataFrame:
    """Clean the raw repo JSON into a tidy DataFrame."""
    if not repos:
        return pd.DataFrame(
            columns=["name", "language", "stars", "forks", "size_kb", "pushed_at", "created_at", "is_fork"]
        )

    df = pd.DataFrame(
        [
            {
                "name": r["name"],
                "language": r.get("language") or "Unspecified",
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "size_kb": r.get("size", 0),
                "pushed_at": r.get("pushed_at"),
                "created_at": r.get("created_at"),
                "is_fork": r.get("fork", False),
            }
            for r in repos
        ]
    )
    df["pushed_at"] = pd.to_datetime(df["pushed_at"])
    df["created_at"] = pd.to_datetime(df["created_at"])
    return df.sort_values("pushed_at", ascending=False).reset_index(drop=True)


def language_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Count of repos per language, excluding forks so it reflects original work."""
    original = df[~df["is_fork"]]
    counts = original["language"].value_counts().reset_index()
    counts.columns = ["language", "repo_count"]
    return counts


def fetch_commit_activity(username: str, repo_name: str) -> list[dict]:
    """
    Weekly commit activity for a single repo (last ~52 weeks).
    GitHub sometimes returns 202 while it computes stats in the background —
    callers should be prepared for an empty result on the first try.
    """
    resp = requests.get(
        f"{GITHUB_API}/repos/{username}/{repo_name}/stats/commit_activity",
        headers=_headers(),
        timeout=10,
    )
    if resp.status_code != 200:
        return []
    data = resp.json()
    return data if isinstance(data, list) else []


def commit_activity_to_dataframe(username: str, repo_names: list[str], max_repos: int = 5) -> pd.DataFrame:
    """
    Aggregate weekly commit counts across a user's most recently active repos.
    Capped at max_repos to keep API calls (and load time) reasonable.
    """
    all_weeks = Counter()
    for repo in repo_names[:max_repos]:
        weeks = fetch_commit_activity(username, repo)
        for w in weeks:
            date = datetime.utcfromtimestamp(w["week"]).date()
            all_weeks[date] += w["total"]

    if not all_weeks:
        return pd.DataFrame(columns=["week", "commits"])

    df = pd.DataFrame(sorted(all_weeks.items()), columns=["week", "commits"])
    return df
