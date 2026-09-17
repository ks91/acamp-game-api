import os
import tempfile
import unittest

from app.api import create_app


class AdminOverviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": os.path.join(self.temporary_directory.name, "game.sqlite3"),
                "ADMIN_TOKEN": "admin-test-token",
                "TEAM_TOKENS": {"green-token": "green", "pink-token": "pink"},
                "TEAM_SESSIONS": {
                    "green": {
                        "game_session_id": "green-test",
                        "status": "test",
                        "scenario": {"id": "green-test", "name": "Green", "places": []},
                    },
                    "pink": {
                        "game_session_id": "pink-test",
                        "status": "paused",
                        "scenario": {"id": "pink-test", "name": "Pink", "places": []},
                    },
                },
            }
        ).test_client()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_admin_can_pause_a_session_with_a_reason(self):
        response = self.client.post(
            "/v1/admin/session/status",
            headers={"Authorization": "Bearer admin-test-token"},
            json={
                "game_session_id": "green-test",
                "status": "paused",
                "reason": "雨天のため",
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual("paused", response.get_json()["status"])
        self.assertEqual("雨天のため", response.get_json()["reason"])

    def test_overview_requires_admin_token(self):
        response = self.client.get("/v1/admin/overview")
        self.assertEqual(401, response.status_code)

    def test_overview_lists_each_team_session_and_operational_state(self):
        response = self.client.get(
            "/v1/admin/overview", headers={"Authorization": "Bearer admin-test-token"}
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            [
                {
                    "team_id": "green",
                    "game_session_id": "green-test",
                    "status": "test",
                    "score": 0,
                    "claimed_places": [],
                    "location_event_count": 0,
                    "latest_location_time": None,
                    "latest_location_accuracy_m": None,
                },
                {
                    "team_id": "pink",
                    "game_session_id": "pink-test",
                    "status": "paused",
                    "score": 0,
                    "claimed_places": [],
                    "location_event_count": 0,
                    "latest_location_time": None,
                    "latest_location_accuracy_m": None,
                },
            ],
            response.get_json()["teams"],
        )


if __name__ == "__main__":
    unittest.main()
