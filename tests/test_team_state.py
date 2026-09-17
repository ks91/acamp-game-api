import os
import tempfile
import unittest

from app.api import create_app


class TeamStateEndpointTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": os.path.join(self.temporary_directory.name, "game.sqlite3"),
                "TEAM_TOKENS": {"test-green-token": "green"},
            }
        ).test_client()
        self.headers = {"Authorization": "Bearer test-green-token"}

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_team_state_returns_only_the_authorized_teams_latest_location(self):
        self.client.post(
            "/v1/location-samples",
            headers=self.headers,
            json={
                "team_id": "green",
                "device_id": "green-ipad",
                "client_time": "2026-09-20T10:00:00+09:00",
                "sample_id": "green-0001",
                "latitude": 35.3387,
                "longitude": 139.4888,
                "accuracy_m": 18.5,
            },
        )

        response = self.client.get("/v1/team/state", headers=self.headers)

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "team_id": "green",
                "location_event_count": 1,
                "latest_location": {
                    "event_id": 1,
                    "client_time": "2026-09-20T10:00:00+09:00",
                    "latitude": 35.3387,
                    "longitude": 139.4888,
                    "accuracy_m": 18.5,
                },
            },
            response.get_json(),
        )


if __name__ == "__main__":
    unittest.main()
