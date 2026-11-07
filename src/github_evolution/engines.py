from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .models import State


def level_for_xp(xp: int, base: int = 100, growth: float = 1.35) -> int:
    level = 1
    spent = 0
    while xp >= spent + round(base * (level ** growth)):
        spent += round(base * (level ** growth))
        level += 1
    return level


def xp_for_next_level(level: int, base: int = 100, growth: float = 1.35) -> int:
    return round(base * (level ** growth))


def streaks(days: dict[str, int], today: date) -> tuple[int, int]:
    active = {date.fromisoformat(day) for day, count in days.items() if count > 0}
    longest = current = 0
    cursor = min(active) if active else today
    while cursor <= today:
        if cursor in active:
            current_run = 1
            while cursor + timedelta(days=current_run) in active:
                current_run += 1
            longest = max(longest, current_run)
            cursor += timedelta(days=current_run)
        else:
            cursor += timedelta(days=1)
    anchor = today if today in active else today - timedelta(days=1)
    while anchor in active:
        current += 1
        anchor -= timedelta(days=1)
    return current, longest


def apply_contributions(state: State, snapshot: Any, xp_config: dict[str, Any], today: date) -> list[str]:
    state.total_contributions = snapshot.total
    state.contribution_days.update(snapshot.days)
    state.categories = snapshot.categories
    state.active_days = sum(1 for count in state.contribution_days.values() if count > 0)
    gained = 0
    for day, count in snapshot.days.items():
        already = state.processed_days.get(day, 0)
        if count > already:
            gained += (count - already) * int(xp_config["contribution_xp"])
            state.processed_days[day] = count
    old_level = state.level
    state.xp += gained
    state.lifetime_xp += gained
    state.level = level_for_xp(state.xp, int(xp_config["level_base_xp"]), float(xp_config["level_growth"]))
    current, longest = streaks(state.contribution_days, today)
    state.current_streak, state.longest_streak = current, max(state.longest_streak, longest)
    if current in {int(key) for key in xp_config.get("streak_milestones", {})}:
        milestones = xp_config["streak_milestones"]
        milestone_xp = int(milestones.get(current, milestones.get(str(current), 0)))
        marker = f"streak:{current}:{today.isoformat()}"
        if marker not in state.recent_milestones:
            state.xp += milestone_xp
            state.lifetime_xp += milestone_xp
            state.recent_milestones.append(marker)
    if gained:
        state.xp_history.append({"date": today.isoformat(), "xp": gained, "reason": "contributions"})
    messages = [f"Level up: {old_level} -> {state.level}"] if state.level > old_level else []
    return messages


def evaluate_achievements(state: State, definitions: list[dict[str, Any]], now: str) -> list[str]:
    values = {"contributions": state.total_contributions, "streak": state.current_streak, "pull_requests": state.categories.get("pull_requests", 0), "issues": state.categories.get("issues", 0), "reviews": state.categories.get("reviews", 0), "level": state.level}
    unlocked = {item["id"] for item in state.achievements}
    messages = []
    for achievement in definitions:
        if achievement["id"] in unlocked:
            continue
        expression = achievement["condition"]
        name, operator, raw = expression.split()
        threshold = int(raw)
        if operator == ">=" and values.get(name, 0) >= threshold:
            state.achievements.append({"id": achievement["id"], "name": achievement["name"], "icon": achievement.get("icon", "*"), "unlocked_at": now})
            reward = int(achievement.get("xp", 0))
            state.xp += reward
            state.lifetime_xp += reward
            state.xp_history.append({"date": now, "xp": reward, "reason": f"achievement:{achievement['id']}"})
            messages.append(achievement["name"])
    return messages


def apply_projects(state: State, projects: list[dict[str, Any]], default_xp: int, now: str) -> list[str]:
    existing = {item["id"] for item in state.projects}
    messages = []
    for project in projects:
        project_id = project.get("id") or project["name"].lower().replace(" ", "-")
        if project.get("completed", True) is False or project_id in existing:
            continue
        reward = int(project.get("xp", default_xp))
        state.projects.append({**project, "id": project_id, "rewarded_at": now})
        state.xp += reward
        state.lifetime_xp += reward
        state.xp_history.append({"date": now, "xp": reward, "reason": f"project:{project_id}"})
        if project.get("building") and project["building"] not in state.unlocked_buildings:
            state.unlocked_buildings.append(project["building"])
        messages.append(project["name"])
    return messages


def update_city(state: State, city_config: dict[str, Any]) -> None:
    state.city_level = state.level
    unlocked = set(state.unlocked_buildings)
    for tier in city_config["levels"]:
        if state.level >= int(tier["level"]):
            unlocked.update(tier["unlock"])
    state.unlocked_buildings = sorted(unlocked)
