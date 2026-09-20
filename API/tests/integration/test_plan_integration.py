import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from main import app
from app.core.skills import Skill
from app.models.player import AccountType, PlayerProfile, SkillDetail


class TestPlanIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @patch("app.services.optimizer.engine.fetch_player_profile", new_callable=AsyncMock)
    def test_optimize_endpoint_with_sote(self, mock_fetch):
        # Mock a mid-level account
        mock_fetch.return_value = PlayerProfile(
            username="John RedHelm",
            account_type=AccountType.IRONMAN,
            skills={
                Skill.AGILITY: SkillDetail(level=60, xp=273742),
                Skill.MINING: SkillDetail(level=65, xp=449428),
                Skill.SMITHING: SkillDetail(level=70, xp=737627),
            },
            quests_status={"Cook's Assistant", "Waterfall Quest"},
        )

        payload = {
            "username": "John RedHelm",
            "account_type": "ironman",
            "target_goal": "Song of the Elves",
            "quests_status": [
                {"name": "Cook's Assistant", "state": "FINISHED"},
                {"name": "Waterfall Quest", "state": "FINISHED"},
            ],
        }

        response = self.client.post("/api/optimize/plan", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["goal_name"], "Song of the Elves")
        self.assertGreater(data["total_hours_remaining"], 0)
        self.assertIn("Song of the Elves", data["missing_quests"])
        self.assertNotIn("Cook's Assistant", data["missing_quests"])
        self.assertNotIn("Waterfall Quest", data["missing_quests"])
        self.assertGreater(len(data["roadmap"]), 0)
        self.assertGreater(len(data["skill_deficits"]), 0)

    @patch("app.services.optimizer.engine.fetch_player_profile", new_callable=AsyncMock)
    def test_optimize_endpoint_with_json_string(self, mock_fetch):
        mock_fetch.return_value = PlayerProfile(
            username="John RedHelm",
            account_type=AccountType.IRONMAN,
            skills={
                Skill.AGILITY: SkillDetail(level=60, xp=273742),
            },
            quests_status=set(),
        )

        raw_json_str = (
            '{"summary": {"finished": 1}, '
            '"quests": [{"name": "Waterfall Quest", "state": "FINISHED"}]}'
        )
        payload = {
            "username": "John RedHelm",
            "account_type": "ironman",
            "target_goal": "Song of the Elves",
            "quests_status": raw_json_str,
        }

        response = self.client.post("/api/optimize/plan", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn("Waterfall Quest", data["missing_quests"])

