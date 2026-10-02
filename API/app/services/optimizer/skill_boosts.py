import math
from typing import NamedTuple

from app.models.skills import Skill


class SkillBoost(NamedTuple):
    flat: int
    percent: float
    source: str

    def boosted_level(self, base_level: int) -> int:
        return base_level + self.flat + math.floor(base_level * self.percent)


# Cheap, widely available temporary boosts. Skills without a realistic boost are omitted.
DEFAULT_SKILL_BOOSTS: dict[Skill, SkillBoost] = {
    Skill.ATTACK: SkillBoost(5, 0.15, "Super attack"),
    Skill.STRENGTH: SkillBoost(5, 0.15, "Super strength"),
    Skill.DEFENCE: SkillBoost(5, 0.15, "Super defence"),
    Skill.RANGED: SkillBoost(4, 0.10, "Ranging potion"),
    Skill.MAGIC: SkillBoost(4, 0.0, "Magic potion"),
    Skill.AGILITY: SkillBoost(5, 0.0, "Summer pie"),
    Skill.CRAFTING: SkillBoost(4, 0.0, "Mushroom pie"),
    Skill.FLETCHING: SkillBoost(4, 0.0, "Dragonfruit pie"),
    Skill.HERBLORE: SkillBoost(4, 0.0, "Botanical pie"),
    Skill.SLAYER: SkillBoost(5, 0.0, "Wild pie"),
    Skill.FISHING: SkillBoost(3, 0.0, "Fish pie"),
    Skill.FARMING: SkillBoost(3, 0.0, "Garden pie"),
    Skill.HUNTER: SkillBoost(3, 0.0, "Hunter potion"),
    Skill.COOKING: SkillBoost(1, 0.05, "Chef's delight"),
    Skill.MINING: SkillBoost(1, 0.0, "Dwarven stout"),
    Skill.SMITHING: SkillBoost(1, 0.0, "Dwarven stout"),
}


def get_skill_boost(skill: Skill) -> SkillBoost | None:
    return DEFAULT_SKILL_BOOSTS.get(skill)


def get_min_base_level(required_level: int, boost: SkillBoost | None) -> int:
    """Lowest base level that can be boosted to reach the required level."""
    if boost is None:
        return required_level
    base_level = required_level
    while base_level > 1 and boost.boosted_level(base_level - 1) >= required_level:
        base_level -= 1
    return base_level
