from pathlib import Path
from app.models.quest import Quest
import json

def load_quests() -> dict[str, Quest]:
    file_path = Path(__file__).parent.parent / "data" / "quests.json"
    with open(file_path, 'r') as file:
        data_dict = json.load(file)
        
    return {item["id"]: Quest(**item) for item in data_dict}
    
QUEST_DB: dict[str, Quest] = load_quests()