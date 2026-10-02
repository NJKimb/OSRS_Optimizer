import html
import re
from typing import Any

from bs4 import BeautifulSoup

from app.models.skills import Skill

SKILL_NAME_MAP = {
    "runecrafting": "runecraft",
    "hp": "hitpoints",
}


def parse_bucket_requirements(requirements_text: str) -> dict[str, Any]:
    """
    Parses the `requirements` field from the Bucket quest table:
      - Skill requirements from <span class="scp" data-skill="..." data-level="...">
      - Quest points requirements from data-skill="Quest points" or text
      - Prerequisite quests from wiki bullet links under quest completion sections
    """
    if not requirements_text or requirements_text.strip().lower() == "none":
        return {"skills": {}, "boostable_skills": [], "quests": [], "quest_points": 0}

    skill_requirements: dict[str, int] = {}
    boostable_skills: list[str] = []
    required_quest_points = 0
    valid_skills = {skill.value for skill in Skill}

    # 1. Extract skills and Quest points from data-skill / data-level tags.
    # Each requirement sits on its own line, followed by its boostable annotation.
    for line in requirements_text.splitlines():
        is_boostable = 'title="This requirement is boostable"' in line
        for match in re.finditer(r'data-skill="([^"]+)"\s+data-level="(\d+)"', line):
            raw_skill = match.group(1).strip()
            level = int(match.group(2))
            raw_skill_lower = raw_skill.lower()
            if raw_skill_lower in ("quest points", "quest point"):
                required_quest_points = max(required_quest_points, level)
                continue
            canonical_skill = SKILL_NAME_MAP.get(raw_skill_lower, raw_skill_lower)
            if canonical_skill in valid_skills:
                skill_requirements[canonical_skill] = level
                if is_boostable and canonical_skill not in boostable_skills:
                    boostable_skills.append(canonical_skill)

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

    return {
        "skills": skill_requirements,
        "boostable_skills": boostable_skills,
        "quests": prerequisite_quests,
        "quest_points": required_quest_points,
    }


def parse_quest_xp_rewards(content: str) -> dict[str, dict[str, int]]:
    """
    Parses `Quest experience rewards` content to extract all skill experience rewards.
    Supports both parsed HTML (prop="text") and raw wikitext (prop="wikitext").
    Returns {quest_name: {skill: xp_amount}}.
    """
    valid_skills = {skill.value for skill in Skill}
    xp_rewards_by_quest: dict[str, dict[str, int]] = {}

    # Check if content is HTML
    if "<table" in content:
        soup = BeautifulSoup(content, "html.parser")
        skill_names = [skill.value for skill in Skill]

        for skill_name in skill_names:
            heading = soup.find(
                lambda tag: tag.name in ["h3", "h2"]
                and tag.get_text(strip=True).lower().startswith(skill_name)
            )
            if not heading:
                continue
            table = heading.find_next("table", class_="wikitable")
            if not table:
                continue
            for row in table.find_all("tr", attrs={"data-rowid": True}):
                quest_name = html.unescape(str(row["data-rowid"])).strip()
                cells = row.find_all("td")
                if len(cells) >= 3:
                    xp_text = cells[2].get_text(strip=True).replace(",", "")
                    amount_match = re.search(r"(\d+(?:\.\d+)?)", xp_text)
                    if amount_match:
                        xp_amount = int(float(amount_match.group(1)))
                        if quest_name not in xp_rewards_by_quest:
                            xp_rewards_by_quest[quest_name] = {}
                        xp_rewards_by_quest[quest_name][skill_name] = xp_amount
    else:
        # Fallback for wikitext format
        matches = re.findall(
            r'data-rowid="([^"]+)"[\s\S]*?\{\{\+=\|([a-z]+)\|([0-9.,]+)', content
        )
        for raw_quest_name, raw_skill, raw_amount in matches:
            xp_amount = int(float(raw_amount.replace(",", "")))
            quest_name = html.unescape(raw_quest_name).strip()
            canonical_skill = SKILL_NAME_MAP.get(raw_skill.lower(), raw_skill.lower())
            if canonical_skill not in valid_skills:
                continue
            if quest_name not in xp_rewards_by_quest:
                xp_rewards_by_quest[quest_name] = {}
            xp_rewards_by_quest[quest_name][canonical_skill] = xp_amount

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
