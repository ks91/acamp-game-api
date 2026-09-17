from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class ClaimResult:
    claimed: bool
    score_delta: int
    team_score: int


class PersistentGameStore:
    """Game claims stored in the API's SQLite database."""

    def __init__(self, database_path: str):
        self.database_path = database_path

    def initialize(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS spot_claims (
                    game_session_id TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    place_id TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    action_id TEXT NOT NULL,
                    PRIMARY KEY (game_session_id, team_id, place_id)
                )
                """
            )

    def team_summary(self, game_session_id: str, team_id: str) -> dict:
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            score = connection.execute(
                "SELECT COALESCE(SUM(score), 0) FROM spot_claims WHERE game_session_id = ? AND team_id = ?",
                (game_session_id, team_id),
            ).fetchone()[0]
            claimed_places = [
                row[0]
                for row in connection.execute(
                    "SELECT place_id FROM spot_claims WHERE game_session_id = ? AND team_id = ? ORDER BY rowid",
                    (game_session_id, team_id),
                )
            ]
        return {"score": score, "claimed_places": claimed_places}

    def claim_place(
        self,
        *,
        game_session_id: str,
        team_id: str,
        place_id: str,
        score: int,
        action_id: str,
    ) -> ClaimResult:
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO spot_claims
                    (game_session_id, team_id, place_id, score, action_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (game_session_id, team_id, place_id, score, action_id),
            )
            team_score = connection.execute(
                """
                SELECT COALESCE(SUM(score), 0)
                FROM spot_claims
                WHERE game_session_id = ? AND team_id = ?
                """,
                (game_session_id, team_id),
            ).fetchone()[0]
        return ClaimResult(
            claimed=cursor.rowcount == 1,
            score_delta=score if cursor.rowcount == 1 else 0,
            team_score=team_score,
        )


class GameStore:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS spot_claims (
                game_session_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                place_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                occurred_at TEXT NOT NULL,
                PRIMARY KEY (game_session_id, team_id, place_id)
            )
            """
        )
        self.connection.commit()

    def claim_place(
        self,
        *,
        game_session_id: str,
        team_id: str,
        place_id: str,
        score: int,
        occurred_at: str,
    ) -> ClaimResult:
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO spot_claims
                    (game_session_id, team_id, place_id, score, occurred_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (game_session_id, team_id, place_id, score, occurred_at),
            )
            team_score = self.connection.execute(
                """
                SELECT COALESCE(SUM(score), 0)
                FROM spot_claims
                WHERE game_session_id = ? AND team_id = ?
                """,
                (game_session_id, team_id),
            ).fetchone()[0]

        return ClaimResult(
            claimed=cursor.rowcount == 1,
            score_delta=score if cursor.rowcount == 1 else 0,
            team_score=team_score,
        )
