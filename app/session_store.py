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
        return self.set_status_at(
            game_session_id, status, reason, datetime.now(timezone.utc).isoformat()
        )

    def set_status_at(self, game_session_id, status, reason, occurred_at):
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "INSERT INTO session_status_events (game_session_id, status, reason, occurred_at) VALUES (?, ?, ?, ?)",
                (game_session_id, status, reason, occurred_at),
            )
        return {"game_session_id": game_session_id, "status": status, "reason": reason, "occurred_at": occurred_at}

    def remaining_seconds(self, game_session_id, duration_seconds, now=None):
        self.initialize()
        now = now or datetime.now(timezone.utc)
        with sqlite3.connect(self.database_path) as connection:
            events = connection.execute(
                "SELECT status, occurred_at FROM session_status_events WHERE game_session_id = ? ORDER BY event_id",
                (game_session_id,),
            ).fetchall()
        elapsed = 0.0
        for index, (status, occurred_at) in enumerate(events):
            if status != "live":
                continue
            started = datetime.fromisoformat(occurred_at)
            ended = (
                datetime.fromisoformat(events[index + 1][1])
                if index + 1 < len(events)
                else now
            )
            elapsed += max(0.0, (ended - started).total_seconds())
        return max(0, int(duration_seconds - elapsed))

    def status_for(self, game_session_id, default_status):
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT status FROM session_status_events WHERE game_session_id = ? ORDER BY event_id DESC LIMIT 1",
                (game_session_id,),
            ).fetchone()
        return row[0] if row else default_status
