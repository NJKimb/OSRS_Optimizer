"""
Downloads fresh OSRS Wiki responses used by tests/unit/test_wiki_fixtures.py.
Usage:
    python -m scripts.refresh_wiki_fixtures
"""

import gzip
import json
from pathlib import Path

from app.services.wiki_quest_parser import fetch_wiki_page_content

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "wiki"


def write_gzip(file_name: str, content: str) -> None:
    with gzip.open(FIXTURES_DIR / file_name, "wt", encoding="utf-8") as fixture_file:
        fixture_file.write(content)


def main():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    write_gzip("quests_list.html.gz", fetch_wiki_page_content("Quests/List", "text"))
    write_gzip("quest_bucket.json.gz", json.dumps(fetch_wiki_page_content()))
    write_gzip(
        "quest_xp_rewards.html.gz",
        fetch_wiki_page_content("Quest_experience_rewards", "text"),
    )
    print(f"Refreshed wiki fixtures in {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
