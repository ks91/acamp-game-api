import os
import tempfile
import unittest

from app.api import create_app


class TeamGameModeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": os.path.join(self.directory.name, "game.sqlite3"),
                "TEAM_TOKENS": {"green-token": "green"},
                "PLACE_SCORES": {"demo-place": 10},
                "TEAM_SESSIONS": {
                    "green": {
                        "modes": {
                            "center_test": {
                                "game_session_id": "center-green-1",
                                "status": "test",
                                "scenario": {"id": "center", "name": "センター棟テスト", "places": []},
                            },
                            "tokyo": {
                                "game_session_id": "tokyo-green-1",
                                "status": "test",
                                "scenario": {"id": "tokyo", "name": "Green 東京版", "places": []},
                            },
                        }
                    }
                },
            }
        ).test_client()

    def tearDown(self):
        self.directory.cleanup()

    def test_definition_selects_the_requested_published_mode(self):
        response = self.client.get(
            "/v1/game/definition?game_mode=tokyo",
            headers={"Authorization": "Bearer green-token"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual("tokyo", response.get_json()["game_mode"])
        self.assertEqual("tokyo-green-1", response.get_json()["game_session_id"])

    def test_action_is_recorded_in_the_selected_mode_session(self):
        response = self.client.post(
            "/v1/actions?game_mode=tokyo",
            headers={"Authorization": "Bearer green-token"},
            json={
                "action_id": "tokyo-claim-1",
                "game_session_id": "center-green-1",
                "type": "claim_place",
                "place_id": "demo-place",
            },
        )
        self.assertEqual(201, response.status_code)
        self.assertEqual(10, response.get_json()["team_score"])
        state = self.client.get(
            "/v1/team/state?game_mode=tokyo",
            headers={"Authorization": "Bearer green-token"},
        )
        self.assertEqual("tokyo-green-1", state.get_json()["game_session_id"])
        self.assertEqual(10, state.get_json()["score"])

    def test_unknown_mode_is_rejected(self):
        response = self.client.get(
            "/v1/game/definition?game_mode=not-a-mode",
            headers={"Authorization": "Bearer green-token"},
        )
        self.assertEqual(403, response.status_code)


if __name__ == "__main__":
    unittest.main()
