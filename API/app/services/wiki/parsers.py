import html
import re

from bs4 import BeautifulSoup

from app.models.quest import QuestRequirements
from app.models.skills import Skill

SKILL_NAME_MAP = {
    "runecrafting": "runecraft",
    "hp": "hitpoints",
}

# A skill or quest point requirement, e.g. data-skill="Agility" data-level="70"
SKILL_LEVEL_PATTERN = re.compile(r'data-skill="([^"]+)"\s+data-level="(\d+)"')
# Quest points written as plain text, e.g. "32 [[Quest points]]"
QUEST_POINTS_TEXT_PATTERN = re.compile(r"(\d+)\s+\[\[Quest points\]\]", re.IGNORECASE)
# A bulleted wiki link, e.g. "**[[Druidic Ritual]]" or "*[[Page|label]]", capturing the page
WIKI_BULLET_LINK_PATTERN = re.compile(r"^\*{1,6}\s*\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
# An XP amount that may have a decimal part, e.g. "1000.5"
XP_AMOUNT_PATTERN = re.compile(r"\d+(?:\.\d+)?")

BOOSTABLE_MARKER = 'title="This requirement is boostable"'
# Links to these pages are never prerequisite quests
IGNORED_LINK_PREFIXES = ("File:", "Image:", "Category:", "Quest point")


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

    skill_requirements, boostable_skills = _parse_skill_requirements(requirements_text)
    return QuestRequirements(
        quests=_parse_prerequisite_quests(requirements_text),
        skills=skill_requirements,
        boostable_skills=boostable_skills,
        quest_points=_parse_quest_points(requirements_text),
    )


def _parse_skill_requirements(
    requirements_text: str,
) -> tuple[dict[Skill, int], list[Skill]]:
    """Returns the required level per skill, and which of those skills are boostable."""
    skill_requirements: dict[Skill, int] = {}
    boostable_skills: list[Skill] = []
    # Each requirement sits on its own line, followed by its boostable annotation
    for line in requirements_text.splitlines():
        is_boostable = BOOSTABLE_MARKER in line
        for match in SKILL_LEVEL_PATTERN.finditer(line):
            skill = _to_skill(match.group(1))
            if skill is None:
                continue
            skill_requirements[skill] = int(match.group(2))
            if is_boostable and skill not in boostable_skills:
                boostable_skills.append(skill)
    return skill_requirements, boostable_skills


def _parse_quest_points(requirements_text: str) -> int:
    """Returns the required quest points, from a data-skill tag or else plain text."""
    required_quest_points = 0
    for match in SKILL_LEVEL_PATTERN.finditer(requirements_text):
        if match.group(1).strip().lower() in ("quest points", "quest point"):
            required_quest_points = max(required_quest_points, int(match.group(2)))
    if required_quest_points == 0:
        quest_points_match = QUEST_POINTS_TEXT_PATTERN.search(requirements_text)
        if quest_points_match:
            required_quest_points = int(quest_points_match.group(1))
    return required_quest_points


def _parse_prerequisite_quests(requirements_text: str) -> list[str]:
    """Returns the quests linked from bullet lists of required quests."""
    prerequisite_quests: list[str] = []
    in_quest_section = False
    for line in requirements_text.splitlines():
        stripped_line = line.strip()
        if "completion of the following quest" in stripped_line.lower():
            in_quest_section = True
            continue

        bullet_match = WIKI_BULLET_LINK_PATTERN.match(stripped_line)
        if not bullet_match:
            # Any non-bullet line ends the list of required quests
            if not stripped_line.startswith("*"):
                in_quest_section = False
            continue

        # Outside a required quests list, only nested (**) bullets count as quests
        if not in_quest_section and not stripped_line.startswith("**"):
            continue

        # Wiki links may use underscores in place of spaces
        quest_name = bullet_match.group(1).replace("_", " ").strip()
        if _is_quest_link(quest_name) and quest_name not in prerequisite_quests:
            prerequisite_quests.append(quest_name)
    return prerequisite_quests


def _is_quest_link(page_name: str) -> bool:
    """Returns False for links to files, categories and page sections."""
    # Links to page sections (e.g. "Balloon transport system#Grand Tree") aren't quests
    return "#" not in page_name and not page_name.startswith(IGNORED_LINK_PREFIXES)


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
            amount_match = XP_AMOUNT_PATTERN.search(xp_text)
            if amount_match:
                xp_amount = int(float(amount_match.group(0)))
                xp_rewards_by_quest.setdefault(quest_name, {})[skill] = xp_amount

    return xp_rewards_by_quest


def parse_quest_points(html_text: str) -> dict[str, int]:
    """
    Parses the `Quests/List` HTML table into {quest_name: quest_points}, skipping
    miniquests. The sync's source of quest points, since the Bucket API query lacks them.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    quest_points_by_name: dict[str, int] = {}

    for row in soup.find_all("tr", attrs={"data-rowid": True}):
        if row.find_previous(id="Miniquests"):
            continue

        cells = [cell.get_text(strip=True) for cell in row.find_all("td")]
        if len(cells) < 5:
            continue

        quest_name = cells[1]
        quest_points_match = re.search(r"\d+", cells[4])
        quest_points = int(quest_points_match.group(0)) if quest_points_match else 0
        # Keep the first row when a quest is listed more than once
        quest_points_by_name.setdefault(quest_name, quest_points)

    return quest_points_by_name
