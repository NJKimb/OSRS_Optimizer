from fastapi import APIRouter, Depends, HTTPException, Query
from app.models.quest import Quest
from app.repositories.quest_repository import QuestRepository, get_quest_repository

router = APIRouter(prefix="/api/quests", tags=["Quests"])


@router.get("", response_model=list[Quest])
def list_quests(
    search: str | None = Query(default=None, description="Filter by quest name substring"),
    difficulty: str | None = Query(default=None, description="Filter by difficulty (e.g. Novice, Master)"),
    repo: QuestRepository = Depends(get_quest_repository),
):
    """Returns all available quests with optional filtering."""
    return repo.search(query=search, difficulty=difficulty)


@router.get("/{quest_name}", response_model=Quest)
def get_quest(
    quest_name: str,
    repo: QuestRepository = Depends(get_quest_repository),
):
    """Retrieves a single quest by name or slug."""
    quest = repo.get(quest_name)
    if not quest:
        raise HTTPException(status_code=404, detail=f"Quest '{quest_name}' not found.")
    return quest
