import unittest

from app.api import create_app


class GameDefinitionEndpointTests(unittest.TestCase):
    def test_authenticated_team_receives_active_scenario_definition(self):
        client = create_app(
            {
                "TESTING": True,
                "TEAM_TOKENS": {"test-green-token": "green"},
                "SCENARIO": {
                    "id": "fujisawa-test-1",
                    "name": "藤沢テスト版",
                    "places": [
                        {"id": "time-site", "name": "時間の結節点", "points": 120}
                    ],
                },
            }
        ).test_client()

        response = client.get(
            "/v1/game/definition",
            headers={"Authorization": "Bearer test-green-token"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual("fujisawa-test-1", response.get_json()["id"])
        self.assertEqual("time-site", response.get_json()["places"][0]["id"])


if __name__ == "__main__":
    unittest.main()
