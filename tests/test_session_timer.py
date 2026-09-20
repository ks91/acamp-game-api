import os
import tempfile
import unittest
from datetime import datetime, timezone

from app.session_store import SessionStore


class SessionTimerTests(unittest.TestCase):
    def test_remaining_seconds_counts_only_live_periods(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(os.path.join(directory, "game.sqlite3"))
            store.set_status_at("green-1", "live", "start", "2026-09-20T00:00:00+00:00")
            store.set_status_at("green-1", "paused", "break", "2026-09-20T00:00:30+00:00")
            store.set_status_at("green-1", "live", "resume", "2026-09-20T00:01:00+00:00")

            remaining = store.remaining_seconds(
                "green-1", 120, now=datetime(2026, 9, 20, 0, 1, 20, tzinfo=timezone.utc)
            )

            self.assertEqual(70, remaining)


if __name__ == "__main__":
    unittest.main()
