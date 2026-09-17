import sqlite3
from datetime import datetime, timezone


class SessionStore:
    def __init__(self, database_path):
        self.database_path = database_path

    def initialize(self):
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_status_events (
                    event_id INTEGER PRIMARY KEY,
                    game_session_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                )
                """
            )

    def set_status(self, game_session_id, status, reason):
        self.initialize()
        occurred_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "INSERT INTO session_status_events (game_session_id, status, reason, occurred_at) VALUES (?, ?, ?, ?)",
                (game_session_id, status, reason, occurred_at),
            )
        return {"game_session_id": game_session_id, "status": status, "reason": reason, "occurred_at": occurred_at}

    def status_for(self, game_session_id, default_status):
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT status FROM session_status_events WHERE game_session_id = ? ORDER BY event_id DESC LIMIT 1",
                (game_session_id,),
            ).fetchone()
        return row[0] if row else default_status
