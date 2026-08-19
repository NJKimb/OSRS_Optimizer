from pydantic import BaseModel
from app.core.skills import Skill, AccountType


class SkillDetail(BaseModel):
    level: int
    xp: int
    rank: int = -1

class PlayerProfile(BaseModel):
    username: str
    account_type: AccountType = AccountType.MAIN
    # Maps each Skill enum to its level/xp/rank
    skills: dict[Skill, SkillDetail]