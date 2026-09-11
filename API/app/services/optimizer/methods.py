from app.core.skills import Skill

# Default average XP rates (XP per hour) for mid-game training methods
DEFAULT_SKILLING_RATES: dict[Skill, int] = {
    Skill.ATTACK: 65_000,        # Sand crabs / Nightmare Zone
    Skill.STRENGTH: 65_000,      # Sand crabs / Nightmare Zone
    Skill.DEFENCE: 65_000,       # Sand crabs / Nightmare Zone
    Skill.RANGED: 75_000,        # Chinchompas / Crabs
    Skill.PRAYER: 250_000,       # Chaos Altar / Gilded Altar
    Skill.MAGIC: 80_000,         # High Alchemy / Bursting
    Skill.RUNECRAFT: 35_000,     # Guardians of the Rift / Bloods
    Skill.CONSTRUCTION: 180_000, # Oak larders / Mythical capes
    Skill.HITPOINTS: 50_000,     # Passive combat
    Skill.AGILITY: 45_000,       # Rooftop courses (Seers / Pollnivneach)
    Skill.HERBLORE: 150_000,     # Potion making
    Skill.THIEVING: 90_000,      # Ardy Knights / Blackjacking
    Skill.CRAFTING: 100_000,     # Cutting gems / Glassblowing
    Skill.FLETCHING: 120_000,    # Broad arrows / Longbows
    Skill.SLAYER: 25_000,        # Task progression
    Skill.HUNTER: 70_000,        # Chinchompas / Birdhouses
    Skill.MINING: 40_000,        # Motherlode Mine / Iron
    Skill.SMITHING: 65_000,      # Giants' Foundry / Blast Furnace
    Skill.FISHING: 45_000,       # Barbarian fishing / Fly fishing
    Skill.COOKING: 150_000,      # Wines / Sharks
    Skill.FIREMAKING: 180_000,   # Wintertodt
    Skill.WOODCUTTING: 60_000,   # Teaks / Willows
    Skill.FARMING: 50_000,       # Tree runs (effective time)
    Skill.SAILING: 40_000,       # Ocean navigation & salvage
}


def get_skill_rate(skill: Skill, custom_rates: dict[Skill, int] | None = None) -> int:
    """
    Returns the XP/hr rate for a skill.
    Prioritizes user's custom rate if provided, otherwise uses default mid-game rate.
    """
    if custom_rates and skill in custom_rates and custom_rates[skill] > 0:
        return custom_rates[skill]
    return DEFAULT_SKILLING_RATES.get(skill, 40_000)