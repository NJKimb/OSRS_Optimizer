from app.models.quest import Quest
from app.repositories.quest_repository import get_quest_repository

QUEST_DB: dict[str, Quest] = get_quest_repository()._quests


def reload_quests() -> dict[str, Quest]:
    """Reloads QUEST_DB in-place from quests.json so imported references stay updated."""
    repo = get_quest_repository()
    repo.load()
    QUEST_DB.clear()
    QUEST_DB.update(repo._quests)
    return QUEST_DB
