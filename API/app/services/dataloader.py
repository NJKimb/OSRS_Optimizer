from pathlib import Path
from app.models.quest import Quest
import json

def load_quests() -> dict[str, Quest]:
    file_path = Path(__file__).parent.parent / "data" / "quests.json"
    with open(file_path, 'r', encoding='utf-8') as file:
        data_dict = json.load(file)
        
    return {item["id"]: Quest(**item) for item in data_dict}
    
QUEST_DB: dict[str, Quest] = load_quests()

def reload_quests() -> dict[str, Quest]:
    """Reloads QUEST_DB in-place from quests.json so imported references stay updated."""
    fresh_quests = load_quests()
    QUEST_DB.clear()
    QUEST_DB.update(fresh_quests)
    return QUEST_DB
