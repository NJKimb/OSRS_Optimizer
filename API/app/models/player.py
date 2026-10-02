from enum import StrEnum
from typing import Annotated
from pydantic import BaseModel, Field, StringConstraints
from app.models.skills import Skill

# OSRS display names: 1-12 letters, digits, spaces, hyphens or underscores
USERNAME_PATTERN = r"^[A-Za-z0-9 _-]{1,12}$"
Username = Annotated[str, StringConstraints(pattern=USERNAME_PATTERN)]


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
    quests_status: set[str] = Field(default_factory=set)
