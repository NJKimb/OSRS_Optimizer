from fastapi import APIRouter, Path, Query
from app.services.hiscores import fetch_player_profile
from app.models.player import USERNAME_PATTERN, AccountType, PlayerProfile

router = APIRouter(prefix="/api/player", tags=["Player"])


@router.get("/{username}", response_model=PlayerProfile)
async def get_player_profile(
    username: str = Path(pattern=USERNAME_PATTERN),
    account_type: AccountType = Query(default=AccountType.MAIN),
):
    return await fetch_player_profile(username, account_type)
