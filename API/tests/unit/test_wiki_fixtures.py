"""
Runs the full quest sync against saved OSRS Wiki responses, so changes to the
wiki's markup show up as test failures instead of silently corrupted data.
Refresh the fixtures with: python -m scripts.refresh_wiki_fixtures
"""

import gzip
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models.skills import Skill
from app.services.wiki import sync
from app.services.optimizer.simulator import QUEST_ESTIMATED_TIME

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "wiki"
KNOWN_DIFFICULTIES = {
    "Novice",
    "Intermediate",
    "Experienced",
    "Master",
    "Grandmaster",
    "Special",
}


def read_gzip(file_name: str) -> str:
    with gzip.open(FIXTURES_DIR / file_name, "rt", encoding="utf-8") as fixture_file:
        return fixture_file.read()


class TestSyncWithWikiFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        responses = {
            ("Quests/List", "text"): read_gzip("quests_list.html.gz"),
            ("Quest_experience_rewards", "text"): read_gzip("quest_xp_rewards.html.gz"),
        }
        bucket = json.loads(read_gzip("quest_bucket.json.gz"))

        def fake_fetch(page_title: str, prop: str):
            return responses[(page_title, prop)]

        with (
            patch.object(sync, "fetch_wiki_page_content", fake_fetch),
            patch.object(sync, "fetch_quest_bucket", lambda: bucket),
            # Silence the sync's expected "Skipping ..." warnings
            patch.object(sync.logger, "warning"),
        ):
            quests = sync.sync_osrs_quests(save=False, reload_db=False)
        cls.quests = {quest.name: quest for quest in quests}

    def test_quest_count(self):
        self.assertGreaterEqual(len(self.quests), 190)

    def test_every_quest_has_known_metadata(self):
        for quest in self.quests.values():
            with self.subTest(quest=quest.name):
                self.assertIn(quest.difficulty, KNOWN_DIFFICULTIES)
                self.assertIn(quest.length, QUEST_ESTIMATED_TIME)
                self.assertGreaterEqual(quest.quest_points, 0)

    def test_every_prerequisite_is_a_known_quest(self):
        quest_names = set(self.quests)
        for quest in self.quests.values():
            with self.subTest(quest=quest.name):
                self.assertEqual(set(quest.requirements.quests) - quest_names, set())

    def test_boostable_skills_are_requirements(self):
        for quest in self.quests.values():
            with self.subTest(quest=quest.name):
                self.assertLessEqual(
                    set(quest.requirements.boostable_skills),
                    set(quest.requirements.skills),
                )

    def test_song_of_the_elves(self):
        sote = self.quests["Song of the Elves"]
        self.assertEqual(sote.difficulty, "Grandmaster")
        self.assertEqual(sote.quest_points, 4)
        self.assertEqual(sote.requirements.skills[Skill.AGILITY], 70)
        self.assertNotIn(Skill.AGILITY, sote.requirements.boostable_skills)
        self.assertIn("Mourning's End Part II", sote.requirements.quests)
        self.assertEqual(sote.xp_rewards[Skill.AGILITY], 40_000)

    def test_knights_sword(self):
        knights_sword = self.quests["The Knight's Sword"]
        self.assertEqual(knights_sword.requirements.skills, {Skill.MINING: 10})
        self.assertEqual(knights_sword.requirements.boostable_skills, [Skill.MINING])
        self.assertEqual(knights_sword.xp_rewards, {Skill.SMITHING: 12_725})

    def test_quest_point_requirement(self):
        dragon_slayer = self.quests["Dragon Slayer I"]
        self.assertEqual(dragon_slayer.requirements.quest_points, 32)
        self.assertEqual(dragon_slayer.quest_points, 2)

    def test_cooks_assistant(self):
        cooks_assistant = self.quests["Cook's Assistant"]
        self.assertEqual(cooks_assistant.difficulty, "Novice")
        self.assertEqual(cooks_assistant.xp_rewards, {Skill.COOKING: 300})


if __name__ == "__main__":
    unittest.main()
