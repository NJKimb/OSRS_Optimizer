import html
import json
import logging
import re
import urllib.parse
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
import httpx2
from slpp import slpp

from app.core.skills import Skill
from app.models.quest import Quest, QuestRequirements
from app.services.dataloader import reload_quests, QUEST_DB

logger = logging.getLogger(__name__)

USER_AGENT = "OSRSAccountOptimizer/1.0 (https://github.com/NJKimb/OSRS_Optimizer) Discord: JJoner"
WIKI_API_ENDPOINT = "https://oldschool.runescape.wiki/api.php"

SKILL_NAME_MAP = {
    "runecrafting": "runecraft",
    "runecraft": "runecraft",
    "hitpoints": "hitpoints",
    "hp": "hitpoints",
}

def fetch_wiki_page_content(page_title: str = "", prop: str | None = None) -> Any:
    """
    Fetches wikitext or parsed HTML from the OSRS Wiki API if prop is specified.
    If prop is None, queries the Wiki Bucket API for all quest entries.
    """
    if prop is not None:
        params = {
            "action": "parse",
            "page": page_title,
            "prop": prop,
            "format": "json"
        }
        response = httpx2.get(WIKI_API_ENDPOINT, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "error" in data:
                raise RuntimeError(f"OSRS Wiki API error for '{page_title}': {data['error'].get('info')}")
            return data["parse"][prop]["*"]
        else:
            raise RuntimeError(f"OSRS Wiki API request failed with status {response.status_code}")
    else:
        query_string = "bucket('quest').select('page_name', 'official_difficulty', 'official_length', 'requirements').run()"
        params = {
            "action": "bucket",
            "format": "json",
            "query": query_string
        }
        response = httpx2.get(WIKI_API_ENDPOINT, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(f"OSRS Wiki Bucket API request failed with status {response.status_code}")


def parse_bucket_requirements(req_text: str) -> dict[str, Any]:
    """
    Parses the `requirements` field from the Bucket quest table:
      - Skill requirements from <span class="scp" data-skill="..." data-level="...">
      - Quest points requirements from data-skill="Quest points" or text
      - Prerequisite quests from wiki bullet links under quest completion sections
    """
    if not req_text or req_text.strip().lower() == "none":
        return {"skills": {}, "quests": [], "quest_points": 0}

    skills: dict[str, int] = {}
    qp_req = 0
    valid_skills = {s.value for s in Skill}

    # 1. Extract skills and Quest points from data-skill / data-level tags
    for match in re.finditer(r'data-skill="([^"]+)"\s+data-level="(\d+)"', req_text):
        raw_skill = match.group(1).strip()
        level = int(match.group(2))
        raw_skill_lower = raw_skill.lower()
        if raw_skill_lower in ("quest points", "quest point"):
            qp_req = max(qp_req, level)
        else:
            canonical = SKILL_NAME_MAP.get(raw_skill_lower, raw_skill_lower)
            if canonical in valid_skills:
                skills[canonical] = level

    if qp_req == 0:
        qp_match = re.search(r'(\d+)\s+\[\[Quest points\]\]', req_text, re.IGNORECASE)
        if qp_match:
            qp_req = int(qp_match.group(1))

    # 2. Extract prerequisite quests
    subquests: list[str] = []
    lines = req_text.splitlines()
    in_quest_section = False
    for line in lines:
        line_clean = line.strip()
        if "completion of the following quest" in line_clean.lower():
            in_quest_section = True
            continue

        m = re.match(r'^\*{1,6}\s*\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', line_clean)
        if m:
            q_candidate = m.group(1).strip()
            if not any(q_candidate.startswith(p) for p in ("File:", "Image:", "Category:", "Quest point")):
                if in_quest_section or line_clean.startswith("**"):
                    if q_candidate not in subquests:
                        subquests.append(q_candidate)
        elif in_quest_section and not line_clean.startswith("*"):
            in_quest_section = False

    return {"skills": skills, "quests": subquests, "quest_points": qp_req}


def parse_quest_xp_rewards(content: str) -> dict[str, dict[str, int]]:
    """
    Parses `Quest experience rewards` content to extract all skill experience rewards.
    Supports both parsed HTML (prop="text") and raw wikitext (prop="wikitext").
    Returns {quest_name: {skill: xp_amount}}.
    """
    valid_skills = {s.value for s in Skill}
    xp_by_quest: dict[str, dict[str, int]] = {}

    # Check if content is HTML
    if "<table" in content:
        soup = BeautifulSoup(content, "html.parser")
        skills = [s.value for s in Skill]

        for skill in skills:
            h = soup.find(lambda tag: tag.name in ["h3", "h2"] and tag.get_text(strip=True).lower().startswith(skill))
            if not h:
                continue
            table = h.find_next("table", class_="wikitable")
            if not table:
                continue
            for row in table.find_all("tr", attrs={"data-rowid": True}):
                qname = html.unescape(row["data-rowid"]).strip()
                cells = row.find_all("td")
                if len(cells) >= 3:
                    xp_text = cells[2].get_text(strip=True).replace(",", "")
                    m = re.search(r"(\d+(?:\.\d+)?)", xp_text)
                    if m:
                        xp_amt = int(float(m.group(1)))
                        if qname not in xp_by_quest:
                            xp_by_quest[qname] = {}
                        xp_by_quest[qname][skill] = xp_amt
    else:
        # Fallback for wikitext format
        matches = re.findall(r'data-rowid="([^"]+)"[\s\S]*?\{\{\+=\|([a-z]+)\|([0-9.,]+)', content)
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


def parse_quest_requirements(wikitext: str) -> dict[str, dict[str, Any]]:
    """
    Legacy parser for `Module:Questreq/data` using `slpp`.
    Maintained for backwards compatibility and unit testing.
    """
    start = wikitext.find("local questReqs = {")
    end = wikitext.rfind("return questReqs")
    if start == -1 or end == -1:
        raise ValueError("Could not find questReqs table in Module:Questreq/data")

    lua_code = wikitext[start + len("local questReqs = "):end].strip()
    decoded = slpp.decode(lua_code) or {}

    valid_skills = {s.value for s in Skill}
    results = {}

    for qname, data in decoded.items():
        if not isinstance(data, dict):
            continue

        subquests = [q.strip() for q in data.get("quests", []) if isinstance(q, str) and q.strip()]
        skills: dict[str, int] = {}
        qp_req = 0

        for item in data.get("skills", []):
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                sname = str(item[0]).strip()
                try:
                    slevel = int(item[1])
                    sname_lower = sname.lower()
                    if sname_lower in ("quest point", "quest points"):
                        qp_req = slevel
                    else:
                        canonical_skill = SKILL_NAME_MAP.get(sname_lower, sname_lower)
                        if canonical_skill in valid_skills:
                            skills[canonical_skill] = slevel
                except (ValueError, TypeError):
                    continue

        results[qname] = {
            "quests": subquests,
            "skills": skills,
            "quest_points": qp_req,
        }

    return results


def parse_quests_list(html_text: str) -> list[dict[str, Any]]:
    """
    Legacy parser for `Quests/List` HTML using BeautifulSoup.
    Maintained for backwards compatibility and unit testing.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    quests = []
    seen_ids = set()

    for row in soup.find_all("tr", attrs={"data-rowid": True}):
        if row.find_previous(id="Miniquests"):
            continue

        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 5:
            continue

        qname = cells[1]
        difficulty = cells[2]
        try:
            qp_match = re.search(r'\d+', cells[4])
            quest_points = int(qp_match.group(0)) if qp_match else 0
        except Exception:
            quest_points = 0

        if qname in seen_ids:
            continue
        seen_ids.add(qname)

        quests.append({
            "id": qname,
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
    Performs automated synchronization of all OSRS quests using:
    1. The Wiki Bucket API (JSON response from bucket('quest')) for quest metadata and requirements
    2. The HTML response from `Quest_experience_rewards` (prop="text") for skill XP rewards
    3. Merges and validates via Pydantic Quest models
    4. Saves to quests.json if save=True
    5. Reloads QUEST_DB in dataloader if reload_db=True
    """
    logger.info("Fetching quest list for quest points from OSRS Wiki...")
    list_html = fetch_wiki_page_content("Quests/List", prop="text")
    base_quests = parse_quests_list(list_html)
    qp_by_name = {q["name"]: q["quest_points"] for q in base_quests}

    logger.info("Fetching quests from OSRS Wiki Bucket API...")
    bucket_data = fetch_wiki_page_content(prop=None)
    bucket_quests = bucket_data.get("bucket", [])
    logger.info(f"Retrieved {len(bucket_quests)} quests from Bucket API.")

    logger.info("Fetching quest experience rewards HTML...")
    xp_html = fetch_wiki_page_content("Quest_experience_rewards", prop="text")
    xp_rewards_db = parse_quest_xp_rewards(xp_html)
    logger.info(f"Parsed XP rewards for {len(xp_rewards_db)} quests.")

    xp_by_lower = {k.lower(): v for k, v in xp_rewards_db.items()}
    valid_skills = {s.value for s in Skill}
    validated_quests: list[Quest] = []
    seen_names: set[str] = set()

    for item in bucket_quests:
        qname = item.get("page_name")
        if not qname:
            continue
        if qname in seen_names:
            continue
        seen_names.add(qname)

        difficulty = item.get("official_difficulty") or "Novice"
        raw_reqs = item.get("requirements", "")
        req_data = parse_bucket_requirements(raw_reqs)

        typed_skills: dict[Skill, int] = {
            Skill(s): lvl for s, lvl in req_data["skills"].items() if s in valid_skills
        }

        xp_entry = xp_rewards_db.get(qname) or xp_by_lower.get(qname.lower()) or {}
        typed_xp_rewards: dict[Skill, int] = {
            Skill(s): xp for s, xp in xp_entry.items() if s in valid_skills
        }

        # Look up quest points from Quests/List, fallback to QUEST_DB
        qp = qp_by_name.get(qname, 0) or (QUEST_DB[qname].quest_points if qname in QUEST_DB else 0)

        requirements = QuestRequirements(
            quests=req_data["quests"],
            skills=typed_skills,
            quest_points=req_data["quest_points"],
        )

        quest = Quest(
            id=qname,
            name=qname,
            quest_points=qp,
            difficulty=difficulty,
            requirements=requirements,
            xp_rewards=typed_xp_rewards,
        )
        validated_quests.append(quest)

    if save:
        out_path = target_file or (Path(__file__).parent.parent / "data" / "quests.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        quest_data = [q.model_dump(mode="json") for q in validated_quests]
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(quest_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved {len(validated_quests)} quests to {out_path}")

    if reload_db:
        reload_quests()

    return validated_quests
