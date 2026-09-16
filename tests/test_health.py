import unittest

from app.api import create_app


class HealthEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app({"TESTING": True}).test_client()

    def test_health_reports_service_ready(self):
        response = self.client.get("/health")

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "api_version": "v1",
                "service": "acamp-game-api",
                "status": "ok",
            },
            response.get_json(),
        )


if __name__ == "__main__":
    unittest.main()
