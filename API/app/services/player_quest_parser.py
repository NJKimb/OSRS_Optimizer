import json
import logging
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)

class QuestStates(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"

# Map RuneLite character-exporter subquest names to OSRS Wiki database canonical names
RFD_NAME_MAP: dict[str, str] = {
    "recipe for disaster - another cook's quest": "Recipe for Disaster/Another Cook's Quest",
    "recipe for disaster - mountain dwarf": "Recipe for Disaster/Freeing the Mountain Dwarf",
    "recipe for disaster - wartface & bentnoze": "Recipe for Disaster/Freeing the Goblin generals",
    "recipe for disaster - pirate pete": "Recipe for Disaster/Freeing Pirate Pete",
    "recipe for disaster - lumbridge guide": "Recipe for Disaster/Freeing the Lumbridge Guide",
    "recipe for disaster - evil dave": "Recipe for Disaster/Freeing Evil Dave",
    "recipe for disaster - skrach uglogwee": "Recipe for Disaster/Freeing Skrach Uglogwee",
    "recipe for disaster - sir amik varze": "Recipe for Disaster/Freeing Sir Amik Varze",
    "recipe for disaster - king awowogei": "Recipe for Disaster/Freeing King Awowogei",
    "recipe for disaster - culinaromancer": "Recipe for Disaster/Defeating the Culinaromancer",
}

def normalize_quest_name(name: str) -> str:
    """Returns canonical quest name if an alias exists, otherwise returns original name."""
    cleaned = name.strip()
    return RFD_NAME_MAP.get(cleaned.lower(), cleaned)

def parse_player_quest_status(quests: Any) -> set[str]:
    """
    Parses RuneLite character-exporter quest data and extracts all
    quest names where state is FINISHED. Supports raw JSON strings,
    character-exporter dicts, flat dicts, or lists.
    """
    if not quests:
        return set()

    # 1. If passed as a string, parse repeatedly to handle any double-stringification
    while isinstance(quests, str):
        try:
            quests = json.loads(quests)
        except (json.JSONDecodeError, TypeError):
            logger.error("Failed to parse quest JSON string.")
            return set()

    finished_quests: set[str] = set()

    # 2. Dictionary input
    if isinstance(quests, dict):
        if "quests" in quests and isinstance(quests["quests"], (list, dict)):
            quest_list = quests["quests"]
        else:
            # Handle direct dictionary e.g. {"Cook's Assistant": "FINISHED"}
            for name, val in quests.items():
                state = (val.get("state") or val.get("status")) if isinstance(val, dict) else val
                if state and str(state).strip().upper() == QuestStates.FINISHED:
                    finished_quests.add(normalize_quest_name(str(name)))
            logger.info(f"Extracted {len(finished_quests)} finished quests from flat dict.")
            return finished_quests
    elif isinstance(quests, list):
        quest_list = quests
    elif isinstance(quests, set):
        return {normalize_quest_name(str(q)) for q in quests}
    else:
        return set()

    # 3. List of items (dicts or strings)
    for quest in quest_list:
        if isinstance(quest, dict):
            state = quest.get("state") or quest.get("status")
            if state and str(state).strip().upper() == QuestStates.FINISHED:
                name = quest.get("name")
                if name:
                    finished_quests.add(normalize_quest_name(str(name)))
        elif isinstance(quest, str):
            finished_quests.add(normalize_quest_name(quest))

    logger.info(f"Extracted {len(finished_quests)} finished quests from request.")
    return finished_quests