from __future__ import annotations

from dataclasses import dataclass
import random
import sqlite3


@dataclass(frozen=True)
class ClaimResult:
    claimed: bool
    score_delta: int
    team_score: int
    transferred: bool = False
    home_place_id: str | None = None
    replayed: bool = False


class _TerritoryStoreMixin:
    def _initialize_territories(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_claims (
                game_session_id TEXT NOT NULL,
                place_id TEXT NOT NULL,
                owner_team_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                occurred_at TEXT NOT NULL,
                PRIMARY KEY (game_session_id, place_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS home_states (
                game_session_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                home_place_id TEXT NOT NULL,
                PRIMARY KEY (game_session_id, team_id)
            )
            """
        )

    @staticmethod
    def _migrate_legacy_claims(
        connection: sqlite3.Connection, occurred_at_column: str
    ) -> None:
        if occurred_at_column not in {"action_id", "occurred_at"}:
            raise ValueError("unsupported legacy occurrence column")
        connection.execute(
            f"""
            INSERT OR IGNORE INTO territory_claims
                (game_session_id, place_id, owner_team_id, score, occurred_at)
            SELECT legacy.game_session_id, legacy.place_id, legacy.team_id,
                   legacy.score, legacy.{occurred_at_column}
            FROM spot_claims AS legacy
            WHERE NOT EXISTS (
                SELECT 1 FROM spot_claims AS newer
                WHERE newer.game_session_id = legacy.game_session_id
                  AND newer.place_id = legacy.place_id
                  AND newer.rowid > legacy.rowid
            )
            """
        )

    @staticmethod
    def _set_home_if_missing(connection, game_session_id, team_id, place_id) -> None:
        connection.execute(
            """
            INSERT OR IGNORE INTO home_states (game_session_id, team_id, home_place_id)
            VALUES (?, ?, ?)
            """,
            (game_session_id, team_id, place_id),
        )

    @staticmethod
    def _team_score(connection, game_session_id: str, team_id: str) -> int:
        return connection.execute(
            """
            SELECT COALESCE(SUM(score), 0) FROM territory_claims
            WHERE game_session_id = ? AND owner_team_id = ?
            """,
            (game_session_id, team_id),
        ).fetchone()[0]

    @staticmethod
    def _relocate_home(connection, game_session_id: str, team_id: str) -> str | None:
        candidates = connection.execute(
            """
            SELECT place_id, score FROM territory_claims
            WHERE game_session_id = ? AND owner_team_id = ?
            ORDER BY score DESC, place_id
            """,
            (game_session_id, team_id),
        ).fetchall()
        if not candidates:
            connection.execute(
                "DELETE FROM home_states WHERE game_session_id = ? AND team_id = ?",
                (game_session_id, team_id),
            )
            return None
        highest_score = candidates[0][1]
        highest = [place_id for place_id, score in candidates if score == highest_score]
        home_place_id = random.choice(highest)
        connection.execute(
            """
            INSERT INTO home_states (game_session_id, team_id, home_place_id)
            VALUES (?, ?, ?)
            ON CONFLICT(game_session_id, team_id)
            DO UPDATE SET home_place_id = excluded.home_place_id
            """,
            (game_session_id, team_id, home_place_id),
        )
        return home_place_id

    @staticmethod
    def _claim_with_connection(connection, *, game_session_id, team_id, place_id, score, occurred_at):
        existing = connection.execute(
            """
            SELECT owner_team_id FROM territory_claims
            WHERE game_session_id = ? AND place_id = ?
            """,
            (game_session_id, place_id),
        ).fetchone()
        if existing and existing[0] == team_id:
            return ClaimResult(
                claimed=False,
                score_delta=0,
                team_score=_TerritoryStoreMixin._team_score(connection, game_session_id, team_id),
            )

        transferred = existing is not None
        previous_owner = existing[0] if existing else None
        connection.execute(
            """
            INSERT INTO territory_claims
                (game_session_id, place_id, owner_team_id, score, occurred_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(game_session_id, place_id)
            DO UPDATE SET owner_team_id = excluded.owner_team_id,
                          score = excluded.score,
                          occurred_at = excluded.occurred_at
            """,
            (game_session_id, place_id, team_id, score, occurred_at),
        )
        if previous_owner:
            home = connection.execute(
                """
                SELECT home_place_id FROM home_states
                WHERE game_session_id = ? AND team_id = ? AND home_place_id = ?
                """,
                (game_session_id, previous_owner, place_id),
            ).fetchone()
            if home:
                _TerritoryStoreMixin._relocate_home(
                    connection, game_session_id, previous_owner
                )
        return ClaimResult(
            claimed=True,
            score_delta=score,
            team_score=_TerritoryStoreMixin._team_score(connection, game_session_id, team_id),
            transferred=transferred,
        )


class PersistentGameStore(_TerritoryStoreMixin):
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
            self._initialize_territories(connection)
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS territory_action_results (
                    game_session_id TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    place_id TEXT NOT NULL,
                    claimed INTEGER NOT NULL,
                    score_delta INTEGER NOT NULL,
                    team_score INTEGER NOT NULL,
                    transferred INTEGER NOT NULL,
                    home_place_id TEXT,
                    PRIMARY KEY (game_session_id, team_id, action_id)
                )
                """
            )
            self._migrate_legacy_claims(connection, "action_id")

    def team_summary(self, game_session_id: str, team_id: str) -> dict:
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            claimed = connection.execute(
                "SELECT COUNT(*) FROM territory_claims WHERE game_session_id = ?",
                (game_session_id,),
            ).fetchone()[0]
            if claimed == 0:
                score = connection.execute(
                    "SELECT COALESCE(SUM(score), 0) FROM spot_claims WHERE game_session_id = ? AND team_id = ?",
                    (game_session_id, team_id),
                ).fetchone()[0]
                claimed_places = [
                    row[0] for row in connection.execute(
                        "SELECT place_id FROM spot_claims WHERE game_session_id = ? AND team_id = ? ORDER BY rowid",
                        (game_session_id, team_id),
                    )
                ]
            else:
                score = self._team_score(connection, game_session_id, team_id)
                claimed_places = [
                    row[0] for row in connection.execute(
                        """
                        SELECT place_id FROM territory_claims
                        WHERE game_session_id = ? AND owner_team_id = ? ORDER BY rowid
                        """,
                        (game_session_id, team_id),
                    )
                ]
            home = connection.execute(
                "SELECT home_place_id FROM home_states WHERE game_session_id = ? AND team_id = ?",
                (game_session_id, team_id),
            ).fetchone()
        return {
            "score": score,
            "claimed_places": claimed_places,
            "home_place_id": home[0] if home else None,
        }

    def public_state(self, game_session_id: str, team_id: str) -> dict:
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            territories = [
                {"place_id": row[0], "owner": row[1], "points": row[2]}
                for row in connection.execute(
                    """
                    SELECT place_id, owner_team_id, score FROM territory_claims
                    WHERE game_session_id = ? ORDER BY place_id
                    """,
                    (game_session_id,),
                )
            ]
            home = connection.execute(
                "SELECT home_place_id FROM home_states WHERE game_session_id = ? AND team_id = ?",
                (game_session_id, team_id),
            ).fetchone()
            ranking = [
                {"team_id": row[0], "score": row[1]}
                for row in connection.execute(
                    """
                    SELECT owner_team_id, COALESCE(SUM(score), 0) AS total
                    FROM territory_claims WHERE game_session_id = ?
                    GROUP BY owner_team_id ORDER BY total DESC, owner_team_id
                    """,
                    (game_session_id,),
                )
            ]
        return {
            "territories": territories,
            "home_place_id": home[0] if home else None,
            "ranking": ranking,
        }

    def set_home(self, game_session_id: str, team_id: str, place_id: str) -> None:
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO home_states (game_session_id, team_id, home_place_id)
                VALUES (?, ?, ?)
                ON CONFLICT(game_session_id, team_id)
                DO UPDATE SET home_place_id = excluded.home_place_id
                """,
                (game_session_id, team_id, place_id),
            )

    def set_home_if_missing(self, game_session_id: str, team_id: str, place_id: str) -> None:
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            self._set_home_if_missing(connection, game_session_id, team_id, place_id)

    def set_home_from_candidates_if_missing(
        self, game_session_id: str, team_id: str, candidates: list[str]
    ) -> None:
        if not candidates:
            return
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            existing = connection.execute(
                "SELECT 1 FROM home_states WHERE game_session_id = ? AND team_id = ?",
                (game_session_id, team_id),
            ).fetchone()
            if existing is None:
                self._set_home_if_missing(
                    connection, game_session_id, team_id, random.choice(candidates)
                )

    def claim_place(self, *, game_session_id, team_id, place_id, score, action_id):
        self.initialize()
        with sqlite3.connect(self.database_path) as connection:
            existing = connection.execute(
                """
                SELECT place_id, claimed, score_delta, team_score, transferred, home_place_id
                FROM territory_action_results
                WHERE game_session_id = ? AND team_id = ? AND action_id = ?
                """,
                (game_session_id, team_id, action_id),
            ).fetchone()
            if existing:
                return ClaimResult(
                    claimed=bool(existing[1]),
                    score_delta=existing[2],
                    team_score=existing[3],
                    transferred=bool(existing[4]),
                    home_place_id=existing[5],
                    replayed=True,
                )
            result = self._claim_with_connection(
                connection,
                game_session_id=game_session_id,
                team_id=team_id,
                place_id=place_id,
                score=score,
                occurred_at=action_id,
            )
            home = connection.execute(
                "SELECT home_place_id FROM home_states WHERE game_session_id = ? AND team_id = ?",
                (game_session_id, team_id),
            ).fetchone()
            result = ClaimResult(
                claimed=result.claimed,
                score_delta=result.score_delta,
                team_score=result.team_score,
                transferred=result.transferred,
                home_place_id=home[0] if home else None,
            )
            connection.execute(
                """
                INSERT INTO territory_action_results
                    (game_session_id, team_id, action_id, place_id, claimed,
                     score_delta, team_score, transferred, home_place_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_session_id,
                    team_id,
                    action_id,
                    place_id,
                    int(result.claimed),
                    result.score_delta,
                    result.team_score,
                    int(result.transferred),
                    result.home_place_id,
                ),
            )
        return result


class GameStore(_TerritoryStoreMixin):
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
        self._initialize_territories(self.connection)
        self._migrate_legacy_claims(self.connection, "occurred_at")
        self.connection.commit()

    def set_home(self, game_session_id: str, team_id: str, place_id: str) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO home_states (game_session_id, team_id, home_place_id)
                VALUES (?, ?, ?)
                ON CONFLICT(game_session_id, team_id)
                DO UPDATE SET home_place_id = excluded.home_place_id
                """,
                (game_session_id, team_id, place_id),
            )

    def set_home_if_missing(self, game_session_id: str, team_id: str, place_id: str) -> None:
        with self.connection:
            self._set_home_if_missing(
                self.connection, game_session_id, team_id, place_id
            )

    def home_for(self, game_session_id: str, team_id: str) -> str | None:
        row = self.connection.execute(
            "SELECT home_place_id FROM home_states WHERE game_session_id = ? AND team_id = ?",
            (game_session_id, team_id),
        ).fetchone()
        return row[0] if row else None

    def place_owner(self, game_session_id: str, place_id: str) -> str | None:
        row = self.connection.execute(
            "SELECT owner_team_id FROM territory_claims WHERE game_session_id = ? AND place_id = ?",
            (game_session_id, place_id),
        ).fetchone()
        return row[0] if row else None

    def claim_place(self, *, game_session_id, team_id, place_id, score, occurred_at):
        with self.connection:
            return self._claim_with_connection(
                self.connection,
                game_session_id=game_session_id,
                team_id=team_id,
                place_id=place_id,
                score=score,
                occurred_at=occurred_at,
            )
