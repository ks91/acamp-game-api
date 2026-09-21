import unittest

from scripts.staff_start import start_team_modes


class StaffStartBatchTests(unittest.TestCase):
    def test_preflight_missing_mode_does_not_start_any_team(self):
        registry = {
            "green": {"modes": {"tokyo": {"game_session_id": "day4-tokyo-green-1"}}},
            "yellow": {"modes": {}},
        }
        calls = []

        with self.assertRaisesRegex(ValueError, "yellow:tokyo"):
            start_team_modes(registry, ["green", "yellow"], "tokyo", "start", request=lambda *args, **kwargs: calls.append((args, kwargs)))
        self.assertEqual([], calls)

    def test_starts_each_preflighted_team(self):
        registry = {
            "green": {"modes": {"tokyo": {"game_session_id": "day4-tokyo-green-1"}}},
            "blue": {"modes": {"tokyo": {"game_session_id": "day4-tokyo-blue-1"}}},
        }
        calls = []
        messages = start_team_modes(registry, ["green", "blue"], "tokyo", "start", request=lambda *args, **kwargs: calls.append((args, kwargs)))
        self.assertEqual(4, len(calls))
        self.assertEqual(2, len(messages))


if __name__ == "__main__":
    unittest.main()
