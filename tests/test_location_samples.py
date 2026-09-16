import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from app.api import create_app


class LocationSamplesEndpointTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temporary_directory.name, "game.sqlite3")
        self.client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": self.database_path,
                "TEAM_TOKENS": {"test-green-token": "green"},
            }
        ).test_client()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_authorized_team_can_store_a_location_sample(self):
        response = self.client.post(
            "/v1/location-samples",
            headers={"Authorization": "Bearer test-green-token"},
            json={
                "team_id": "green",
                "device_id": "green-ipad",
                "client_time": "2026-09-20T10:00:00+09:00",
                "latitude": 35.3387,
                "longitude": 139.4888,
                "accuracy_m": 18.5,
            },
        )

        self.assertEqual(201, response.status_code)
        self.assertEqual(
            {"accepted": True, "event_id": 1},
            response.get_json(),
        )
        with sqlite3.connect(self.database_path) as connection:
            stored = connection.execute(
                "SELECT team_id, latitude, longitude, accuracy_m FROM location_events"
            ).fetchone()
        self.assertEqual(("green", 35.3387, 139.4888, 18.5), stored)

    def test_token_cannot_send_a_sample_for_another_team(self):
        response = self.client.post(
            "/v1/location-samples",
            headers={"Authorization": "Bearer test-green-token"},
            json={
                "team_id": "pink",
                "device_id": "green-ipad",
                "client_time": "2026-09-20T10:00:00+09:00",
                "latitude": 35.3387,
                "longitude": 139.4888,
                "accuracy_m": 18.5,
            },
        )

        self.assertEqual(403, response.status_code)
        self.assertEqual(
            {"error": "team token does not match team_id"},
            response.get_json(),
        )
    def test_individual_team_token_environment_variable_takes_priority_over_json(self):
        with patch.dict(
            os.environ,
            {
                "ACAMP_GAME_TEAM_TOKEN_GREEN": "test-green-token",
                "ACAMP_GAME_TEAM_TOKENS_JSON": "malformed JSON must not prevent startup",
            },
            clear=False,
        ):
            client = create_app(
                {"TESTING": True, "DATABASE_PATH": self.database_path}
            ).test_client()

        response = client.post(
            "/v1/location-samples",
            headers={"Authorization": "Bearer test-green-token"},
            json={
                "team_id": "green",
                "device_id": "green-ipad",
                "client_time": "2026-09-20T10:00:00+09:00",
                "latitude": 35.3387,
                "longitude": 139.4888,
                "accuracy_m": 18.5,
            },
        )

        self.assertEqual(201, response.status_code)

    def test_team_tokens_can_be_loaded_from_an_environment_variable(self):
        with patch.dict(
            os.environ,
            {"ACAMP_GAME_TEAM_TOKENS_JSON": '{"green": "test-green-token"}'},
            clear=False,
        ):
            client = create_app(
                {"TESTING": True, "DATABASE_PATH": self.database_path}
            ).test_client()

        response = client.post(
            "/v1/location-samples",
            headers={"Authorization": "Bearer test-green-token"},
            json={
                "team_id": "green",
                "device_id": "green-ipad",
                "client_time": "2026-09-20T10:00:00+09:00",
                "latitude": 35.3387,
                "longitude": 139.4888,
                "accuracy_m": 18.5,
            },
        )

        self.assertEqual(201, response.status_code)


if __name__ == "__main__":
    unittest.main()
