from enum import StrEnum
from pydantic import BaseModel, Field
from app.core.skills import Skill

class AccountType(StrEnum):
    MAIN = "main"
    IRONMAN = "ironman"
    HARDCORE_IRONMAN = "hardcore_ironman"
    ULTIMATE_IRONMAN = "ultimate_ironman"

class SkillDetail(BaseModel):
    level: int
    xp: int
    rank: int = -1

class PlayerProfile(BaseModel):
    username: str
    account_type: AccountType
    # Maps each Skill enum to its level/xp/rank
    skills: dict[Skill, SkillDetail]
    completed_quests: set[str] = Field(default_factory=set)