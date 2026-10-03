import json
import tempfile
import unittest
from pathlib import Path

from app.models.player import AccountType, PlayerProfile
from app.models.quest import Quest, normalize_name
from app.repositories.quest_repository import QuestRepository, get_quest_repository
from app.services.optimizer.engine import get_missing_quests
from app.services.optimizer.simulator import OptimizationSimulator
from app.services.player_quest_parser import resolve_exporter_alias


class TestNormalizeName(unittest.TestCase):
    def test_ignores_case_whitespace_and_underscores(self):
        expected = "song of the elves"
        for variant in (
            "Song of the Elves",
            "SONG OF THE ELVES",
            "song_of_the_elves",
            "  Song   of the\tElves ",
        ):
            self.assertEqual(normalize_name(variant), expected, variant)

    def test_keeps_punctuation(self):
        self.assertEqual(normalize_name("Romeo & Juliet"), "romeo & juliet")
        self.assertEqual(
            normalize_name("Recipe for Disaster/Freeing Evil Dave"),
            "recipe for disaster/freeing evil dave",
        )

    def test_quest_exposes_normalized_name_without_serializing_it(self):
        quest = Quest(
            name="Cook's Assistant", quest_points=1, difficulty="Novice", length="short"
        )
        self.assertEqual(quest.normalized_name, "cook's assistant")
        self.assertNotIn("normalized_name", quest.model_dump())


class TestRepositoryNames(unittest.TestCase):
    def setUp(self):
        self.repo = get_quest_repository()

    def test_get_accepts_any_spelling(self):
        for variant in ("Cook's Assistant", "cook's assistant", "cook's_assistant"):
            quest = self.repo.get(variant)
            self.assertIsNotNone(quest, variant)
            self.assertEqual(quest.name, "Cook's Assistant")

    def test_canonical_name(self):
        self.assertEqual(self.repo.canonical_name(" DEMON slayer "), "Demon Slayer")
        # Unknown names pass through, trimmed
        self.assertEqual(self.repo.canonical_name(" Not A Quest "), "Not A Quest")

    def test_search_ignores_case_and_underscores(self):
        names = {quest.name for quest in self.repo.search(query="SONG_OF")}
        self.assertIn("Song of the Elves", names)

    def test_prerequisites_are_stored_under_canonical_names(self):
        def record(name: str, prereqs: list[str]) -> dict:
            return {
                "id": name,
                "name": name,
                "quest_points": 1,
                "difficulty": "Novice",
                "length": "short",
                "requirements": {"quests": prereqs},
            }

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "quests.json"
            path.write_text(
                json.dumps(
                    [record("First Quest", []), record("Second Quest", ["first_QUEST"])]
                ),
                encoding="utf-8",
            )
            repo = QuestRepository(data_path=path)

        second = repo.get("Second Quest")
        self.assertEqual(second.requirements.quests, ["First Quest"])

    def test_every_stored_prerequisite_is_a_known_quest_name(self):
        known = {quest.name for quest in self.repo.all()}
        for quest in self.repo.all():
            for prereq in quest.requirements.quests:
                self.assertIn(prereq, known, f"{quest.name} requires {prereq}")


class TestCompletedQuestNames(unittest.TestCase):
    def setUp(self):
        self.repo = get_quest_repository()

    def test_missing_quests_ignore_how_completed_names_are_spelled(self):
        expected = get_missing_quests(
            "Song of the Elves", {"Mourning's End Part II"}, repo=self.repo
        )
        self.assertNotIn("Mourning's End Part II", [quest.name for quest in expected])

        for variant in (
            "mourning's end part ii",
            "MOURNING'S_END_PART_II",
            " Mourning's End Part II ",
        ):
            actual = get_missing_quests("Song of the Elves", [variant], repo=self.repo)
            self.assertEqual(
                [quest.name for quest in actual],
                [quest.name for quest in expected],
                variant,
            )

    def test_simulator_stores_completed_quests_under_canonical_names(self):
        target = self.repo.get("Dragon Slayer I")
        simulator = OptimizationSimulator(
            player=PlayerProfile(
                username="Tester", account_type=AccountType.MAIN, skills={}
            ),
            missing_quests=[],
            target_quest=target,
            player_completed_quests={"cook's_assistant", "DEMON SLAYER"},
            quest_repository=self.repo,
        )
        self.assertEqual(
            simulator.completed_names, {"Cook's Assistant", "Demon Slayer"}
        )
        # Quest points are counted even though the names weren't spelled canonically
        self.assertEqual(
            simulator.current_qp,
            self.repo.get("Cook's Assistant").quest_points
            + self.repo.get("Demon Slayer").quest_points,
        )


class TestExporterAlias(unittest.TestCase):
    def test_alias_lookup_ignores_case_and_spacing(self):
        self.assertEqual(
            resolve_exporter_alias("  RECIPE for Disaster - Evil  Dave "),
            "Recipe for Disaster/Freeing Evil Dave",
        )

    def test_unknown_names_are_only_trimmed(self):
        self.assertEqual(
            resolve_exporter_alias(" Cook's Assistant "), "Cook's Assistant"
        )
