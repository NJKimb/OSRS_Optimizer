import math
from typing import NamedTuple

from app.core.skills import Skill

# Default average XP rates (XP per hour) for mid-game training methods
DEFAULT_SKILLING_RATES: dict[Skill, int] = {
    Skill.ATTACK: 65_000,  # Sand crabs / Nightmare Zone
    Skill.STRENGTH: 65_000,  # Sand crabs / Nightmare Zone
    Skill.DEFENCE: 65_000,  # Sand crabs / Nightmare Zone
    Skill.RANGED: 75_000,  # Chinchompas / Crabs
    Skill.PRAYER: 250_000,  # Chaos Altar / Gilded Altar
    Skill.MAGIC: 80_000,  # High Alchemy / Bursting
    Skill.RUNECRAFT: 35_000,  # Guardians of the Rift / Bloods
    Skill.CONSTRUCTION: 180_000,  # Oak larders / Mythical capes
    Skill.HITPOINTS: 50_000,  # Passive combat
    Skill.AGILITY: 45_000,  # Rooftop courses (Seers / Pollnivneach)
    Skill.HERBLORE: 150_000,  # Potion making
    Skill.THIEVING: 90_000,  # Ardy Knights / Blackjacking
    Skill.CRAFTING: 100_000,  # Cutting gems / Glassblowing
    Skill.FLETCHING: 120_000,  # Broad arrows / Longbows
    Skill.SLAYER: 25_000,  # Task progression
    Skill.HUNTER: 70_000,  # Chinchompas / Birdhouses
    Skill.MINING: 40_000,  # Motherlode Mine / Iron
    Skill.SMITHING: 65_000,  # Giants' Foundry / Blast Furnace
    Skill.FISHING: 45_000,  # Barbarian fishing / Fly fishing
    Skill.COOKING: 150_000,  # Wines / Sharks
    Skill.FIREMAKING: 180_000,  # Wintertodt
    Skill.WOODCUTTING: 60_000,  # Teaks / Willows
    Skill.FARMING: 50_000,  # Tree runs (effective time)
    Skill.SAILING: 40_000,  # Ocean navigation & salvage
}


def get_skill_rate(skill: Skill, custom_rates: dict[Skill, int] | None = None) -> int:
    """
    Returns the XP/hr rate for a skill.
    Prioritizes user's custom rate if provided, otherwise uses default mid-game rate.
    """
    if custom_rates and skill in custom_rates and custom_rates[skill] > 0:
        return custom_rates[skill]
    return DEFAULT_SKILLING_RATES.get(skill, 40_000)


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
