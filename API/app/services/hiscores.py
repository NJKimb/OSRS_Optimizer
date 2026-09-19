import cachetools
from app.models.player import AccountType, SkillDetail, PlayerProfile
import httpx2
import time
from fastapi import HTTPException
from app.core.skills import Skill

HISCORES_BASE_URLS = {
    AccountType.MAIN: "https://secure.runescape.com/m=hiscore_oldschool/index_lite.json",
    AccountType.IRONMAN: "https://secure.runescape.com/m=hiscore_oldschool_ironman/index_lite.json",
    AccountType.HARDCORE_IRONMAN: "https://services.runescape.com/m=hiscore_oldschool_hardcore_ironman/index_lite.json",
    AccountType.ULTIMATE_IRONMAN: "https://services.runescape.com/m=hiscore_oldschool_ultimate/index_lite.json",
}

_PROFILE_CACHE = cachetools.TTLCache(maxsize=2000, ttl=300)

async def fetch_player_profile(username: str, account_type: AccountType) -> PlayerProfile:

    cache_key = f"{username.lower()}_{account_type.value}"
    current_time = time.time()

    if cache_key in _PROFILE_CACHE:
        return _PROFILE_CACHE[cache_key].model_copy(deep=True)

    base_url = HISCORES_BASE_URLS.get(account_type, HISCORES_BASE_URLS[AccountType.MAIN])
    params = {"player": username}
    headers = {"User-Agent": "OSRS_Account_Optimizer"}

    async with httpx2.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(base_url, params=params, headers=headers)
        except httpx2.RequestError:
            raise HTTPException(status_code=503, detail="Unable to connect to Jagex Hiscores.")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Player '{username}' not found on hiscores.")
        
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Error fetching data from Jagex Hiscores.")
        data = response.json()

    skills_data = {}

    for item in data.get("skills", []):
        raw_name = item.get("name", "").lower()
        try:
            skill_enum = Skill(raw_name)
        except ValueError:
            continue

        level = item.get("level", -1)
        xp = item.get("xp", -1)
        rank = item.get("rank", -1)

        if level == -1 or xp == -1:
            # Hitpoints starts at level 10, other skills start at 1
            level = 10 if skill_enum == Skill.HITPOINTS else 1
            xp = 1154 if skill_enum == Skill.HITPOINTS else 0

        skills_data[skill_enum] = SkillDetail(level = level, xp = xp, rank = rank)

    profile = PlayerProfile(username=username, account_type=account_type, skills = skills_data)

    _PROFILE_CACHE[cache_key] = (current_time, profile)

    return profile