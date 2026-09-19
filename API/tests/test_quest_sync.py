import unittest
from fastapi.testclient import TestClient

from main import app
from app.core.skills import Skill
from app.models.quest import Quest
from app.services.dataloader import QUEST_DB
from app.services.quest_parser import (
    parse_bucket_requirements,
    parse_quest_xp_rewards,
    parse_quests_list,
)
from app.services.optimizer.engine import get_missing_quests, get_skill_requirements


class TestQuestSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

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

    def test_parse_quest_xp_rewards_html_mock(self):
        sample_html = """
        <h2>Agility</h2>
        <table class="wikitable">
        <tr data-rowid="Recruitment Drive">
        <td>Recruitment Drive</td><td>Yes</td><td>1,000.5</td>
        </tr>
        </table>
        <h2>Attack</h2>
        <table class="wikitable">
        <tr data-rowid="Waterfall Quest">
        <td>Waterfall Quest</td><td>Yes</td><td>13,750</td>
        </tr>
        </table>
        """
        xp = parse_quest_xp_rewards(sample_html)
        self.assertIn("Recruitment Drive", xp)
        self.assertEqual(xp["Recruitment Drive"]["agility"], 1000)
        self.assertIn("Waterfall Quest", xp)
        self.assertEqual(xp["Waterfall Quest"]["attack"], 13750)

    def test_parse_bucket_requirements(self):
        sample_req = """
        *<span class="scp" data-skill="Agility" data-level="70">70 Agility</span>
        *<span class="scp" data-skill="Quest points" data-level="32">32 Quest points</span>
        *Completion of the following quests:
        **[[Mourning's End Part II]]
        ***[[Mourning's End Part I]]
        **[[Druidic Ritual]]
        """
        res = parse_bucket_requirements(sample_req)
        self.assertEqual(res["skills"]["agility"], 70)
        self.assertEqual(res["quest_points"], 32)
        self.assertIn("Mourning's End Part II", res["quests"])
        self.assertIn("Druidic Ritual", res["quests"])

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
        self.assertEqual(quests[0]["name"], "Cook's Assistant")
        self.assertEqual(quests[0]["difficulty"], "Novice")
        self.assertEqual(quests[0]["quest_points"], 1)
        self.assertEqual(quests[1]["name"], "Dragon Slayer I")
        self.assertEqual(quests[1]["difficulty"], "Experienced")
        self.assertEqual(quests[1]["quest_points"], 2)

    def test_quests_database_integrity(self):
        """Verifies that all synced quests in QUEST_DB are loaded and valid."""
        self.assertGreaterEqual(len(QUEST_DB), 190)
        self.assertIn("Song of the Elves", QUEST_DB)
        self.assertIn("The Knight's Sword", QUEST_DB)
        self.assertIn("Cook's Assistant", QUEST_DB)

        sote = QUEST_DB["Song of the Elves"]
        self.assertEqual(sote.name, "Song of the Elves")
        self.assertEqual(sote.difficulty, "Grandmaster")
        self.assertEqual(sote.quest_points, 4)
        self.assertEqual(sote.requirements.skills[Skill.AGILITY], 70)
        self.assertEqual(sote.xp_rewards[Skill.AGILITY], 40000)

        for q_name, q in QUEST_DB.items():
            self.assertIsInstance(q, Quest)
            self.assertEqual(q.name, q_name)
            self.assertTrue(bool(q.name))
            self.assertTrue(bool(q.difficulty))
            self.assertGreaterEqual(q.quest_points, 0)

    def test_optimizer_with_synced_quests(self):
        """Tests that the optimizer DFS engine can resolve prerequisite trees on the real database."""
        missing_quests = get_missing_quests("Song of the Elves", completed_quests=[])
        self.assertGreater(len(missing_quests), 5)
        self.assertTrue(any(q.name == "Mourning's End Part II" for q in missing_quests))
        self.assertEqual(missing_quests[-1].name, "Song of the Elves")

        req_skills = get_skill_requirements(missing_quests)
        self.assertEqual(req_skills[Skill.AGILITY], 70)
        self.assertEqual(req_skills[Skill.MINING], 70)

    def test_api_quests_endpoints(self):
        """Tests the /api/quests FastAPI endpoints."""
        # List all
        resp = self.client.get("/api/quests")
        self.assertEqual(resp.status_code, 200)
        quests = resp.json()
        self.assertGreaterEqual(len(quests), 190)

        # Search filter
        resp = self.client.get("/api/quests?search=cook")
        self.assertEqual(resp.status_code, 200)
        filtered = resp.json()
        self.assertTrue(any(q["name"] == "Cook's Assistant" for q in filtered))

        # Difficulty filter
        resp = self.client.get("/api/quests?difficulty=Grandmaster")
        self.assertEqual(resp.status_code, 200)
        gm_quests = resp.json()
        self.assertTrue(all(q["difficulty"].lower() == "grandmaster" for q in gm_quests))
        self.assertTrue(any(q["name"] == "Song of the Elves" for q in gm_quests))

        # Single quest
        resp = self.client.get("/api/quests/The Knight's Sword")
        self.assertEqual(resp.status_code, 200)
        q = resp.json()
        self.assertEqual(q["name"], "The Knight's Sword")
        self.assertEqual(q["xp_rewards"]["smithing"], 12725)

        # 404 for non-existent quest
        resp = self.client.get("/api/quests/non_existent_quest_xyz")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
