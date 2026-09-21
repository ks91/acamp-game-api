import os
import tempfile
import unittest

from app.api import create_app


class TestSessionRestartTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": os.path.join(self.directory.name, "game.sqlite3"),
                "TEAM_TOKENS": {"green-token": "green", "blue-token": "blue"},
                "PLACE_SCORES": {"center": 40},
                "TEAM_SESSIONS": {
                    "green": {
                        "game_session_id": "center-green-1",
                        "status": "test",
                        "allow_team_restart": True,
                        "scenario": {"places": []},
                    },
                    "blue": {
                        "game_session_id": "tokyo-blue-1",
                        "status": "live",
                        "allow_team_restart": False,
                        "scenario": {"places": []},
                    },
                },
            }
        ).test_client()

    def tearDown(self):
        self.directory.cleanup()

    def test_team_can_restart_only_its_explicitly_restartable_test_session(self):
        self.client.post(
            "/v1/actions",
            headers={"Authorization": "Bearer green-token"},
            json={
                "action_id": "claim-1",
                "game_session_id": "center-green-1",
                "type": "claim_place",
                "place_id": "center",
            },
        )

        response = self.client.post(
            "/v1/test-session/restart",
            headers={"Authorization": "Bearer green-token"},
            json={"confirm": True},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual("center-green-1", response.get_json()["game_session_id"])
        self.assertEqual(0, response.get_json()["score"])
        self.assertEqual([], response.get_json()["claimed_places"])

    def test_team_cannot_restart_a_live_or_non_restartable_session(self):
        response = self.client.post(
            "/v1/test-session/restart",
            headers={"Authorization": "Bearer blue-token"},
            json={"confirm": True},
        )
        self.assertEqual(403, response.status_code)


if __name__ == "__main__":
    unittest.main()
