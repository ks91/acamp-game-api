import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.api import create_app


class AdminTeamModesTests(unittest.TestCase):
    def test_admin_can_batch_install_team_modes_into_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            registry_path = os.path.join(directory, "sessions.json")
            with open(registry_path, "w", encoding="utf-8") as handle:
                json.dump({"green": {"game_session_id": "old", "status": "test", "scenario": {"places": []}}}, handle)
            with patch.dict(os.environ, {"ACAMP_GAME_TEAM_SESSIONS_PATH": registry_path}):
                client = create_app({"TESTING": True, "ADMIN_TOKEN": "admin", "TEAM_SESSIONS": {"green": {"game_session_id": "old", "status": "test", "scenario": {"places": []}}}}).test_client()
                response = client.post("/v1/admin/team-modes", headers={"Authorization": "Bearer admin"}, json={"team_modes": {"green": {"center_test": {"game_session_id": "day3-center-test-green-1", "status": "test", "allow_team_restart": True, "scenario": {"id": "day3-center-test-green-1", "name": "Green test", "places": []}}}}})
            self.assertEqual(200, response.status_code)
            with open(registry_path, encoding="utf-8") as handle:
                saved = json.load(handle)
            self.assertIn("center_test", saved["green"]["modes"])
            self.assertEqual("day3-center-test-green-1", saved["green"]["modes"]["center_test"]["game_session_id"])

    def test_admin_updates_only_named_mode_place_radii_without_exposing_or_replacing_scenario(self):
        scenario = {
            "id": "green-city-1",
            "name": "Green city route",
            "claim_policy": "territory",
            "places": [
                {"id": "library", "name": "Library", "latitude": 35.1, "longitude": 139.2, "radius_m": 25, "points": 5},
                {"id": "station", "name": "Station", "latitude": 35.3, "longitude": 139.4, "radius_m": 30, "points": 10},
            ],
        }
        registry = {"green": {"default_mode": "tokyo", "modes": {"tokyo": {
            "game_session_id": "green-tokyo-1", "status": "test", "scenario": scenario,
        }}}}
        with tempfile.TemporaryDirectory() as directory:
            registry_path = os.path.join(directory, "sessions.json")
            with open(registry_path, "w", encoding="utf-8") as handle:
                json.dump(registry, handle)
            with patch.dict(os.environ, {"ACAMP_GAME_TEAM_SESSIONS_PATH": registry_path}):
                client = create_app({"TESTING": True, "ADMIN_TOKEN": "admin", "TEAM_SESSIONS": json.loads(json.dumps(registry))}).test_client()
                response = client.post(
                    "/v1/admin/team-mode-radii",
                    headers={"Authorization": "Bearer admin"},
                    json={"team_id": "green", "mode": "tokyo", "radii": {"library": 40, "station": 55}},
                )
            with open(registry_path, encoding="utf-8") as handle:
                saved = json.load(handle)

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {"updated": True, "team_id": "green", "mode": "tokyo", "radii": {"library": 40, "station": 55}},
            response.get_json(),
        )
        self.assertNotIn("latitude", json.dumps(response.get_json()))
        self.assertNotIn("longitude", json.dumps(response.get_json()))
        self.assertEqual(40, saved["green"]["modes"]["tokyo"]["scenario"]["places"][0]["radius_m"])
        self.assertEqual(55, saved["green"]["modes"]["tokyo"]["scenario"]["places"][1]["radius_m"])
        self.assertEqual(35.1, saved["green"]["modes"]["tokyo"]["scenario"]["places"][0]["latitude"])
        self.assertEqual(139.2, saved["green"]["modes"]["tokyo"]["scenario"]["places"][0]["longitude"])
        self.assertEqual("territory", saved["green"]["modes"]["tokyo"]["scenario"]["claim_policy"])
        self.assertEqual("green-tokyo-1", saved["green"]["modes"]["tokyo"]["game_session_id"])
        self.assertEqual(40, client.application.config["TEAM_SESSIONS"]["green"]["modes"]["tokyo"]["scenario"]["places"][0]["radius_m"])

    def test_radius_update_rejects_unknown_team_mode_or_place_without_persisting_changes(self):
        registry = {"green": {"modes": {"tokyo": {"scenario": {"places": [
            {"id": "library", "latitude": 35.1, "longitude": 139.2, "radius_m": 25},
        ]}}}}}
        with tempfile.TemporaryDirectory() as directory:
            registry_path = os.path.join(directory, "sessions.json")
            with open(registry_path, "w", encoding="utf-8") as handle:
                json.dump(registry, handle)
            with open(registry_path, encoding="utf-8") as handle:
                original = handle.read()
            with patch.dict(os.environ, {"ACAMP_GAME_TEAM_SESSIONS_PATH": registry_path}):
                client = create_app({"TESTING": True, "ADMIN_TOKEN": "admin", "TEAM_SESSIONS": json.loads(json.dumps(registry))}).test_client()
                for payload in (
                    {"team_id": "blue", "mode": "tokyo", "radii": {"library": 40}},
                    {"team_id": "green", "mode": "center_test", "radii": {"library": 40}},
                    {"team_id": "green", "mode": "tokyo", "radii": {"museum": 40}},
                ):
                    response = client.post(
                        "/v1/admin/team-mode-radii",
                        headers={"Authorization": "Bearer admin"},
                        json=payload,
                    )
                    self.assertEqual(404, response.status_code)
            with open(registry_path, encoding="utf-8") as handle:
                self.assertEqual(original, handle.read())

    def test_radius_update_requires_admin_and_positive_integer_radii(self):
        registry = {"green": {"modes": {"tokyo": {"scenario": {"places": [
            {"id": "library", "latitude": 35.1, "longitude": 139.2, "radius_m": 25},
        ]}}}}}
        with tempfile.TemporaryDirectory() as directory:
            registry_path = os.path.join(directory, "sessions.json")
            with open(registry_path, "w", encoding="utf-8") as handle:
                json.dump(registry, handle)
            with patch.dict(os.environ, {"ACAMP_GAME_TEAM_SESSIONS_PATH": registry_path}):
                client = create_app({"TESTING": True, "ADMIN_TOKEN": "admin", "TEAM_SESSIONS": json.loads(json.dumps(registry))}).test_client()
                unauthenticated = client.post(
                    "/v1/admin/team-mode-radii",
                    json={"team_id": "green", "mode": "tokyo", "radii": {"library": 40}},
                )
                invalid = client.post(
                    "/v1/admin/team-mode-radii",
                    headers={"Authorization": "Bearer admin"},
                    json={"team_id": "green", "mode": "tokyo", "radii": {"library": True}},
                )

        self.assertEqual(401, unauthenticated.status_code)
        self.assertEqual(400, invalid.status_code)


if __name__ == "__main__":
    unittest.main()
