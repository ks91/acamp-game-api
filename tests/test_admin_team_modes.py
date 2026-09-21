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
            saved = json.load(open(registry_path, encoding="utf-8"))
            self.assertIn("center_test", saved["green"]["modes"])
            self.assertEqual("day3-center-test-green-1", saved["green"]["modes"]["center_test"]["game_session_id"])


if __name__ == "__main__":
    unittest.main()
