from fastapi import APIRouter, HTTPException, Query
from app.models.quest import Quest
from app.services.dataloader import QUEST_DB
from app.services.quest_sync import sync_osrs_quests

router = APIRouter(prefix="/api/quests", tags=["Quests"])

@router.get("", response_model=list[Quest])
def list_quests(
    search: str | None = Query(default=None, description="Filter by quest name or ID substring"),
    difficulty: str | None = Query(default=None, description="Filter by difficulty (e.g. Novice, Master)")
):
    """Returns all available quests with optional filtering."""
    results = list(QUEST_DB.values())
    
    if search:
        s = search.lower()
        results = [q for q in results if s in q.name.lower() or s in q.id.lower()]
        
    if difficulty:
        d = difficulty.lower()
        results = [q for q in results if q.difficulty.lower() == d]
        
    return results

@router.get("/{quest_id}", response_model=Quest)
def get_quest(quest_id: str):
    """Retrieves a single quest by ID."""
    if quest_id not in QUEST_DB:
        raise HTTPException(status_code=404, detail=f"Quest '{quest_id}' not found.")
    return QUEST_DB[quest_id]

