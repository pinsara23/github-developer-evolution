from datetime import date
from pathlib import Path

import yaml

from github_evolution.engines import apply_contributions, apply_projects, evaluate_achievements, level_for_xp, streaks
from github_evolution.github_api import parse_contribution_response
from github_evolution.models import ContributionSnapshot, State
from github_evolution.render import render_city, update_readme
from github_evolution.storage import load_state, save_state


def snapshot(days, total=None):
    return ContributionSnapshot(total or sum(days.values()), days, {"commits": 2, "issues": 1, "pull_requests": 1, "reviews": 0, "restricted": 0}, "now")


def test_graphql_calendar_is_canonical_and_categories_are_separate():
    payload = {"data": {"user": {"contributionsCollection": {"contributionCalendar": {"totalContributions": 7, "weeks": [{"contributionDays": [{"date": "2026-01-01", "contributionCount": 7}]}]}, "commitContributionsByRepository": [{"contributions": {"totalCount": 3}}], "issueContributions": {"totalCount": 2}, "pullRequestContributions": {"totalCount": 1}, "pullRequestReviewContributions": {"totalCount": 1}, "restrictedContributionsCount": 0}}}}
    result = parse_contribution_response(payload)
    assert result.total == 7
    assert result.days == {"2026-01-01": 7}
    assert result.categories["commits"] == 3


def test_streak_today_yesterday_and_gap():
    assert streaks({"2026-01-01": 1, "2026-01-02": 1}, date(2026, 1, 2)) == (2, 2)
    assert streaks({"2026-01-01": 1, "2026-01-02": 1}, date(2026, 1, 3))[0] == 2
    assert streaks({"2026-01-01": 1, "2026-01-02": 1}, date(2026, 1, 4))[0] == 0
    assert streaks({"2025-12-01": 1}, date(2026, 1, 3))[0] == 0


def test_xp_is_idempotent_and_level_progresses():
    state = State()
    settings = {"contribution_xp": 10, "level_base_xp": 100, "level_growth": 1.35, "streak_milestones": {}}
    data = snapshot({"2026-01-01": 2})
    apply_contributions(state, data, settings, date(2026, 1, 1))
    apply_contributions(state, data, settings, date(2026, 1, 1))
    assert state.xp == 20
    assert state.level == level_for_xp(20)


def test_achievements_unlock_once():
    state = State(total_contributions=1)
    definitions = [{"id": "first", "name": "First", "condition": "contributions >= 1", "xp": 50}]
    assert evaluate_achievements(state, definitions, "now") == ["First"]
    assert evaluate_achievements(state, definitions, "later") == []
    assert state.xp == 50


def test_project_reward_is_explicit_and_idempotent():
    state = State()
    project = {"id": "demo", "name": "Demo", "completed": True, "xp": 300, "building": "dev-lab"}
    assert apply_projects(state, [project], 500, "now") == ["Demo"]
    assert apply_projects(state, [project], 500, "later") == []
    assert state.xp == 300 and state.unlocked_buildings == ["dev-lab"]


def test_atomic_state_round_trip(tmp_path: Path):
    path = tmp_path / "state.json"
    state = State(username="test", xp=42)
    save_state(path, state)
    assert load_state(path).xp == 42


def test_city_and_readme_are_real_and_preserve_content(tmp_path: Path):
    state = State(level=5, city_level=5, unlocked_buildings=["developer-house", "office-tower"], total_contributions=4)
    svg = render_city(state)
    assert "DEVELOPER CITY" in svg and "<polygon" in svg
    readme = tmp_path / "README.md"
    readme.write_text("# Me\n\n## GitHub Activity\n\nExisting stats\n", encoding="utf-8")
    update_readme(readme, "ignored")
    content = readme.read_text(encoding="utf-8")
    assert "# Me" in content and "Existing stats" in content and content.count("DEVELOPER-EVOLUTION:START") == 1
