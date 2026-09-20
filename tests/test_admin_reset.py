import os
import tempfile
import unittest

from app.api import create_app


class AdminResetTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": os.path.join(self.directory.name, "game.sqlite3"),
                "TEAM_TOKENS": {"green-token": "green"},
                "ADMIN_TOKEN": "admin-token",
                "PLACE_SCORES": {"center": 40},
                "GAME_SESSION_ID": "green-1",
            }
        ).test_client()

    def tearDown(self):
        self.directory.cleanup()

    def test_admin_reset_clears_one_sessions_territories_scores_and_homes(self):
        self.client.post(
            "/v1/actions",
            headers={"Authorization": "Bearer green-token"},
            json={
                "action_id": "claim-1",
                "game_session_id": "green-1",
                "type": "claim_place",
                "place_id": "center",
            },
        )

        response = self.client.post(
            "/v1/admin/session/reset",
            headers={"Authorization": "Bearer admin-token"},
            json={"game_session_id": "green-1", "reason": "start field test"},
        )
        state = self.client.get("/v1/team/state", headers={"Authorization": "Bearer green-token"})

        self.assertEqual(200, response.status_code)
        self.assertEqual("green-1", response.get_json()["game_session_id"])
        self.assertEqual(0, state.get_json()["score"])
        self.assertEqual([], state.get_json()["claimed_places"])


if __name__ == "__main__":
    unittest.main()
