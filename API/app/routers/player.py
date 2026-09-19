from fastapi import APIRouter, Query
from app.services.hiscores import fetch_player_profile
from app.models.player import AccountType, PlayerProfile

router = APIRouter(prefix="/api/player", tags=["Player"])

@router.get("/{username}", response_model=PlayerProfile)
async def get_player_profile(username: str, account_type: AccountType = Query(default=AccountType.MAIN)):
    return await fetch_player_profile(username, account_type)