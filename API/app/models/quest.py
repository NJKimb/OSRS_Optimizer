from pydantic import BaseModel, Field
from app.models.skills import Skill


class QuestRequirements(BaseModel):
    quests: list[str] = Field(default_factory=list)
    skills: dict[Skill, int] = Field(default_factory=dict)
    # Skills whose requirement the wiki marks as boostable
    boostable_skills: list[Skill] = Field(default_factory=list)
    quest_points: int = 0


def normalize_name(name: str) -> str:
    """
    The one definition of "same quest": ignores case, stray whitespace and
    underscores, so the slug "song_of_the_elves" matches "Song of the Elves".
    """
    return " ".join(name.replace("_", " ").split()).casefold()


class Quest(BaseModel):
    id: str | None = None
    name: str
    quest_points: int
    difficulty: str
    length: str
    requirements: QuestRequirements = Field(default_factory=QuestRequirements)
    xp_rewards: dict[Skill, int] = Field(default_factory=dict)

    @property
    def normalized_name(self) -> str:
        return normalize_name(self.name)
