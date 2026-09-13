import unittest
from fastapi.testclient import TestClient

from main import app
from app.core.skills import Skill
from app.models.quest import Quest
from app.services.dataloader import QUEST_DB
from app.services.quest_sync import (
    slugify,
    parse_quest_requirements,
    parse_quest_xp_rewards,
    parse_quests_list,
)
from app.services.optimizer.engine import get_missing_quests, get_skill_requirements


class TestQuestSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_slugify(self):
        self.assertEqual(slugify("Cook's Assistant"), "cooks_assistant")
        self.assertEqual(slugify("Dragon Slayer I"), "dragon_slayer_1")
        self.assertEqual(slugify("Dragon Slayer II"), "dragon_slayer_2")
        self.assertEqual(slugify("Mourning's End Part I"), "mournings_end_part_1")
        self.assertEqual(slugify("Mourning's End Part II"), "mournings_end_part_2")
        self.assertEqual(
            slugify("Recipe for Disaster/Freeing the Mountain Dwarf"),
            "recipe_for_disaster_freeing_the_mountain_dwarf"
        )
        self.assertEqual(slugify("Between a Rock..."), "between_a_rock")

    def test_parse_quest_requirements_mock(self):
        sample_lua = """
local questReqs = {
    ['Animal Magnetism'] = {
        ['quests'] = {
            'Ernest the Chicken',
            'Priest in Peril',
            'The Restless Ghost'
        },
        ['skills'] = {
            {'Crafting', 19},
            {'Prayer', 31, 'ironman'},
            {'Ranged', 30},
            {'Slayer', 18},
            {'Woodcutting', 35}
        }
    },
    ['Below Ice Mountain'] = {
        ['quests'] = {},
        ['skills'] = {
            {'Quest point', 16}
        }
    }
}
return questReqs
        """
        reqs = parse_quest_requirements(sample_lua)
        self.assertIn("Animal Magnetism", reqs)
        self.assertEqual(reqs["Animal Magnetism"]["quests"], [
            "Ernest the Chicken",
            "Priest in Peril",
            "The Restless Ghost"
        ])
        self.assertEqual(reqs["Animal Magnetism"]["skills"]["crafting"], 19)
        self.assertEqual(reqs["Animal Magnetism"]["skills"]["ranged"], 30)
        self.assertEqual(reqs["Animal Magnetism"]["quest_points"], 0)

        self.assertIn("Below Ice Mountain", reqs)
        self.assertEqual(reqs["Below Ice Mountain"]["quest_points"], 16)

    def test_parse_quest_xp_rewards_mock(self):
        sample_wikitext = """
==Set experience==
===Agility===
{| class="wikitable"
|- data-rowid="Recruitment Drive"
|[[Recruitment Drive]]
|Yes||{{+=|agility|1,000.5|echo=2}}
|-
|- data-rowid="Waterfall Quest"
|[[Waterfall Quest]]
|Yes||{{+=|attack|13,750|echo=2}}||{{+=|strength|13,750|echo=2}}
|}
        """
        xp = parse_quest_xp_rewards(sample_wikitext)
        self.assertIn("Recruitment Drive", xp)
        self.assertEqual(xp["Recruitment Drive"]["agility"], 1000)
        self.assertIn("Waterfall Quest", xp)
        self.assertEqual(xp["Waterfall Quest"]["attack"], 13750)

    def test_parse_quests_list_mock(self):
        sample_html = """
<table class="wikitable">
<tr data-rowid="Cook's Assistant">
<td>1</td>
<td><a href="/w/Cook%27s_Assistant">Cook's Assistant</a></td>
<td>Novice</td>
<td>Very Short</td>
<td>1</td>
</tr>
<tr data-rowid="Dragon Slayer I">
<td>17</td>
<td><a href="/w/Dragon_Slayer_I">Dragon Slayer I</a></td>
<td>Experienced</td>
<td>Medium</td>
<td>2</td>
</tr>
</table>
<div class="mw-heading mw-heading2"><h2 id="Miniquests">Miniquests</h2></div>
<tr data-rowid="Barcrawl">
<td>999</td>
<td><a href="/w/Barcrawl">Alfred Grimhand's Barcrawl</a></td>
<td>Miniquest</td>
<td>Short</td>
<td>0</td>
</tr>
        """
        quests = parse_quests_list(sample_html)
        self.assertEqual(len(quests), 2)
        self.assertEqual(quests[0]["id"], "cooks_assistant")
        self.assertEqual(quests[0]["difficulty"], "Novice")
        self.assertEqual(quests[0]["quest_points"], 1)
        self.assertEqual(quests[1]["id"], "dragon_slayer_1")
        self.assertEqual(quests[1]["difficulty"], "Experienced")
        self.assertEqual(quests[1]["quest_points"], 2)

    def test_quests_database_integrity(self):
        """Verifies that all synced quests in QUEST_DB are loaded and valid."""
        self.assertGreaterEqual(len(QUEST_DB), 190)
        self.assertIn("song_of_the_elves", QUEST_DB)
        self.assertIn("the_knights_sword", QUEST_DB)
        self.assertIn("cooks_assistant", QUEST_DB)

        sote = QUEST_DB["song_of_the_elves"]
        self.assertEqual(sote.name, "Song of the Elves")
        self.assertEqual(sote.difficulty, "Grandmaster")
        self.assertEqual(sote.quest_points, 4)
        self.assertEqual(sote.requirements.skills[Skill.AGILITY], 70)
        self.assertEqual(sote.xp_rewards[Skill.AGILITY], 40000)

        for qid, q in QUEST_DB.items():
            self.assertIsInstance(q, Quest)
            self.assertEqual(q.id, qid)
            self.assertTrue(bool(q.name))
            self.assertTrue(bool(q.difficulty))
            self.assertGreaterEqual(q.quest_points, 0)

    def test_optimizer_with_synced_quests(self):
        """Tests that the optimizer DFS engine can resolve prerequisite trees on the real database."""
        missing_quests = get_missing_quests("song_of_the_elves", completed_quests=[])
        self.assertGreater(len(missing_quests), 5)
        self.assertTrue(any(q.id == "mournings_end_part_2" for q in missing_quests))
        self.assertEqual(missing_quests[-1].id, "song_of_the_elves")

        req_skills = get_skill_requirements(missing_quests)
        self.assertEqual(req_skills[Skill.AGILITY], 70)
        self.assertEqual(req_skills[Skill.MINING], 70)

    def test_api_quests_endpoints(self):
        """Tests the new /api/quests FastAPI endpoints."""
        # List all
        resp = self.client.get("/api/quests")
        self.assertEqual(resp.status_code, 200)
        quests = resp.json()
        self.assertGreaterEqual(len(quests), 190)

        # Search filter
        resp = self.client.get("/api/quests?search=cook")
        self.assertEqual(resp.status_code, 200)
        filtered = resp.json()
        self.assertTrue(any(q["id"] == "cooks_assistant" for q in filtered))

        # Difficulty filter
        resp = self.client.get("/api/quests?difficulty=Grandmaster")
        self.assertEqual(resp.status_code, 200)
        gm_quests = resp.json()
        self.assertTrue(all(q["difficulty"].lower() == "grandmaster" for q in gm_quests))
        self.assertTrue(any(q["id"] == "song_of_the_elves" for q in gm_quests))

        # Single quest
        resp = self.client.get("/api/quests/the_knights_sword")
        self.assertEqual(resp.status_code, 200)
        q = resp.json()
        self.assertEqual(q["name"], "The Knight's Sword")
        self.assertEqual(q["xp_rewards"]["smithing"], 12725)

        # 404 for non-existent quest
        resp = self.client.get("/api/quests/non_existent_quest_xyz")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
