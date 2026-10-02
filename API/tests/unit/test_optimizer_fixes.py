import unittest

from app.models.skills import MAX_LEVEL, XP_TABLE, Skill, xp_for_level
from app.models.player import AccountType, PlayerProfile, SkillDetail
from app.models.quest import Quest, QuestRequirements
from app.repositories.quest_repository import get_quest_repository
from app.services.optimizer.engine import get_missing_quests
from app.services.optimizer.skill_boosts import get_min_base_level, get_skill_boost
from app.services.optimizer.simulator import OptimizationSimulator
from app.services.wiki.parsers import parse_bucket_requirements


def make_player(skills: dict[Skill, int] | None = None) -> PlayerProfile:
    return PlayerProfile(
        username="TestUser",
        account_type=AccountType.MAIN,
        skills={
            skill: SkillDetail(level=level, xp=xp_for_level(level))
            for skill, level in (skills or {}).items()
        },
    )


class TestXpForLevel(unittest.TestCase):
    def test_clamps_to_valid_range(self):
        self.assertEqual(xp_for_level(0), 0)
        self.assertEqual(xp_for_level(99), 13_034_431)
        self.assertEqual(xp_for_level(500), XP_TABLE[MAX_LEVEL])


class TestSlugGoal(unittest.TestCase):
    def test_completed_goal_given_as_slug_is_not_missing(self):
        self.assertEqual(
            get_missing_quests("cook's_assistant", {"Cook's Assistant"}), []
        )


class TestQuestPointFillers(unittest.TestCase):
    def test_fillers_added_to_reach_qp_requirement(self):
        repo = get_quest_repository()
        target = repo.get("Dragon Slayer I")
        assert target is not None
        simulator = OptimizationSimulator(
            player=make_player(),
            missing_quests=get_missing_quests("Dragon Slayer I", set(), repo=repo),
            target_quest=target,
            player_completed_quests=set(),
            repo=repo,
        )
        simulator.run()

        completed = simulator.ordered_completed_quests
        self.assertEqual(completed[-1].name, "Dragon Slayer I")
        qp_before_target = sum(quest.quest_points for quest in completed[:-1])
        self.assertGreaterEqual(qp_before_target, target.requirements.quest_points)
        self.assertTrue(simulator.qp_filler_reasons)
        filler_step = simulator.roadmap[0]
        self.assertIn("QP needed for Dragon Slayer I", filler_step.description)


class TestBoosts(unittest.TestCase):
    def setUp(self):
        self.quest = Quest(
            name="Boost Quest",
            quest_points=1,
            difficulty="Novice",
            length="Short",
            requirements=QuestRequirements(
                skills={Skill.AGILITY: 70, Skill.THIEVING: 50},
                boostable_skills=[Skill.AGILITY, Skill.THIEVING],
            ),
        )

    def run_simulator(self, allow_boosts: bool) -> OptimizationSimulator:
        simulator = OptimizationSimulator(
            player=make_player({Skill.AGILITY: 65, Skill.THIEVING: 50}),
            missing_quests=[self.quest],
            target_quest=self.quest,
            player_completed_quests=set(),
            allow_boosts=allow_boosts,
        )
        simulator.run()
        return simulator

    def test_min_base_level(self):
        self.assertEqual(get_min_base_level(70, get_skill_boost(Skill.AGILITY)), 65)
        # Super attack: 5 + 15% of base
        self.assertEqual(get_min_base_level(99, get_skill_boost(Skill.ATTACK)), 82)
        self.assertEqual(get_min_base_level(50, None), 50)

    def test_boost_replaces_training(self):
        simulator = self.run_simulator(allow_boosts=True)
        self.assertEqual([step.step_type for step in simulator.roadmap], ["quest"])
        self.assertIn("Agility to 70 (Summer pie)", simulator.roadmap[0].description)
        deficits = {
            deficit.skill: deficit for deficit in simulator.build_skill_deficits()
        }
        self.assertEqual(deficits[Skill.AGILITY].target_level, 65)
        self.assertEqual(deficits[Skill.AGILITY].boost, "Boost to 70 with a Summer pie")

    def test_boosts_can_be_disabled(self):
        simulator = self.run_simulator(allow_boosts=False)
        self.assertEqual(simulator.roadmap[0].title, "Train Agility to level 70")

    def test_parse_boostable_flag(self):
        sample_req = (
            '*<span class="scp" data-skill="Mining" data-level="10">10 Mining</span> '
            '<sup>[<span title="This requirement is boostable">boostable</span>]</sup>\n'
            '*<span class="scp" data-skill="Agility" data-level="70">70 Agility</span> '
            '<sup>[<span title="This requirement is not boostable">not boostable</span>]</sup>'
        )
        result = parse_bucket_requirements(sample_req)
        self.assertEqual(result.skills, {Skill.MINING: 10, Skill.AGILITY: 70})
        self.assertEqual(result.boostable_skills, [Skill.MINING])


class TestSharedSkillRequirement(unittest.TestCase):
    def setUp(self):
        self.first_quest = Quest(
            name="First Quest",
            quest_points=1,
            difficulty="Novice",
            length="Short",
            requirements=QuestRequirements(skills={Skill.AGILITY: 20}),
            xp_rewards={Skill.AGILITY: 2_000},
        )
        self.second_quest = Quest(
            name="Second Quest",
            quest_points=1,
            difficulty="Novice",
            length="Short",
            requirements=QuestRequirements(
                quests=["First Quest"], skills={Skill.AGILITY: 30}
            ),
        )

    def test_higher_requirement_raises_target(self):
        simulator = OptimizationSimulator(
            player=make_player(),
            missing_quests=[self.first_quest, self.second_quest],
            target_quest=self.second_quest,
            player_completed_quests=set(),
        )
        simulator.run()

        self.assertEqual(
            [step.title for step in simulator.roadmap],
            [
                "Train Agility to level 20",
                "Complete First Quest",
                "Train Agility to level 30",
                "Complete Second Quest",
            ],
        )
        self.assertEqual(simulator.skill_targets[Skill.AGILITY].base_level, 30)

        deficits = {
            deficit.skill: deficit for deficit in simulator.build_skill_deficits()
        }
        agility = deficits[Skill.AGILITY]
        self.assertEqual(agility.target_level, 30)
        self.assertEqual(agility.xp_needed, xp_for_level(30))
        self.assertEqual(agility.quest_xp_rewards, 2_000)
        self.assertEqual(agility.remaining_xp_to_grind, xp_for_level(30) - 2_000)


if __name__ == "__main__":
    unittest.main()
