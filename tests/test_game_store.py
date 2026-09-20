import os
import sqlite3
import tempfile
import unittest

from app.game_store import GameStore, PersistentGameStore


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

    def test_claiming_a_place_transfers_the_flag_and_scores_the_new_owner(self):
        first = self.store.claim_place(
            game_session_id="territory-1",
            team_id="green",
            place_id="cat-point",
            score=30,
            occurred_at="2026-09-20T10:00:00+09:00",
        )
        second = self.store.claim_place(
            game_session_id="territory-1",
            team_id="blue",
            place_id="cat-point",
            score=30,
            occurred_at="2026-09-20T10:05:00+09:00",
        )

        self.assertTrue(first.claimed)
        self.assertTrue(second.claimed)
        self.assertTrue(second.transferred)
        self.assertEqual("blue", self.store.place_owner("territory-1", "cat-point"))

    def test_home_moves_to_a_random_high_value_owned_point_after_capture(self):
        self.store.claim_place(
            game_session_id="territory-1", team_id="green", place_id="home", score=100,
            occurred_at="2026-09-20T09:59:00+09:00",
        )
        self.store.claim_place(
            game_session_id="territory-1", team_id="green", place_id="low", score=10,
            occurred_at="2026-09-20T10:00:00+09:00",
        )
        self.store.claim_place(
            game_session_id="territory-1", team_id="green", place_id="high", score=50,
            occurred_at="2026-09-20T10:01:00+09:00",
        )
        self.store.set_home("territory-1", "green", "home")
        self.store.claim_place(
            game_session_id="territory-1", team_id="blue", place_id="home", score=100,
            occurred_at="2026-09-20T10:02:00+09:00",
        )

        self.assertEqual("high", self.store.home_for("territory-1", "green"))

    def test_initial_home_configuration_does_not_overwrite_a_relocated_home(self):
        for place_id, score in (("home", 100), ("high", 50)):
            self.store.claim_place(
                game_session_id="territory-1", team_id="green", place_id=place_id,
                score=score, occurred_at="2026-09-20T10:00:00+09:00",
            )
        self.store.set_home_if_missing("territory-1", "green", "home")
        self.store.claim_place(
            game_session_id="territory-1", team_id="blue", place_id="home", score=100,
            occurred_at="2026-09-20T10:01:00+09:00",
        )

        self.store.set_home_if_missing("territory-1", "green", "home")

        self.assertEqual("high", self.store.home_for("territory-1", "green"))

    def test_existing_claims_are_migrated_when_territory_storage_is_initialized(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "legacy.sqlite3")
            with sqlite3.connect(database_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE spot_claims (
                        game_session_id TEXT NOT NULL, team_id TEXT NOT NULL,
                        place_id TEXT NOT NULL, score INTEGER NOT NULL,
                        action_id TEXT NOT NULL,
                        PRIMARY KEY (game_session_id, team_id, place_id)
                    )
                    """
                )
                connection.execute(
                    "INSERT INTO spot_claims VALUES (?, ?, ?, ?, ?)",
                    ("legacy-1", "green", "old-place", 120, "old-action"),
                )

            store = PersistentGameStore(database_path)
            store.claim_place(
                game_session_id="legacy-1", team_id="green", place_id="new-place",
                score=10, action_id="new-action",
            )
            summary = store.team_summary("legacy-1", "green")

            self.assertEqual(130, summary["score"])
            self.assertEqual(["old-place", "new-place"], summary["claimed_places"])


if __name__ == "__main__":
    unittest.main()
