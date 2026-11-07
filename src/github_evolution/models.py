from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ContributionSnapshot:
    total: int
    days: dict[str, int]
    categories: dict[str, int]
    fetched_at: str


@dataclass
class State:
    version: int = 1
    username: str = "pinsara23"
    contribution_days: dict[str, int] = field(default_factory=dict)
    categories: dict[str, int] = field(default_factory=dict)
    total_contributions: int = 0
    xp: int = 0
    lifetime_xp: int = 0
    level: int = 1
    xp_history: list[dict[str, Any]] = field(default_factory=list)
    processed_days: dict[str, int] = field(default_factory=dict)
    current_streak: int = 0
    longest_streak: int = 0
    active_days: int = 0
    achievements: list[dict[str, Any]] = field(default_factory=list)
    projects: list[dict[str, Any]] = field(default_factory=list)
    unlocked_buildings: list[str] = field(default_factory=list)
    city_level: int = 1
    last_sync: str | None = None
    recent_milestones: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "State":
        fields = {name: data[name] for name in cls.__dataclass_fields__ if name in data}
        return cls(**fields)

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}
