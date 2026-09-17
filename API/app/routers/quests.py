from fastapi import APIRouter, HTTPException, Query
from app.models.quest import Quest
from app.services.dataloader import QUEST_DB

router = APIRouter(prefix="/api/quests", tags=["Quests"])

@router.get("", response_model=list[Quest])
def list_quests(
    search: str | None = Query(default=None, description="Filter by quest name substring"),
    difficulty: str | None = Query(default=None, description="Filter by difficulty (e.g. Novice, Master)")
):
    """Returns all available quests with optional filtering."""
    results = list(QUEST_DB.values())
    
    if search:
        s = search.lower()
        results = [q for q in results if s in q.name.lower()]
        
    if difficulty:
        d = difficulty.lower()
        results = [q for q in results if q.difficulty.lower() == d]
        
    return results

@router.get("/{quest_name}", response_model=Quest)
def get_quest(quest_name: str):
    """Retrieves a single quest by name."""
    if quest_name in QUEST_DB:
        return QUEST_DB[quest_name]
    for name, quest in QUEST_DB.items():
        if name.lower() == quest_name.lower():
            return quest
    raise HTTPException(status_code=404, detail=f"Quest '{quest_name}' not found.")

