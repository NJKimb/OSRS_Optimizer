import unittest
from app.services.player_quest_parser import parse_player_quest_status

class TestPlayerQuestParser(unittest.TestCase):
    def test_full_character_exporter_dict(self):
        data = {
            "summary": {"finished": 2},
            "quests": [
                {"name": "Cook's Assistant", "state": "FINISHED"},
                {"name": "Demon Slayer", "state": "IN_PROGRESS"},
                {"name": "Dragon Slayer I", "state": "NOT_STARTED"},
            ]
        }
        res = parse_player_quest_status(data)
        self.assertEqual(res, {"Cook's Assistant"})

    def test_rfd_subquest_normalization(self):
        data = {
            "quests": [
                {"name": "Recipe for Disaster - Mountain Dwarf", "state": "FINISHED"},
                {"name": "Recipe for Disaster - Wartface & Bentnoze", "state": "FINISHED"},
                {"name": "Recipe for Disaster - Another Cook's Quest", "state": "FINISHED"},
            ]
        }
        res = parse_player_quest_status(data)
        self.assertIn("Recipe for Disaster/Freeing the Mountain Dwarf", res)
        self.assertIn("Recipe for Disaster/Freeing the Goblin generals", res)
        self.assertIn("Recipe for Disaster/Another Cook's Quest", res)

    def test_flat_dict(self):
        data = {
            "Cook's Assistant": "FINISHED",
            "Demon Slayer": "NOT_STARTED"
        }
        res = parse_player_quest_status(data)
        self.assertEqual(res, {"Cook's Assistant"})

    def test_json_string(self):
        raw = '{"quests": [{"name": "Waterfall Quest", "state": "FINISHED"}]}'
        res = parse_player_quest_status(raw)
        self.assertEqual(res, {"Waterfall Quest"})

    def test_empty_input(self):
        self.assertEqual(parse_player_quest_status(None), set())
        self.assertEqual(parse_player_quest_status({}), set())
        self.assertEqual(parse_player_quest_status(""), set())

if __name__ == "__main__":
    unittest.main()
