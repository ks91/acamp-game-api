import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.api import create_app


class ActionsEndpointTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": os.path.join(self.temporary_directory.name, "game.sqlite3"),
                "TEAM_TOKENS": {"test-green-token": "green"},
                "PLACE_SCORES": {"time-site": 120},
            }
        ).test_client()
        self.headers = {"Authorization": "Bearer test-green-token"}
        self.claim = {
            "action_id": "green-claim-0001",
            "game_session_id": "fujisawa-test-1",
            "type": "claim_place",
            "place_id": "time-site",
        }

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_claim_place_awards_server_defined_points_only_once_per_team(self):
        first = self.client.post("/v1/actions", headers=self.headers, json=self.claim)
        second = self.client.post("/v1/actions", headers=self.headers, json=self.claim)

        self.assertEqual(201, first.status_code)
        self.assertEqual(
            {
                "action_id": "green-claim-0001",
                "claimed": True,
                "place_id": "time-site",
                "score_delta": 120,
                "team_score": 120,
            },
            first.get_json(),
        )
        self.assertEqual(200, second.status_code)
        self.assertEqual(
            {
                "action_id": "green-claim-0001",
                "claimed": False,
                "place_id": "time-site",
                "score_delta": 0,
                "team_score": 120,
            },
            second.get_json(),
        )
    def test_place_score_can_be_loaded_from_a_simple_environment_variable(self):
        with patch.dict(
            os.environ, {"ACAMP_GAME_PLACE_SCORE_TIME_SITE": "120"}, clear=False
        ):
            client = create_app(
                {
                    "TESTING": True,
                    "DATABASE_PATH": os.path.join(
                        self.temporary_directory.name, "environment.sqlite3"
                    ),
                    "TEAM_TOKENS": {"test-green-token": "green"},
                }
            ).test_client()

        response = client.post("/v1/actions", headers=self.headers, json=self.claim)

        self.assertEqual(201, response.status_code)
        self.assertEqual(120, response.get_json()["score_delta"])
    def test_claim_requires_latest_team_location_to_be_within_place_radius(self):
        client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": os.path.join(
                    self.temporary_directory.name, "location-gate.sqlite3"
                ),
                "TEAM_TOKENS": {"test-green-token": "green"},
                "PLACE_DEFINITIONS": {
                    "time-site": {
                        "latitude": 35.3387,
                        "longitude": 139.4888,
                        "radius_m": 40,
                        "points": 120,
                    }
                },
            }
        ).test_client()
        client.post(
            "/v1/location-samples",
            headers=self.headers,
            json={
                "team_id": "green",
                "device_id": "green-ipad",
                "client_time": "2026-09-20T10:00:00+09:00",
                "sample_id": "at-time-site",
                "latitude": 35.3387,
                "longitude": 139.4888,
                "accuracy_m": 18.5,
            },
        )

        response = client.post("/v1/actions", headers=self.headers, json=self.claim)

        self.assertEqual(201, response.status_code)
        self.assertTrue(response.get_json()["claimed"])
    def test_places_are_loaded_from_a_versioned_scenario_file(self):
        scenario_path = os.path.join(self.temporary_directory.name, "scenario.json")
        with open(scenario_path, "w", encoding="utf-8") as scenario_file:
            json.dump(
                {
                    "places": [
                        {
                            "id": "time-site",
                            "latitude": 35.3387,
                            "longitude": 139.4888,
                            "radius_m": 40,
                            "points": 120,
                        }
                    ]
                },
                scenario_file,
            )
        with patch.dict(os.environ, {"ACAMP_GAME_SCENARIO_PATH": scenario_path}):
            app = create_app(
                {"TESTING": True, "TEAM_TOKENS": {"test-green-token": "green"}}
            )

        self.assertEqual(120, app.config["PLACE_DEFINITIONS"]["time-site"]["points"])


if __name__ == "__main__":
    unittest.main()
