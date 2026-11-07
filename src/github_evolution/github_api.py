from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from .models import ContributionSnapshot

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
      commitContributionsByRepository(maxRepositories: 100) { contributions(first: 1) { totalCount } }
      issueContributions(first: 1) { totalCount }
      pullRequestContributions(first: 1) { totalCount }
      pullRequestReviewContributions(first: 1) { totalCount }
      restrictedContributionsCount
    }
  }
}
"""


def parse_contribution_response(payload: dict[str, Any]) -> ContributionSnapshot:
    if payload.get("errors"):
        raise RuntimeError("GitHub GraphQL error: " + "; ".join(str(e.get("message", e)) for e in payload["errors"]))
    try:
        collection = payload["data"]["user"]["contributionsCollection"]
        calendar = collection["contributionCalendar"]
        days = {day["date"]: int(day["contributionCount"]) for week in calendar["weeks"] for day in week["contributionDays"]}
        categories = {
            "commits": sum(item["contributions"]["totalCount"] for item in collection.get("commitContributionsByRepository", [])),
            "issues": collection.get("issueContributions", {}).get("totalCount", 0),
            "pull_requests": collection.get("pullRequestContributions", {}).get("totalCount", 0),
            "reviews": collection.get("pullRequestReviewContributions", {}).get("totalCount", 0),
            "restricted": collection.get("restrictedContributionsCount", 0),
        }
        return ContributionSnapshot(int(calendar["totalContributions"]), days, {key: int(value) for key, value in categories.items()}, datetime.now(timezone.utc).isoformat())
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid GitHub contribution response: {exc}") from exc


class GitHubClient:
    def __init__(self, token: str, timeout: int = 30) -> None:
        self.token = token
        self.timeout = timeout

    def fetch_contributions(self, username: str, start: datetime, end: datetime) -> ContributionSnapshot:
        response = requests.post(
            "https://api.github.com/graphql",
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
            json={"query": QUERY, "variables": {"login": username, "from": start.isoformat(), "to": end.isoformat()}},
            timeout=self.timeout,
        )
        if response.status_code == 401:
            raise RuntimeError("GitHub token is invalid or expired")
        if response.status_code == 403:
            raise RuntimeError("GitHub API rate limit or permission failure")
        response.raise_for_status()
        return parse_contribution_response(response.json())
