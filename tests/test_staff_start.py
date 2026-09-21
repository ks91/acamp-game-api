import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location(
    "staff_start", Path(__file__).parents[1] / "scripts" / "staff_start.py"
)
staff_start = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(staff_start)


class StaffStartTests(unittest.TestCase):
    def test_start_resets_exact_team_mode_then_declares_it_live(self):
        calls = []

        def request(path, method="GET", payload=None):
            calls.append((path, method, payload))
            return {"game_session_id": payload["game_session_id"], "status": payload.get("status", "")}

        announcement = staff_start.start_team_mode(
            {"green": {"modes": {"center_test": {"game_session_id": "day3-center-test-green-1"}}}},
            "green",
            "center_test",
            "スタッフが開始",
            request,
        )

        self.assertEqual("/v1/admin/session/reset", calls[0][0])
        self.assertEqual("day3-center-test-green-1", calls[0][2]["game_session_id"])
        self.assertEqual("/v1/admin/session/status", calls[1][0])
        self.assertEqual("live", calls[1][2]["status"])
        self.assertIn("グリーン", announcement)
        self.assertIn("センター棟テスト", announcement)


if __name__ == "__main__":
    unittest.main()
