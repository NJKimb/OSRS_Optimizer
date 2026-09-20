import unittest
from unittest.mock import AsyncMock, patch

from app.core.skills import Skill
from app.models.plan import OptimizationRequest
from app.models.player import AccountType, PlayerProfile, SkillDetail
from app.models.quest import Quest, QuestRequirements
from app.services.optimizer.engine import (
    generate_optimization_plan,
    get_missing_quests,
    get_skill_requirements,
)
from app.services.optimizer.simulator import OptimizationSimulator


class TestOptimizationSimulator(unittest.TestCase):
    def setUp(self):
        self.player = PlayerProfile(
            username="TestUser",
            account_type=AccountType.IRONMAN,
            skills={
                Skill.ATTACK: SkillDetail(level=10, xp=1154),
                Skill.AGILITY: SkillDetail(level=20, xp=4470),
            },
            quests_status=set(),
        )
        self.quest1 = Quest(
            id="quest_one",
            name="Quest One",
            difficulty="Novice",
            length="Short",
            quest_points=1,
            requirements=QuestRequirements(
                skills={Skill.AGILITY: 25},
                quests=[],
            ),
            xp_rewards={Skill.ATTACK: 2000},
        )
        self.quest2 = Quest(
            id="quest_two",
            name="Quest Two",
            difficulty="Intermediate",
            length="Medium",
            quest_points=2,
            requirements=QuestRequirements(
                skills={Skill.ATTACK: 20},
                quests=["Quest One"],
            ),
            xp_rewards={},
        )

    def test_simulator_execution(self):
        simulator = OptimizationSimulator(
            player=self.player,
            missing_quests=[self.quest1, self.quest2],
            target_quest=self.quest2,
            target_goal="Quest Two",
            player_completed_quests=set(),
        )
        self.assertEqual(len(simulator.roadmap), 0)
        simulator.run()

        # Should have trained Agility to 25, completed Quest One, trained Attack if needed, completed Quest Two
        self.assertGreater(len(simulator.roadmap), 0)
        quest_steps = [s for s in simulator.roadmap if s.step_type == "quest"]
        self.assertEqual(len(quest_steps), 2)
        self.assertEqual(quest_steps[0].title, "Complete Quest One")
        self.assertEqual(quest_steps[1].title, "Complete Quest Two")

        # Check skill deficits summary
        skill_reqs = get_skill_requirements([self.quest1, self.quest2])
        deficits = simulator.build_skill_deficits(skill_reqs)
        self.assertGreater(len(deficits), 0)

    def test_already_completed_plan(self):
        """Testing when target quest is already completed returns 0-hour plan."""
        req = OptimizationRequest(
            username="TestUser",
            target_goal="Cook's Assistant",
            completed_quests=["Cook's Assistant"],
        )
        with patch(
            "app.services.optimizer.engine.fetch_player_profile",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = PlayerProfile(
                username="TestUser",
                account_type=AccountType.IRONMAN,
                skills={},
                quests_status={"Cook's Assistant"},
            )
            import asyncio

            response = asyncio.run(generate_optimization_plan(req))
            self.assertEqual(response.total_hours_remaining, 0.0)
            self.assertEqual(len(response.missing_quests), 0)
            self.assertEqual(response.roadmap[0].step_type, "complete")
