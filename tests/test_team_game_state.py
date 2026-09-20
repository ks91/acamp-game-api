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
    def test_game_state_returns_public_territories_and_only_own_home(self):
        client = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": os.path.join(self.temporary_directory.name, "public-state.sqlite3"),
                "TEAM_TOKENS": {"green-token": "green", "blue-token": "blue"},
                "GAME_SESSION_ID": "territory-1",
                "TEAM_SESSIONS": {
                    "green": {"game_session_id": "territory-1", "status": "test", "home_place_id": "green-home", "scenario": {"id": "territory-1", "name": "陣地戦", "places": []}},
                    "blue": {"game_session_id": "territory-1", "status": "test", "home_place_id": "blue-home", "scenario": {"id": "territory-1", "name": "陣地戦", "places": []}},
                },
                "PLACE_SCORES": {"green-point": 40, "blue-point": 80},
            }
        ).test_client()
        claim = {"game_session_id": "territory-1", "type": "claim_place", "place_id": "green-point", "device_id": "green-ipad"}
        client.post("/v1/actions", headers={"Authorization": "Bearer green-token"}, json=dict(claim, action_id="green-1"))
        claim["place_id"] = "blue-point"
        client.post("/v1/actions", headers={"Authorization": "Bearer blue-token"}, json=dict(claim, action_id="blue-1"))

        response = client.get("/v1/game/state", headers={"Authorization": "Bearer green-token"})

        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertEqual("green-home", payload["home_place_id"])
        self.assertEqual(40, payload["score"])
        self.assertEqual(["green-point"], payload["claimed_places"])
        self.assertEqual({"green-point", "blue-point"}, {item["place_id"] for item in payload["territories"]})
        self.assertTrue(all("is_home" not in item for item in payload["territories"]))


if __name__ == "__main__":
    unittest.main()
