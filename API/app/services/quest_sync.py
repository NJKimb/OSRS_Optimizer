import json
import logging
import re
import html
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any

from app.core.skills import Skill
from app.models.quest import Quest, QuestRequirements
from app.services.dataloader import reload_quests

logger = logging.getLogger(__name__)

USER_AGENT = "OSRSAccountOptimizer/1.0 (https://github.com/NJKimb/OSRS_Optimizer)"
WIKI_API_ENDPOINT = "https://oldschool.runescape.wiki/api.php"

# Normalization mapping for skills (e.g., Runecrafting -> runecraft)
SKILL_NAME_MAP = {
    "runecrafting": "runecraft",
    "runecraft": "runecraft",
    "hitpoints": "hitpoints",
    "hp": "hitpoints",
}

def slugify(title: str) -> str:
    """
    Converts a quest title into a normalized snake_case identifier.
    Converts Roman numerals (I, II, III...) to Arabic digits (1, 2, 3...)
    to maintain consistent quest IDs.
    """
    s = title.strip()
    # Normalize Roman numerals at word boundaries
    s = re.sub(r'\bVIII\b', '8', s, flags=re.IGNORECASE)
    s = re.sub(r'\bVII\b', '7', s, flags=re.IGNORECASE)
    s = re.sub(r'\bVI\b', '6', s, flags=re.IGNORECASE)
    s = re.sub(r'\bIV\b', '4', s, flags=re.IGNORECASE)
    s = re.sub(r'\bV\b', '5', s, flags=re.IGNORECASE)
    s = re.sub(r'\bIII\b', '3', s, flags=re.IGNORECASE)
    s = re.sub(r'\bII\b', '2', s, flags=re.IGNORECASE)
    s = re.sub(r'\bI\b', '1', s, flags=re.IGNORECASE)
    # Remove apostrophes (e.g. Cook's -> Cooks)
    s = s.replace("'", "")
    # Replace any non-alphanumeric character with underscore
    s = re.sub(r'[^a-zA-Z0-9]+', '_', s)
    return s.strip('_').lower()


def fetch_wiki_page_content(page_title: str, prop: str = "wikitext") -> str:
    """Fetches wikitext or parsed HTML from the OSRS Wiki API."""
    params = {
        "action": "parse",
        "page": page_title,
        "prop": prop,
        "format": "json"
    }
    url = f"{WIKI_API_ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if "error" in data:
            raise RuntimeError(f"OSRS Wiki API error for '{page_title}': {data['error'].get('info')}")
        return data["parse"][prop]["*"]


def extract_lua_table(content: str, key: str) -> str:
    """Extracts the body of a nested Lua table like `['key'] = { ... }` with balanced braces."""
    pattern = rf"\['{key}'\]\s*=\s*\{{"
    m = re.search(pattern, content)
    if not m:
        return ""
    start = m.end()
    depth = 1
    i = start
    while i < len(content) and depth > 0:
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
        i += 1
    return content[start:i - 1]


def parse_quest_requirements(wikitext: str) -> dict[str, dict[str, Any]]:
    """
    Parses `Module:Questreq/data` wikitext into a structured dictionary of quest requirements.
    Key is the quest title, value is dict with:
      - 'quests': list of prerequisite quest title strings
      - 'skills': dict of {Skill: int}
      - 'quest_points': int
    """
    start_idx = wikitext.find("local questReqs = {")
    end_idx = wikitext.rfind("return questReqs")
    if start_idx == -1 or end_idx == -1:
        raise ValueError("Could not find questReqs table in Module:Questreq/data")

    body = wikitext[start_idx:end_idx]
    matches = list(re.finditer(r"\[\s*'((?:\\'|[^'])+)'\s*\]\s*=\s*\{", body))
    quest_matches = [m for m in matches if m.group(1) not in ("quests", "skills")]

    valid_skills = {s.value for s in Skill}
    results = {}

    for i, m in enumerate(quest_matches):
        raw_qname = m.group(1)
        qname = raw_qname.replace(r"\'", "'").strip()
        pos = m.start()
        next_pos = quest_matches[i + 1].start() if i + 1 < len(quest_matches) else len(body)
        qblock = body[pos:next_pos]

        # Prerequisite quests
        subquests = []
        quests_body = extract_lua_table(qblock, "quests")
        if quests_body:
            raw_items = re.findall(r"'((?:\\'|[^'])*)'", quests_body)
            subquests = [it.replace(r"\'", "'").strip() for it in raw_items if it.strip()]

        # Skill requirements & QP requirements
        skills: dict[str, int] = {}
        qp_req = 0
        skills_body = extract_lua_table(qblock, "skills")
        if skills_body:
            for entry_match in re.finditer(r"\{([^}]+)\}", skills_body):
                parts = [p.strip().strip("'").replace(r"\'", "'") for p in entry_match.group(1).split(',')]
                if len(parts) >= 2:
                    sname = parts[0].strip()
                    try:
                        slevel = int(parts[1].strip())
                        sname_lower = sname.lower()
                        if sname_lower in ("quest point", "quest points"):
                            qp_req = slevel
                        else:
                            canonical_skill = SKILL_NAME_MAP.get(sname_lower, sname_lower)
                            if canonical_skill in valid_skills:
                                skills[canonical_skill] = slevel
                    except ValueError:
                        continue

        results[qname] = {
            "quests": subquests,
            "skills": skills,
            "quest_points": qp_req,
        }

    return results


