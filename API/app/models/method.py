from pydantic import BaseModel
from app.models.skills import Skill


class TrainingTier(BaseModel):
    start_level: int
    end_level: int
    xp_rate: int
    method_name: str


class SkillTrainingMethods(BaseModel):
    skill: Skill
    main_tiers: list[TrainingTier]
    ironman_tiers: list[TrainingTier]
