from pydantic import BaseModel, Field
from app.core.skills import Skill


class QuestRequirements(BaseModel):
    quests: list[str] = Field(default_factory=list)
    skills: dict[Skill, int] = Field(default_factory=dict)
    # Skills whose requirement the wiki marks as boostable
    boostable_skills: list[Skill] = Field(default_factory=list)
    quest_points: int = 0


class Quest(BaseModel):
    id: str | None = None
    name: str
    quest_points: int
    difficulty: str
    length: str
    requirements: QuestRequirements = Field(default_factory=QuestRequirements)
    xp_rewards: dict[Skill, int] = Field(default_factory=dict)
