import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.api import _team_sessions_from_environment, create_app


class TeamSessionEndpointTests(unittest.TestCase):
    def test_registry_loads_a_team_scenario_from_a_relative_file_path(self):
        with tempfile.TemporaryDirectory() as directory:
            scenario_path = os.path.join(directory, "green.json")
            registry_path = os.path.join(directory, "sessions.json")
            with open(scenario_path, "w", encoding="utf-8") as handle:
                json.dump({"id": "green-1", "name": "Green", "places": []}, handle)
            with open(registry_path, "w", encoding="utf-8") as handle:
                json.dump({"green": {"game_session_id": "green-1", "status": "test", "scenario_path": "green.json"}}, handle)
            with patch.dict(os.environ, {"ACAMP_GAME_TEAM_SESSIONS_PATH": registry_path}):
                sessions = _team_sessions_from_environment()
        self.assertEqual("Green", sessions["green"]["scenario"]["name"])

    def test_team_receives_its_assigned_session_scenario(self):
        client = create_app(
            {
                "TESTING": True,
                "TEAM_TOKENS": {"green-token": "green"},
                "TEAM_SESSIONS": {
                    "green": {
                        "game_session_id": "prototype-green-1",
                        "status": "test",
                        "scenario": {
                            "id": "prototype-green-1",
                            "name": "グリーン班試作",
                            "places": [],
                        },
                    }
                },
            }
        ).test_client()

        response = client.get(
            "/v1/game/definition", headers={"Authorization": "Bearer green-token"}
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual("prototype-green-1", response.get_json()["id"])
        self.assertEqual("グリーン班試作", response.get_json()["name"])


if __name__ == "__main__":
    unittest.main()
