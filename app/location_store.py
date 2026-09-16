import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class LocationSample:
    team_id: str
    device_id: str
    client_time: str
    latitude: float
    longitude: float
    accuracy_m: float


class LocationStore:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def initialize(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS location_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    def add(self, sample: LocationSample) -> int:
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO location_events
                    (team_id, device_id, client_time, latitude, longitude, accuracy_m)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    sample.team_id,
                    sample.device_id,
                    sample.client_time,
                    sample.latitude,
                    sample.longitude,
                    sample.accuracy_m,
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("location event insert did not return an id")
            return cursor.lastrowid