def parse_quest_xp_rewards(wikitext: str) -> dict[str, dict[str, int]]:
    """
    Parses `Quest experience rewards` wikitext to extract all set skill experience rewards.
    Returns {quest_name: {skill: xp_amount}}.
    """
    valid_skills = {s.value for s in Skill}
    matches = re.findall(r'data-rowid="([^"]+)"[\s\S]*?\{\{\+=\|([a-z]+)\|([0-9.,]+)', wikitext)
    xp_by_quest: dict[str, dict[str, int]] = {}

    for qname, raw_skill, raw_amt in matches:
        clean_amt = int(float(raw_amt.replace(',', '')))
        qname_clean = html.unescape(qname).strip()
        skill = SKILL_NAME_MAP.get(raw_skill.lower(), raw_skill.lower())
        if skill not in valid_skills:
            continue

        if qname_clean not in xp_by_quest:
            xp_by_quest[qname_clean] = {}
        xp_by_quest[qname_clean][skill] = clean_amt

    return xp_by_quest


def parse_quests_list(html_text: str) -> list[dict[str, Any]]:
    """
    Parses `Quests/List` parsed HTML to extract quest base metadata:
    id, name, difficulty, quest_points.
    Excludes miniquests.
    """
    miniquest_idx = html_text.find('id="Miniquests"')
    main_html = html_text[:miniquest_idx] if miniquest_idx != -1 else html_text

    quests = []
    seen_ids = set()

    for row_m in re.finditer(r'<tr[^>]*data-rowid="([^"]+)"[^>]*>([\s\S]*?)</tr>', main_html):
        row_body = row_m.group(2)
        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<td[^>]*>([\s\S]*?)</td>', row_body)]
        if len(cells) < 5:
            continue

        qname = html.unescape(cells[1]).strip()
        difficulty = cells[2].strip()
        try:
            qp_match = re.search(r'\d+', cells[4])
            quest_points = int(qp_match.group(0)) if qp_match else 0
        except Exception:
            quest_points = 0

        qid = slugify(qname)
        if qid in seen_ids:
            continue
        seen_ids.add(qid)

        quests.append({
            "id": qid,
            "name": qname,
            "difficulty": difficulty,
            "quest_points": quest_points,
        })

    return quests


def sync_osrs_quests(
    save: bool = True,
    target_file: Path | None = None,
    reload_db: bool = True
) -> list[Quest]:
    """
    Performs full automated synchronization of all OSRS quests from the Wiki API:
    1. Fetches Quests/List (base quest metadata & QP)
    2. Fetches Quest experience rewards (skill XP rewards)
    3. Fetches Module:Questreq/data (prerequisites, skill requirements, QP requirements)
    4. Merges and validates via Pydantic Quest models
    5. Saves to quests.json if save=True
    6. Reloads QUEST_DB in dataloader if reload_db=True
    """
    logger.info("Fetching quest metadata from OSRS Wiki...")
    list_html = fetch_wiki_page_content("Quests/List", prop="text")
    base_quests = parse_quests_list(list_html)

    logger.info("Fetching quest experience rewards...")
    xp_wikitext = fetch_wiki_page_content("Quest_experience_rewards", prop="wikitext")
    xp_rewards_db = parse_quest_xp_rewards(xp_wikitext)

    logger.info("Fetching quest requirements from Module:Questreq/data...")
    req_wikitext = fetch_wiki_page_content("Module:Questreq/data", prop="wikitext")
    reqs_db = parse_quest_requirements(req_wikitext)

    # Index helper maps for fast slug lookup
    reqs_by_slug = {slugify(k): v for k, v in reqs_db.items()}
    xp_by_slug = {slugify(k): v for k, v in xp_rewards_db.items()}

    valid_quest_ids = {q["id"] for q in base_quests}

    validated_quests: list[Quest] = []

    for base in base_quests:
        qid = base["id"]
        qname = base["name"]

        # Requirements lookup
        req_entry = reqs_db.get(qname) or reqs_by_slug.get(qid) or {}
        raw_subquests = req_entry.get("quests", [])
        raw_skills = req_entry.get("skills", {})
        qp_req = req_entry.get("quest_points", 0)

        # Convert subquests to valid quest IDs
        subquest_ids = []
        for sq in raw_subquests:
            sq_slug = slugify(sq)
            # Only add prerequisite if it exists or keep slug
            subquest_ids.append(sq_slug)

        # Convert skill strings to Skill enum
        typed_skills: dict[Skill, int] = {
            Skill(s): lvl for s, lvl in raw_skills.items() if s in Skill
        }

        # XP rewards lookup
        xp_entry = xp_rewards_db.get(qname) or xp_by_slug.get(qid) or {}
        typed_xp_rewards: dict[Skill, int] = {
            Skill(s): xp for s, xp in xp_entry.items() if s in Skill
        }

        requirements = QuestRequirements(
            quests=subquest_ids,
            skills=typed_skills,
            quest_points=qp_req,
        )

        quest = Quest(
            id=qid,
            name=qname,
            quest_points=base["quest_points"],
            difficulty=base["difficulty"],
            requirements=requirements,
            xp_rewards=typed_xp_rewards,
        )
        validated_quests.append(quest)

    if save:
        out_path = target_file or (Path(__file__).parent.parent / "data" / "quests.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Convert models to JSON-serializable list
        quest_data = [q.model_dump(mode="json") for q in validated_quests]
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(quest_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved {len(validated_quests)} quests to {out_path}")

    if reload_db:
        reload_quests()

    return validated_quests
