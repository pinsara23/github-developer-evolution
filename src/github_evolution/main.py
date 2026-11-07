from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .engines import apply_contributions, apply_projects, evaluate_achievements, level_for_xp, update_city
from .github_api import GitHubClient
from .models import ContributionSnapshot
from .render import update_readme, write_svgs
from .storage import load_state, save_state


ROOT = Path(__file__).resolve().parents[2]


def config(name: str) -> dict:
    with (ROOT / "config" / name).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def run(mock: bool = False) -> None:
    load_dotenv(ROOT / ".env")
    username = os.getenv("GITHUB_USERNAME", "pinsara23")
    state = load_state(ROOT / "data" / "state.json", username)
    today = date.today()
    if mock:
        snapshot = ContributionSnapshot(state.total_contributions + 3, {today.isoformat(): 3}, {"commits": 3, "issues": 0, "pull_requests": 0, "reviews": 0, "restricted": 0}, datetime.now(timezone.utc).isoformat())
    else:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN is required for live synchronization; use --mock for local rendering")
        snapshot = GitHubClient(token).fetch_contributions(username, datetime.now(timezone.utc) - timedelta(days=365), datetime.now(timezone.utc))
    state.username = username
    messages = apply_contributions(state, snapshot, config("xp.yaml"), today)
    messages += evaluate_achievements(state, config("achievements.yaml"), datetime.now(timezone.utc).isoformat())
    projects = config("projects.yaml").get("projects", [])
    messages += apply_projects(state, projects, int(config("xp.yaml")["project_default_xp"]), datetime.now(timezone.utc).isoformat())
    xp_settings = config("xp.yaml")
    state.level = max(1, level_for_xp(state.xp, int(xp_settings["level_base_xp"]), float(xp_settings["level_growth"])))
    messages += evaluate_achievements(state, config("achievements.yaml"), datetime.now(timezone.utc).isoformat())
    state.level = max(1, level_for_xp(state.xp, int(xp_settings["level_base_xp"]), float(xp_settings["level_growth"])))
    update_city(state, config("city.yaml"))
    state.last_sync = datetime.now(timezone.utc).isoformat()
    state.recent_milestones = (state.recent_milestones + messages)[-12:]
    save_state(ROOT / "data" / "state.json", state)
    write_svgs(state, ROOT / "generated")
    update_readme(ROOT / "README.md", "generated/developer-dashboard.svg")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synchronize GitHub Developer Evolution")
    parser.add_argument("--mock", action="store_true", help="Generate a local deterministic sample update")
    run(mock=parser.parse_args().mock)
