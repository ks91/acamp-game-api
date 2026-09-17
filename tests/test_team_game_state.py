import os
import tempfile
import unittest

from app.api import create_app


class TeamGameStateEndpointTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": os.path.join(self.temporary_directory.name, "game.sqlite3"),
                "TEAM_TOKENS": {"test-green-token": "green"},
                "PLACE_SCORES": {"time-site": 120},
                "GAME_SESSION_ID": "fujisawa-test-1",
            }
        ).test_client()
        self.headers = {"Authorization": "Bearer test-green-token"}

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_team_state_includes_score_and_claimed_places(self):
        self.client.post(
            "/v1/actions",
            headers=self.headers,
            json={
                "action_id": "green-claim-0001",
                "game_session_id": "fujisawa-test-1",
                "type": "claim_place",
                "place_id": "time-site",
            },
        )

        response = self.client.get("/v1/team/state", headers=self.headers)

        self.assertEqual(200, response.status_code)
        self.assertEqual(120, response.get_json()["score"])
        self.assertEqual(["time-site"], response.get_json()["claimed_places"])


if __name__ == "__main__":
    unittest.main()
