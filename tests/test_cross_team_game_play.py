import os
import tempfile
import unittest

from app.api import create_app
from app.game_store import PersistentGameStore


class CrossTeamGamePlayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.directory.name, "game.sqlite3")
        self.client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": self.database_path,
                "TEAM_TOKENS": {"green-token": "green", "blue-token": "blue"},
                "PLACE_SCORES": {"demo-place": 10},
                "TEAM_SESSIONS": {
                    "green": {
                        "game_session_id": "green-game",
                        "status": "test",
                        "play_device_id": "green-ipad",
                        "scenario": {"id": "green-game", "name": "Green game", "places": []},
                    },
                    "blue": {
                        "game_session_id": "blue-game",
                        "status": "test",
                        "play_device_id": "blue-ipad",
                        "scenario": {"id": "blue-game", "name": "Blue game", "places": []},
                    },
                },
            }
        ).test_client()

    def tearDown(self):
        self.directory.cleanup()

    def test_team_can_read_another_published_team_game_without_using_its_token(self):
        response = self.client.get(
            "/v1/game/definition?game_team=blue",
            headers={"Authorization": "Bearer green-token"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual("Blue game", response.get_json()["name"])
        self.assertEqual("green", response.get_json()["player_team_id"])
        self.assertEqual("blue", response.get_json()["game_team_id"])
        self.assertEqual("blue-game", response.get_json()["game_session_id"])

    def test_team_can_claim_in_selected_game_with_its_own_device(self):
        response = self.client.post(
            "/v1/actions?game_team=blue",
            headers={"Authorization": "Bearer green-token"},
            json={
                "action_id": "green-plays-blue-1",
                "game_session_id": "green-game",
                "type": "claim_place",
                "place_id": "demo-place",
                "device_id": "green-ipad",
            },
        )

        self.assertEqual(201, response.status_code)
        self.assertEqual(10, response.get_json()["team_score"])
        self.assertEqual(
            10,
            PersistentGameStore(self.database_path).team_summary("blue-game", "green")["score"],
        )
        self.assertEqual(
            0,
            PersistentGameStore(self.database_path).team_summary("green-game", "green")["score"],
        )

    def test_selected_game_state_uses_selected_games_progress(self):
        self.client.post(
            "/v1/actions?game_team=blue",
            headers={"Authorization": "Bearer green-token"},
            json={
                "action_id": "green-plays-blue-2",
                "game_session_id": "green-game",
                "type": "claim_place",
                "place_id": "demo-place",
                "device_id": "green-ipad",
            },
        )

        response = self.client.get(
            "/v1/team/state?game_team=blue",
            headers={"Authorization": "Bearer green-token"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual("blue", response.get_json()["game_team_id"])
        self.assertEqual("blue-game", response.get_json()["game_session_id"])
        self.assertEqual(10, response.get_json()["score"])

    def test_unknown_game_team_is_rejected(self):
        response = self.client.get(
            "/v1/game/definition?game_team=unknown",
            headers={"Authorization": "Bearer green-token"},
        )

        self.assertEqual(403, response.status_code)


if __name__ == "__main__":
    unittest.main()
