import json
import logging
from pathlib import Path

from app.models.quest import Quest
from app.repositories.quest_repository import DEFAULT_DATA_PATH, get_quest_repository
from app.services.wiki.client import fetch_quest_bucket, fetch_wiki_page_content
from app.services.wiki.parsers import (
    parse_bucket_requirements,
    parse_quest_xp_rewards,
    parse_quests_list,
)

logger = logging.getLogger(__name__)


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
    bucket_data = fetch_quest_bucket()
    bucket_quests = bucket_data.get("bucket", [])
    logger.info(f"Retrieved {len(bucket_quests)} quests from Bucket API.")

    logger.info("Fetching quest experience rewards HTML...")
    quest_xp_html = fetch_wiki_page_content("Quest_experience_rewards", prop="text")
    quest_xp_rewards = parse_quest_xp_rewards(quest_xp_html)
    logger.info(f"Parsed XP rewards for {len(quest_xp_rewards)} quests.")

    quest_xp_rewards_lowercase = {
        quest_name.lower(): rewards for quest_name, rewards in quest_xp_rewards.items()
    }
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

        # Skip entries that aren't full official quests (e.g. miniquests or unreleased pitches)
        if not raw_difficulty or not raw_length:
            logger.warning(
                f"Skipping '{quest_name}': missing difficulty ({raw_difficulty}) or length ({raw_length})"
            )
            continue

        difficulty = str(raw_difficulty).strip()
        length = str(raw_length).strip().lower()

        xp_rewards = (
            quest_xp_rewards.get(quest_name)
            or quest_xp_rewards_lowercase.get(quest_name.lower())
            or {}
        )

        # Look up quest points from Quests/List, fallback to the existing quest data
        existing_quest = repo.get(quest_name)
        quest_points = quest_points_by_name.get(quest_name, 0) or (
            existing_quest.quest_points if existing_quest else 0
        )

        quest = Quest(
            id=quest_name,
            name=quest_name,
            quest_points=quest_points,
            length=length,
            difficulty=difficulty,
            requirements=parse_bucket_requirements(quest_item.get("requirements", "")),
            xp_rewards=xp_rewards,
        )
        validated_quests.append(quest)

    if save:
        output_path = target_file or DEFAULT_DATA_PATH
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
