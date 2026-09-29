import html
import json
import logging
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
import httpx2

from app.core.skills import Skill
from app.models.quest import Quest, QuestRequirements
from app.repositories.quest_repository import get_quest_repository

logger = logging.getLogger(__name__)

USER_AGENT = "OSRSAccountOptimizer/1.0 (https://github.com/NJKimb/OSRS_Optimizer) Discord: JJoner"
WIKI_API_ENDPOINT = "https://oldschool.runescape.wiki/api.php"

SKILL_NAME_MAP = {
    "runecrafting": "runecraft",
    "hp": "hitpoints",
}


def fetch_wiki_page_content(page_title: str = "", prop: str | None = None) -> Any:
    """
    Fetches wikitext or parsed HTML from the OSRS Wiki API if prop is specified.
    If prop is None, queries the Wiki Bucket API for all quest entries.
    """
    if prop is not None:
        params = {"action": "parse", "page": page_title, "prop": prop, "format": "json"}
        response = httpx2.get(
            WIKI_API_ENDPOINT,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        if response.status_code == 200:
            data = response.json()
            if "error" in data:
                raise RuntimeError(
                    f"OSRS Wiki API error for '{page_title}': {data['error'].get('info')}"
                )
            return data["parse"][prop]["*"]
        else:
            raise RuntimeError(
                f"OSRS Wiki API request failed with status {response.status_code}"
            )
    else:
        query_string = "bucket('quest').select('page_name', 'official_difficulty', 'official_length', 'requirements').run()"
        params = {"action": "bucket", "format": "json", "query": query_string}
        response = httpx2.get(
            WIKI_API_ENDPOINT,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(
                f"OSRS Wiki Bucket API request failed with status {response.status_code}"
            )


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
            quest_candidate = bullet_match.group(1).strip()
            ignored_prefixes = ("File:", "Image:", "Category:", "Quest point")
            if not any(
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
                quest_name = html.unescape(row["data-rowid"]).strip()
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
    Legacy parser for `Quests/List` HTML using BeautifulSoup.
    Maintained for backwards compatibility and unit testing.
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


def sync_osrs_quests(
    save: bool = True, target_file: Path | None = None, reload_db: bool = True
) -> list[Quest]:
    """
    Performs automated synchronization of all OSRS quests using:
    1. The Wiki Bucket API (JSON response from bucket('quest')) for quest metadata and requirements
    2. The HTML response from `Quest_experience_rewards` (prop="text") for skill XP rewards
    3. Merges and validates via Pydantic Quest models
    4. Saves to quests.json if save=True
    5. Reloads the quest repository if reload_db=True
    """
    logger.info("Fetching quest list for quest points from OSRS Wiki...")
    quest_list_html = fetch_wiki_page_content("Quests/List", prop="text")
    base_quests = parse_quests_list(quest_list_html)
    quest_points_by_name = {
        quest["name"]: quest["quest_points"] for quest in base_quests
    }

    logger.info("Fetching quests from OSRS Wiki Bucket API...")
    bucket_data = fetch_wiki_page_content(prop=None)
    bucket_quests = bucket_data.get("bucket", [])
    logger.info(f"Retrieved {len(bucket_quests)} quests from Bucket API.")

    logger.info("Fetching quest experience rewards HTML...")
    quest_xp_html = fetch_wiki_page_content("Quest_experience_rewards", prop="text")
    quest_xp_rewards = parse_quest_xp_rewards(quest_xp_html)
    logger.info(f"Parsed XP rewards for {len(quest_xp_rewards)} quests.")

    quest_xp_rewards_lowercase = {
        quest_name.lower(): rewards for quest_name, rewards in quest_xp_rewards.items()
    }
    valid_skills = {skill.value for skill in Skill}
    repo = get_quest_repository()
    validated_quests: list[Quest] = []
    seen_quest_names: set[str] = set()

    for quest_item in bucket_quests:
        quest_name = quest_item.get("page_name")
        if not quest_name:
            continue
        if quest_name in seen_quest_names:
            continue
        seen_quest_names.add(quest_name)

        raw_difficulty = quest_item.get("official_difficulty")
        raw_length = quest_item.get("official_length")
        raw_requirements = quest_item.get("requirements", "")
        requirements_data = parse_bucket_requirements(raw_requirements)

        # Skip entries that aren't full official quests (e.g. miniquests or unreleased pitches)
        if not raw_difficulty or not raw_length:
            logger.warning(
                f"Skipping '{quest_name}': missing difficulty ({raw_difficulty}) or length ({raw_length})"
            )
            continue

        difficulty = str(raw_difficulty).strip()
        length = str(raw_length).strip().lower()

        typed_skill_requirements: dict[Skill, int] = {
            Skill(skill_name): level
            for skill_name, level in requirements_data["skills"].items()
            if skill_name in valid_skills
        }

        quest_xp = (
            quest_xp_rewards.get(quest_name)
            or quest_xp_rewards_lowercase.get(quest_name.lower())
            or {}
        )
        typed_xp_rewards: dict[Skill, int] = {
            Skill(skill_name): xp_amount
            for skill_name, xp_amount in quest_xp.items()
            if skill_name in valid_skills
        }

        # Look up quest points from Quests/List, fallback to the existing quest data
        existing_quest = repo.get(quest_name)
        quest_points = quest_points_by_name.get(quest_name, 0) or (
            existing_quest.quest_points if existing_quest else 0
        )

        requirements = QuestRequirements(
            quests=requirements_data["quests"],
            skills=typed_skill_requirements,
            boostable_skills=[
                Skill(skill_name)
                for skill_name in requirements_data["boostable_skills"]
                if skill_name in valid_skills
            ],
            quest_points=requirements_data["quest_points"],
        )

        quest = Quest(
            id=quest_name,
            name=quest_name,
            quest_points=quest_points,
            length=length,
            difficulty=difficulty,
            requirements=requirements,
            xp_rewards=typed_xp_rewards,
        )
        validated_quests.append(quest)

    if save:
        output_path = target_file or (
            Path(__file__).resolve().parents[2] / "data" / "quests.json"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        quest_data = [quest.model_dump(mode="json") for quest in validated_quests]
        with open(output_path, "w", encoding="utf-8") as output_file:
            json.dump(quest_data, output_file, indent=2, ensure_ascii=False)
        logger.info(
            f"Successfully saved {len(validated_quests)} quests to {output_path}"
        )

    if reload_db:
        repo.load()

    return validated_quests
