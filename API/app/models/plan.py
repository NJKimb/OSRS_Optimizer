from enum import StrEnum
from typing import Any
from app.models.player import AccountType, Username
from pydantic import AliasChoices, BaseModel, Field, PositiveInt
from app.core.skills import Skill


# What the frontend sends:
class OptimizationRequest(BaseModel):
    username: Username
    account_type: AccountType = AccountType.MAIN
    target_goal: str  # e.g. "song_of_the_elves"
    # Character Exporter JSON as a dict, list, or string; also accepted as "completed_quests"
    quests_status: dict[str, Any] | list[Any] | str | None = Field(
        default=None,
        validation_alias=AliasChoices("quests_status", "completed_quests"),
    )
    custom_xp_rates: dict[Skill, PositiveInt] = Field(default_factory=dict)
    allow_boosts: bool = True  # Use cheap temporary boosts for boostable requirements


# Breakdown of each skill's deficit & hours:
class SkillDeficit(BaseModel):
    skill: Skill
    current_level: int
    target_level: int
    current_xp: int
    target_xp: int
    xp_needed: int
    quest_xp_rewards: int = 0  # Free XP from scheduled quests
    remaining_xp_to_grind: int = 0  # Net XP player must train manually
    estimated_hours: float = 0.0
    boost: str | None = None  # e.g. "Boost to 70 with Summer pie"


class StepType(StrEnum):
    QUEST = "quest"
    SKILL_TRAINING = "skill_training"
    COMPLETE = "complete"


# Actionable chronological step in the roadmap:
class RoadmapStep(BaseModel):
    step_number: int
    step_type: StepType
    title: str  # e.g. "Complete The Knight's Sword"
    description: str  # e.g. "Grants 12,725 Smithing XP"
    estimated_hours: float = 0.0


# What the API returns:
class OptimizationResponse(BaseModel):
    goal_name: str
    total_hours_remaining: float
    missing_quests: list[str]
    skill_deficits: list[SkillDeficit]
    roadmap: list[RoadmapStep]
