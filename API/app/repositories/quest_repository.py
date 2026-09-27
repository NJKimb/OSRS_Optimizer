import json
from pathlib import Path
from app.models.quest import Quest

DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "quests.json"


class QuestRepository:
    def __init__(self, data_path: Path = DEFAULT_DATA_PATH):
        self.data_path = data_path
        self._quests: dict[str, Quest] = {}
        self._by_normalized_name: dict[str, Quest] = {}
        self.load()

    def load(self) -> None:
        """Loads and indexes quests from JSON into memory."""
        with open(self.data_path, "r", encoding="utf-8") as quest_file:
            quest_records = json.load(quest_file)

        self._quests = {
            quest_data["id"]: Quest(**quest_data) for quest_data in quest_records
        }
        self._by_normalized_name.clear()
        for quest in self._quests.values():
            clean_name = quest.name.strip().lower()
            self._by_normalized_name[clean_name] = quest
            self._by_normalized_name[clean_name.replace(" ", "_")] = quest

    def get(self, name_or_id: str) -> Quest | None:
        """O(1) lookup supporting exact name, lowercase, or slug format."""
        normalized = name_or_id.strip().lower()
        return self._by_normalized_name.get(normalized) or self._by_normalized_name.get(
            normalized.replace(" ", "_")
        )

    def search(
        self, query: str | None = None, difficulty: str | None = None
    ) -> list[Quest]:
        """
        Filters quests by name substring and/or difficulty.
        Returns all quests if no filters are provided.
        """
        results = list(self._quests.values())
        if query:
            normalized_query = query.strip().lower()
            results = [
                quest for quest in results if normalized_query in quest.name.lower()
            ]
        if difficulty:
            normalized_difficulty = difficulty.strip().lower()
            results = [
                quest
                for quest in results
                if quest.difficulty.lower() == normalized_difficulty
            ]
        return results

    def all(self) -> list[Quest]:
        """Returns all loaded quests."""
        return list(self._quests.values())

    def count(self) -> int:
        """Returns total count of loaded quests."""
        return len(self._quests)


_quest_repo: QuestRepository | None = None


def get_quest_repository() -> QuestRepository:
    """Provides a singleton QuestRepository instance for FastAPI dependency injection."""
    global _quest_repo
    if _quest_repo is None:
        _quest_repo = QuestRepository()
    return _quest_repo
