import json
import os
import sqlite3
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

    def test_development_device_cannot_claim_for_a_team_with_a_play_device(self):
        client = create_app({"TESTING": True, "DATABASE_PATH": os.path.join(self.temporary_directory.name, "device.sqlite3"), "TEAM_TOKENS": {"test-green-token": "green"}, "TEAM_SESSIONS": {"green": {"game_session_id": "green-1", "status": "test", "play_device_id": "green-ipad", "development_device_id": "green-wifi-ipad", "scenario": {"id": "green-1", "name": "Green", "places": []}}}}).test_client()
        claim = dict(self.claim, device_id="green-wifi-ipad")
        response = client.post("/v1/actions", headers=self.headers, json=claim)
        self.assertEqual(403, response.status_code)
        self.assertEqual("device is not allowed to claim", response.get_json()["error"])

    def test_claim_rejects_a_stale_location_sample(self):
        database_path = os.path.join(self.temporary_directory.name, "stale.sqlite3")
        client = create_app({"TESTING": True, "DATABASE_PATH": database_path, "TEAM_TOKENS": {"test-green-token": "green"}, "PLACE_DEFINITIONS": {"time-site": {"latitude": 35.0, "longitude": 139.0, "radius_m": 40, "points": 120}}, "MAX_LOCATION_AGE_SECONDS": 300}).test_client()
        client.post("/v1/location-samples", headers=self.headers, json={"sample_id": "stale-sample", "team_id": "green", "device_id": "green-ipad", "client_time": "2026-09-17T10:00:00+09:00", "latitude": 35.0, "longitude": 139.0, "accuracy_m": 5})
        with sqlite3.connect(database_path) as connection:
            connection.execute("UPDATE location_events SET received_at = '2000-01-01 00:00:00'")
        response = client.post("/v1/actions", headers=self.headers, json=self.claim)
        self.assertEqual(409, response.status_code)
        self.assertEqual("location sample is too old", response.get_json()["error"])

    def test_paused_game_session_rejects_place_claims(self):
        client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": os.path.join(
                    self.temporary_directory.name, "paused-session.sqlite3"
                ),
                "TEAM_TOKENS": {"test-green-token": "green"},
                "PLACE_SCORES": {"time-site": 120},
                "GAME_STATUS": "paused",
            }
        ).test_client()

        response = client.post("/v1/actions", headers=self.headers, json=self.claim)

        self.assertEqual(409, response.status_code)
        self.assertEqual("game session is paused", response.get_json()["error"])

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
    def test_claim_rejects_location_fix_less_accurate_than_the_place_radius(self):
        client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": os.path.join(
                    self.temporary_directory.name, "accuracy-gate.sqlite3"
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
                "sample_id": "imprecise-fix",
                "latitude": 35.3387,
                "longitude": 139.4888,
                "accuracy_m": 41,
            },
        )

        response = client.post("/v1/actions", headers=self.headers, json=self.claim)

        self.assertEqual(409, response.status_code)
        self.assertEqual("location accuracy is too low", response.get_json()["error"])

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
    def test_claiming_a_place_transfers_the_flag_between_teams(self):
        client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": os.path.join(self.temporary_directory.name, "territory.sqlite3"),
                "TEAM_TOKENS": {"green-token": "green", "blue-token": "blue"},
                "PLACE_SCORES": {"cat-point": 30},
                "GAME_SESSION_ID": "territory-1",
            }
        ).test_client()
        claim = {
            "action_id": "claim-1",
            "game_session_id": "territory-1",
            "type": "claim_place",
            "place_id": "cat-point",
        }

        first = client.post("/v1/actions", headers={"Authorization": "Bearer green-token"}, json=claim)
        second = client.post("/v1/actions", headers={"Authorization": "Bearer blue-token"}, json=dict(claim, action_id="claim-2"))

        self.assertEqual(201, first.status_code)
        self.assertEqual(201, second.status_code)
        self.assertFalse(first.get_json()["transferred"])
        self.assertTrue(second.get_json()["transferred"])
        self.assertEqual(30, second.get_json()["score_delta"])


if __name__ == "__main__":
    unittest.main()
