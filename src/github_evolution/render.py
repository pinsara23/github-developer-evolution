from __future__ import annotations

from html import escape
from pathlib import Path

from .engines import xp_for_next_level
from .models import State


def _building(x: int, y: int, width: int, height: int, color: str, label: str) -> str:
    roof = f"{x},{y} {x + width // 2},{y - 22} {x + width},{y}"
    return f'<g><polygon points="{roof}" fill="#f4c95d" stroke="#17233b" stroke-width="3"/><rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{color}" stroke="#17233b" stroke-width="3"/><path d="M{x + 12} {y + 22}h12v18H{x + 12}z M{x + width - 25} {y + 22}h12v18H{x + width - 25}z" fill="#a8d8df"/><text x="{x + width // 2}" y="{y + height - 12}" text-anchor="middle" class="tiny">{escape(label)}</text></g>'


def render_city(state: State) -> str:
    buildings = list(state.unlocked_buildings)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 430" role="img" aria-label="Isometric developer city">', '<style>text{font-family:monospace}.tiny{font-size:10px;fill:#fff}.pixel{shape-rendering:crispEdges}</style>', '<rect width="760" height="430" fill="#10243d"/><path d="M0 290L380 90 760 290 380 430z" fill="#254b52"/><path d="M30 300L380 120 730 300M180 390L520 210M160 220L530 400" fill="none" stroke="#d7b75c" stroke-width="10" opacity=".8"/>']
    positions = [(180, 236, 100, 105, "#d76f51", "HOUSE"), (330, 210, 115, 145, "#3e86a0", "HQ"), (500, 245, 120, 110, "#8e5aa4", "OFFICE"), (270, 310, 92, 75, "#376b8c", "LAB"), (440, 320, 95, 65, "#c46b47", "DATA")]
    labels = ["HOUSE", "HQ", "OFFICE", "LAB", "DATA"]
    for index, (x, y, width, height, color, label) in enumerate(positions):
        if index < len(buildings) or index == 1:
            parts.append(_building(x, y, width, height, color, label if index != 1 else "HQ"))
    for x, y in [(90, 275), (650, 276), (125, 350), (625, 350), (570, 160)]:
        parts.append(f'<g class="pixel"><rect x="{x + 8}" y="{y}" width="8" height="30" fill="#5b4435"/><circle cx="{x + 12}" cy="{y - 3}" r="20" fill="#62a86b"/><circle cx="{x + 28}" cy="{y + 3}" r="15" fill="#4d965f"/></g>')
    parts.extend([f'<text x="28" y="38" fill="#f4c95d" font-size="24" font-weight="bold">DEVELOPER CITY // LVL {state.city_level}</text>', f'<text x="30" y="65" fill="#b7d7d9" font-size="14">{state.active_days} active days  |  {len(state.achievements)} achievements  |  {len(state.projects)} projects</text>', "</svg>"])
    return "".join(parts)


def render_dashboard(state: State) -> str:
    next_xp = xp_for_next_level(state.level)
    progress = min(1.0, state.xp / max(1, next_xp))
    achievement_text = ", ".join(item["name"] for item in state.achievements[-4:]) or "No milestones yet"
    city = render_city(state).replace('viewBox="0 0 760 430"', 'x="30" y="270" width="700" height="395" viewBox="0 0 760 430"')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 820 700" role="img" aria-label="GitHub Developer Evolution dashboard">
<style>text{{font-family:monospace}}.muted{{fill:#9db7c7;font-size:13px}}.value{{fill:#f4c95d;font-size:24px;font-weight:bold}}.heading{{fill:#f4c95d;font-size:16px;font-weight:bold}}</style>
<rect width="820" height="700" rx="8" fill="#10243d"/><rect x="18" y="18" width="784" height="96" rx="5" fill="#173653" stroke="#376b8c" stroke-width="2"/>
<text x="38" y="51" fill="#f4c95d" font-size="25" font-weight="bold">GITHUB DEVELOPER EVOLUTION</text><text x="38" y="80" class="muted">A living city built from real contribution activity</text>
<text x="38" y="150" class="heading">LEVEL</text><text x="38" y="180" class="value">{state.level}</text><text x="145" y="150" class="heading">XP</text><text x="145" y="180" class="value">{state.xp:,}</text><text x="285" y="150" class="heading">CONTRIBUTIONS</text><text x="285" y="180" class="value">{state.total_contributions:,}</text><text x="510" y="150" class="heading">STREAK</text><text x="510" y="180" class="value">{state.current_streak} days</text>
<rect x="38" y="202" width="700" height="16" rx="3" fill="#244459"/><rect x="38" y="202" width="{700 * progress:.2f}" height="16" rx="3" fill="#65c18c"/><text x="38" y="245" class="muted">{state.xp:,} / {next_xp:,} XP to next level  |  longest streak: {state.longest_streak} days</text>
<text x="38" y="270" class="heading">RECENT UNLOCKS</text><text x="38" y="292" class="muted">{escape(achievement_text)}</text>{city}</svg>'''


def write_svgs(state: State, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "developer-city.svg").write_text(render_city(state), encoding="utf-8")
    (output_dir / "developer-dashboard.svg").write_text(render_dashboard(state), encoding="utf-8")


def update_readme(path: Path, dashboard: str) -> None:
    start = "<!-- DEVELOPER-EVOLUTION:START -->"
    end = "<!-- DEVELOPER-EVOLUTION:END -->"
    block = f"{start}\n![Developer Evolution](generated/developer-dashboard.svg)\n{end}"
    content = path.read_text(encoding="utf-8") if path.exists() else "# GitHub Developer Evolution\n\n## GitHub Activity\n"
    if start in content and end in content:
        before, remainder = content.split(start, 1)
        _, after = remainder.split(end, 1)
        content = before + block + after
    else:
        marker = "## GitHub Activity"
        content = content.replace(marker, block + "\n\n" + marker, 1) if marker in content else content.rstrip() + "\n\n" + block + "\n"
    path.write_text(content, encoding="utf-8")
