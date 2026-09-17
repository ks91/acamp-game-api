import unittest

from app.api import create_app


class TeamSessionEndpointTests(unittest.TestCase):
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
