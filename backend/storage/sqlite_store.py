"""SQLite-backed storage implementation.

All entity data is stored as JSON blobs in a `data TEXT` column.
No SQL outside this file.
"""

import sqlite3
import time

from ulid import ULID

from backend.models import BunqToken, PendingTool, Profile, Session, Turn


class SqliteStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self, user_id: str) -> Profile | None:
        row = self._conn.execute(
            "SELECT data FROM profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        return Profile.model_validate_json(row[0])

    def upsert_profile(self, profile: Profile) -> None:
        self._conn.execute(
            """
            INSERT INTO profiles (user_id, data) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET data = excluded.data
            """,
            (profile.user_id, profile.model_dump_json()),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self, user_id: str) -> Session:
        now = int(time.time() * 1000)
        session = Session(
            session_id=str(ULID()),
            user_id=user_id,
            started_at=now,
            last_active_at=now,
        )
        self._conn.execute(
            """
            INSERT INTO sessions (session_id, user_id, last_active_at, data)
            VALUES (?, ?, ?, ?)
            """,
            (session.session_id, user_id, now, session.model_dump_json()),
        )
        self._conn.commit()
        return session

    def get_latest_session(self, user_id: str) -> Session | None:
        row = self._conn.execute(
            """
            SELECT data FROM sessions
            WHERE user_id = ?
            ORDER BY last_active_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return Session.model_validate_json(row[0])

    def touch_session(self, session_id: str) -> None:
        now = int(time.time() * 1000)
        # Update the JSON blob and the indexed column atomically.
        row = self._conn.execute(
            "SELECT data FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return
        session = Session.model_validate_json(row[0])
        session.last_active_at = now
        self._conn.execute(
            "UPDATE sessions SET last_active_at = ?, data = ? WHERE session_id = ?",
            (now, session.model_dump_json(), session_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Turns
    # ------------------------------------------------------------------

    def append_turn(self, session_id: str, turn: Turn) -> None:
        self._conn.execute(
            """
            INSERT INTO turns (turn_id, session_id, ts_ms, data)
            VALUES (?, ?, ?, ?)
            """,
            (turn.turn_id, session_id, turn.ts_ms, turn.model_dump_json()),
        )
        self._conn.commit()
        self.touch_session(session_id)

    def list_turns(self, session_id: str, include_hidden: bool = False) -> list[Turn]:
        rows = self._conn.execute(
            """
            SELECT data FROM turns
            WHERE session_id = ?
            ORDER BY ts_ms ASC, turn_id ASC
            """,
            (session_id,),
        ).fetchall()
        turns = [Turn.model_validate_json(row[0]) for row in rows]
        if not include_hidden:
            turns = [t for t in turns if not t.hidden]
        return turns

    # ------------------------------------------------------------------
    # Pending tools
    # ------------------------------------------------------------------

    def put_pending_tool(self, session_id: str, pending: PendingTool) -> None:
        self._conn.execute(
            """
            INSERT INTO pending_tools (tool_use_id, session_id, data)
            VALUES (?, ?, ?)
            ON CONFLICT(tool_use_id) DO UPDATE SET data = excluded.data
            """,
            (pending.tool_use_id, session_id, pending.model_dump_json()),
        )
        self._conn.commit()

    def get_pending_tool(self, session_id: str, tool_use_id: str) -> PendingTool | None:
        row = self._conn.execute(
            "SELECT data FROM pending_tools WHERE tool_use_id = ? AND session_id = ?",
            (tool_use_id, session_id),
        ).fetchone()
        if row is None:
            return None
        return PendingTool.model_validate_json(row[0])

    def clear_pending_tool(self, session_id: str, tool_use_id: str) -> None:
        self._conn.execute(
            "DELETE FROM pending_tools WHERE tool_use_id = ? AND session_id = ?",
            (tool_use_id, session_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # bunq tokens
    # ------------------------------------------------------------------

    def get_bunq_token(self, user_id: str) -> BunqToken | None:
        row = self._conn.execute(
            "SELECT data FROM bunq_tokens WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        return BunqToken.model_validate_json(row[0])

    def put_bunq_token(self, user_id: str, token: BunqToken) -> None:
        self._conn.execute(
            """
            INSERT INTO bunq_tokens (user_id, data) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET data = excluded.data
            """,
            (user_id, token.model_dump_json()),
        )
        self._conn.commit()


def init_db(path: str) -> SqliteStore:
    """Open (or create) the SQLite database, run migrations, return a store."""
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            user_id TEXT PRIMARY KEY,
            data    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            session_id      TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL,
            last_active_at  INTEGER NOT NULL,
            data            TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user_active
            ON sessions (user_id, last_active_at);

        CREATE TABLE IF NOT EXISTS turns (
            turn_id     TEXT PRIMARY KEY,
            session_id  TEXT NOT NULL,
            ts_ms       INTEGER NOT NULL,
            data        TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_turns_session_ts
            ON turns (session_id, ts_ms, turn_id);

        CREATE TABLE IF NOT EXISTS pending_tools (
            tool_use_id  TEXT PRIMARY KEY,
            session_id   TEXT NOT NULL,
            data         TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bunq_tokens (
            user_id  TEXT PRIMARY KEY,
            data     TEXT NOT NULL
        );
        """
    )
    conn.commit()
    return SqliteStore(conn)
