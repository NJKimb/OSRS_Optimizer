from app.core.skills import AccountType
from app.models.player import SkillDetail
from app.models.player import PlayerProfile
import httpx2
from app.core.skills import Skill

username = "JJoner1"
accountType = "main"

HISCORES_URLS = {
        "main": f"https://secure.runescape.com/m=hiscore_oldschool/index_lite.json?player={username}",
        "ironman": f"https://secure.runescape.com/m=hiscore_oldschool_ironman/index_lite.json?player={username}",
        "hardcore_ironman": f"https://services.runescape.com/m=hiscore_oldschool_hardcore_ironman/index_lite.json?player={username}",
        "ultimate_ironman": f"https://services.runescape.com/m=hiscore_oldschool_ultimate/index_lite.json?player={username}",
}

response = httpx2.get(HISCORES_URLS.get(AccountType(accountType)))
response.raise_for_status()
data = response.json()

skills_data = {}

for item in data.get("skills", []):
    raw_name = item.get("name", "").lower()
    try:
        skill_enum = Skill(raw_name)
    except ValueError:
        continue

    level = item.get("level", -1)
    xp = item.get("xp", -1)
    rank = item.get("rank", -1)

    if level == -1 or xp == -1:
        # Hitpoints starts at level 10, other skills start at 1
        level = 10 if skill_enum == Skill.HITPOINTS else 1
        xp = 1154 if skill_enum == Skill.HITPOINTS else 0

    skills_data[skill_enum] = SkillDetail(level = level, xp = xp, rank = rank)

player = PlayerProfile(username=username, account_type= accountType, skills = skills_data)

print(player.username)
print(player.account_type)
print(player.skills)