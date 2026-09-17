import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class LocationSample:
    sample_id: str
    team_id: str
    device_id: str
    client_time: str
    latitude: float
    longitude: float
    accuracy_m: float


@dataclass(frozen=True)
class LocationInsertResult:
    event_id: int
    duplicate: bool


class LocationStore:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def initialize(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS location_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_id TEXT,
                    team_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    client_time TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    accuracy_m REAL NOT NULL,
                    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(location_events)")
            }
            if "sample_id" not in columns:
                connection.execute("ALTER TABLE location_events ADD COLUMN sample_id TEXT")
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS unique_location_sample
                ON location_events(team_id, device_id, sample_id)
                WHERE sample_id IS NOT NULL
                """
            )

    def team_state(self, team_id: str) -> dict:
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM location_events WHERE team_id = ?", (team_id,)
            ).fetchone()[0]
            latest = connection.execute(
                """
                SELECT event_id, client_time, latitude, longitude, accuracy_m, received_at
                FROM location_events
                WHERE team_id = ?
                ORDER BY event_id DESC
                LIMIT 1
                """,
                (team_id,),
            ).fetchone()

        return {
            "team_id": team_id,
            "location_event_count": count,
            "latest_location": None
            if latest is None
            else {
                "event_id": latest[0],
                "client_time": latest[1],
                "latitude": latest[2],
                "longitude": latest[3],
                "accuracy_m": latest[4],
                "received_at": latest[5],
            },
        }

    def add(self, sample: LocationSample) -> LocationInsertResult:
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO location_events
                    (sample_id, team_id, device_id, client_time, latitude, longitude, accuracy_m)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sample.sample_id,
                    sample.team_id,
                    sample.device_id,
                    sample.client_time,
                    sample.latitude,
                    sample.longitude,
                    sample.accuracy_m,
                ),
            )
            if cursor.rowcount == 1:
                if cursor.lastrowid is None:
                    raise RuntimeError("location event insert did not return an id")
                return LocationInsertResult(event_id=cursor.lastrowid, duplicate=False)

            row = connection.execute(
                """
                SELECT event_id FROM location_events
                WHERE team_id = ? AND device_id = ? AND sample_id = ?
                """,
                (sample.team_id, sample.device_id, sample.sample_id),
            ).fetchone()
            if row is None:
                raise RuntimeError("duplicate location event could not be found")
            return LocationInsertResult(event_id=row[0], duplicate=True)
