import sqlite3
import unittest

from app.game_store import GameStore


class GameStoreTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.store = GameStore(self.connection)
        self.store.initialize()

    def tearDown(self):
        self.connection.close()

    def test_claiming_a_place_first_time_awards_its_score(self):
        result = self.store.claim_place(
            game_session_id="aoyama-2026",
            team_id="green",
            place_id="time-site",
            score=120,
            occurred_at="2026-09-20T10:00:00+09:00",
        )

        self.assertTrue(result.claimed)
        self.assertEqual(120, result.score_delta)
        self.assertEqual(120, result.team_score)

    def test_claiming_same_place_twice_returns_original_result_without_extra_score(self):
        first = self.store.claim_place(
            game_session_id="aoyama-2026",
            team_id="green",
            place_id="time-site",
            score=120,
            occurred_at="2026-09-20T10:00:00+09:00",
        )
        second = self.store.claim_place(
            game_session_id="aoyama-2026",
            team_id="green",
            place_id="time-site",
            score=120,
            occurred_at="2026-09-20T10:01:00+09:00",
        )

        self.assertTrue(first.claimed)
        self.assertFalse(second.claimed)
        self.assertEqual(0, second.score_delta)
        self.assertEqual(120, second.team_score)


if __name__ == "__main__":
    unittest.main()
