import html
import re
from typing import Any

from bs4 import BeautifulSoup

from app.models.quest import QuestRequirements
from app.models.skills import Skill

SKILL_NAME_MAP = {
    "runecrafting": "runecraft",
    "hp": "hitpoints",
}


def _to_skill(raw_name: str) -> Skill | None:
    """Maps a wiki skill name (e.g. "Runecrafting") to a Skill, or None if it isn't one."""
    name = raw_name.strip().lower()
    try:
        return Skill(SKILL_NAME_MAP.get(name, name))
    except ValueError:
        return None


def parse_bucket_requirements(requirements_text: str) -> QuestRequirements:
    """
    Parses the `requirements` field from the Bucket quest table:
      - Skill requirements from <span class="scp" data-skill="..." data-level="...">
      - Quest points requirements from data-skill="Quest points" or text
      - Prerequisite quests from wiki bullet links under quest completion sections
    """
    if not requirements_text or requirements_text.strip().lower() == "none":
        return QuestRequirements()

    skill_requirements: dict[Skill, int] = {}
    boostable_skills: list[Skill] = []
    required_quest_points = 0

    # 1. Extract skills and Quest points from data-skill / data-level tags.
    # Each requirement sits on its own line, followed by its boostable annotation.
    for line in requirements_text.splitlines():
        is_boostable = 'title="This requirement is boostable"' in line
        for match in re.finditer(r'data-skill="([^"]+)"\s+data-level="(\d+)"', line):
            raw_skill = match.group(1)
            level = int(match.group(2))
            if raw_skill.strip().lower() in ("quest points", "quest point"):
                required_quest_points = max(required_quest_points, level)
                continue
            skill = _to_skill(raw_skill)
            if skill is not None:
                skill_requirements[skill] = level
                if is_boostable and skill not in boostable_skills:
                    boostable_skills.append(skill)

    if required_quest_points == 0:
        quest_points_match = re.search(
            r"(\d+)\s+\[\[Quest points\]\]", requirements_text, re.IGNORECASE
        )
        if quest_points_match:
            required_quest_points = int(quest_points_match.group(1))

    # 2. Extract prerequisite quests
    prerequisite_quests: list[str] = []
    lines = requirements_text.splitlines()
    in_quest_section = False
    for line in lines:
        stripped_line = line.strip()
        if "completion of the following quest" in stripped_line.lower():
            in_quest_section = True
            continue

        bullet_match = re.match(
            r"^\*{1,6}\s*\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", stripped_line
        )
        if bullet_match:
            # Wiki links may use underscores in place of spaces
            quest_candidate = bullet_match.group(1).replace("_", " ").strip()
            ignored_prefixes = ("File:", "Image:", "Category:", "Quest point")
            # Links to page sections (e.g. "Balloon transport system#Grand Tree") aren't quests
            if "#" not in quest_candidate and not any(
                quest_candidate.startswith(prefix) for prefix in ignored_prefixes
            ):
                if in_quest_section or stripped_line.startswith("**"):
                    if quest_candidate not in prerequisite_quests:
                        prerequisite_quests.append(quest_candidate)
        elif in_quest_section and not stripped_line.startswith("*"):
            in_quest_section = False

    return QuestRequirements(
        quests=prerequisite_quests,
        skills=skill_requirements,
        boostable_skills=boostable_skills,
        quest_points=required_quest_points,
    )


def parse_quest_xp_rewards(html_text: str) -> dict[str, dict[Skill, int]]:
    """
    Parses the `Quest experience rewards` HTML, which has one table per skill.
    Returns {quest_name: {skill: xp_amount}}.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    xp_rewards_by_quest: dict[str, dict[Skill, int]] = {}

    for skill in Skill:
        heading = soup.find(
            lambda tag: tag.name in ["h3", "h2"]
            and tag.get_text(strip=True).lower().startswith(skill.value)
        )
        if not heading:
            continue
        table = heading.find_next("table", class_="wikitable")
        if not table:
            continue
        for row in table.find_all("tr", attrs={"data-rowid": True}):
            quest_name = html.unescape(str(row["data-rowid"])).strip()
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            xp_text = cells[2].get_text(strip=True).replace(",", "")
            amount_match = re.search(r"(\d+(?:\.\d+)?)", xp_text)
            if amount_match:
                xp_amount = int(float(amount_match.group(1)))
                xp_rewards_by_quest.setdefault(quest_name, {})[skill] = xp_amount

    return xp_rewards_by_quest


def parse_quests_list(html_text: str) -> list[dict[str, Any]]:
    """
    Parses the `Quests/List` HTML table into quest name, difficulty, and quest points.
    Skips miniquests and duplicate rows. Used by the sync as the source of quest points,
    which the Bucket API query doesn't include.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    parsed_quests = []
    seen_quest_names = set()

    for row in soup.find_all("tr", attrs={"data-rowid": True}):
        if row.find_previous(id="Miniquests"):
            continue

        cells = [cell.get_text(strip=True) for cell in row.find_all("td")]
        if len(cells) < 5:
            continue

        quest_name = cells[1]
        difficulty = cells[2]
        try:
            quest_points_match = re.search(r"\d+", cells[4])
            quest_points = int(quest_points_match.group(0)) if quest_points_match else 0
        except Exception:
            quest_points = 0

        if quest_name in seen_quest_names:
            continue
        seen_quest_names.add(quest_name)

        parsed_quests.append(
            {
                "id": quest_name,
                "name": quest_name,
                "difficulty": difficulty,
                "quest_points": quest_points,
            }
        )

    return parsed_quests
