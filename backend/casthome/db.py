"""SQLite access (aiosqlite) with a tiny versioned migration system."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite

MIGRATIONS: list[str] = [
    # v1
    """
    CREATE TABLE sessions (
        id TEXT PRIMARY KEY,
        token_hash BLOB NOT NULL UNIQUE,
        persistent INTEGER NOT NULL,
        created_at REAL NOT NULL,
        last_seen_at REAL NOT NULL,
        expires_at REAL NOT NULL,
        user_agent TEXT NOT NULL DEFAULT '',
        ip TEXT NOT NULL DEFAULT ''
    );
    CREATE INDEX sessions_expires_at ON sessions (expires_at);

    CREATE TABLE credentials (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        password_enc BLOB NOT NULL,
        updated_at REAL NOT NULL
    );

    CREATE TABLE app_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """,
]


class Database:
    def __init__(self, path: Path | str) -> None:
        self._path = str(path)
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not open")
        return self._conn

    async def open(self) -> None:
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._migrate()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def _migrate(self) -> None:
        async with self.conn.execute("PRAGMA user_version") as cur:
            row = await cur.fetchone()
        version = int(row[0]) if row else 0
        for index, script in enumerate(MIGRATIONS[version:], start=version + 1):
            await self.conn.executescript(script)
            await self.conn.execute(f"PRAGMA user_version = {index}")
        await self.conn.commit()

    # --- key/value app state -------------------------------------------------

    async def get_state(self, key: str, default: Any = None) -> Any:
        async with self.conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
        return json.loads(row["value"]) if row else default

    async def set_state(self, key: str, value: Any) -> None:
        await self.conn.execute(
            "INSERT INTO app_state (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )
        await self.conn.commit()
