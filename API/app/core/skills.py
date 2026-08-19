from enum import StrEnum
from bisect import bisect_right
import math

MAX_LEVEL = 126

class Skill(StrEnum):
    OVERALL = "overall"
    ATTACK = "attack"
    DEFENCE = "defence"
    STRENGTH = "strength"
    HITPOINTS = "hitpoints"
    RANGED = "ranged"
    PRAYER = "prayer"
    MAGIC = "magic"
    COOKING = "cooking"
    WOODCUTTING = "woodcutting"
    FLETCHING = "fletching"
    FISHING = "fishing"
    FIREMAKING = "firemaking"
    CRAFTING = "crafting"
    SMITHING = "smithing"
    MINING = "mining"
    HERBLORE = "herblore"
    AGILITY = "agility"
    THIEVING = "thieving"
    SLAYER = "slayer"
    FARMING = "farming"
    RUNECRAFT = "runecraft"
    HUNTER = "hunter"
    CONSTRUCTION = "construction"
    SAILING = "sailing"

class AccountType(StrEnum):
    MAIN = "main"
    IRONMAN = "ironman"
    HARDCORE_IRONMAN = "hardcore_ironman"
    ULTIMATE_IRONMAN = "ultimate_ironman"

def calculate_xp_for_level(level: int) -> int:
    """Calculates total XP needed for a specific level using the OSRS formula."""
    if level <= 1:
        return 0
    
    total = 0.0
    for i in range(1, level):
        # floor(i + 300 * 2^(i/7))
        total += math.floor(i + 300.0 * (2.0 ** (i / 7.0)))
    
    return math.floor(total / 4.0)

XP_TABLE = [calculate_xp_for_level(lvl) for lvl in range(MAX_LEVEL + 1)]

def xp_to_level(xp: int) -> int:
    """Returns the level (1-126) for a given amount of XP."""
    if xp < 0:
        return 1
    # bisect_right finds the highest level where XP_TABLE[level] <= xp
    level = bisect_right(XP_TABLE, xp) - 1
    return max(1, min(level, MAX_LEVEL))