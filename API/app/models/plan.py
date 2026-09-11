from app.core.skills import AccountType
from pydantic import BaseModel, Field
from app.core.skills import Skill
from app.models.player import PlayerProfile

# What the frontend sends:
class OptimizationRequest(BaseModel):
    username: str
    account_type: AccountType = AccountType.MAIN
    target_goal: str                                         # e.g. "song_of_the_elves"
    completed_quests: set[str] = Field(default_factory=set) # Optional completed quests
    custom_xp_rates: dict[Skill, int] = Field(default_factory=dict)

# Breakdown of each skill's deficit & hours:
class SkillDeficit(BaseModel):
    skill: Skill
    current_level: int
    target_level: int
    current_xp: int
    target_xp: int
    xp_needed: int
    quest_xp_rewards: int = 0               # Free XP from scheduled quests
    remaining_xp_to_grind: int = 0          # Net XP player must train manually
    estimated_hours: float = 0.0

# Actionable chronological step in the roadmap:
class RoadmapStep(BaseModel):
    step_number: int
    step_type: str                          # "quest" | "skill_training"
    title: str                              # e.g. "Complete The Knight's Sword"
    description: str                        # e.g. "Grants 12,725 Smithing XP"
    estimated_hours: float = 0.0

# What the API returns:
class OptimizationResponse(BaseModel):
    goal_name: str
    total_hours_remaining: float
    missing_quests: list[str]
    skill_deficits: list[SkillDeficit]
    roadmap: list[RoadmapStep]
