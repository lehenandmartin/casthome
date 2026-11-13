"""Browser sessions: opaque cookie token, only its SHA-256 is stored.

- persistent ("keep me signed in"): long-lived cookie, sliding expiry.
- non-persistent: browser-session cookie plus a short sliding idle timeout.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass

from casthome.db import Database

# Avoid a database write on every request: only slide the expiry this often.
TOUCH_INTERVAL_S = 300.0


@dataclass(frozen=True)
class Session:
    id: str
    persistent: bool
    created_at: float
    last_seen_at: float
    expires_at: float
    user_agent: str
    ip: str


@dataclass(frozen=True)
class TouchResult:
    session: Session
    renewed: bool  # True when the cookie should be re-sent with a fresh Max-Age


def _hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


class SessionStore:
    def __init__(
        self,
        db: Database,
        remember_seconds: float,
        short_seconds: float,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._db = db
        self.remember_seconds = remember_seconds
        self.short_seconds = short_seconds
        self._clock = clock

    def lifetime(self, persistent: bool) -> float:
        return self.remember_seconds if persistent else self.short_seconds

    async def create(self, persistent: bool, user_agent: str = "", ip: str = "") -> tuple[str, Session]:
        token = secrets.token_urlsafe(32)
        now = self._clock()
        session = Session(
            id=secrets.token_hex(8),
            persistent=persistent,
            created_at=now,
            last_seen_at=now,
            expires_at=now + self.lifetime(persistent),
            user_agent=user_agent[:300],
            ip=ip,
        )
        await self._db.conn.execute(
            "INSERT INTO sessions (id, token_hash, persistent, created_at, last_seen_at, expires_at, user_agent, ip)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session.id,
                _hash(token),
                int(persistent),
                session.created_at,
                session.last_seen_at,
                session.expires_at,
                session.user_agent,
                session.ip,
            ),
        )
        await self._db.conn.commit()
        return token, session

    async def touch(self, token: str) -> TouchResult | None:
        """Validate a token and slide its expiry. Returns None if unknown or expired."""
        async with self._db.conn.execute("SELECT * FROM sessions WHERE token_hash = ?", (_hash(token),)) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        now = self._clock()
        session = _row_to_session(row)
        if session.expires_at <= now:
            await self.revoke(session.id)
            return None
        if now - session.last_seen_at < TOUCH_INTERVAL_S:
            return TouchResult(session, renewed=False)
        expires_at = now + self.lifetime(session.persistent)
        await self._db.conn.execute(
            "UPDATE sessions SET last_seen_at = ?, expires_at = ? WHERE id = ?",
            (now, expires_at, session.id),
        )
        await self._db.conn.commit()
        updated = Session(**{**session.__dict__, "last_seen_at": now, "expires_at": expires_at})
        return TouchResult(updated, renewed=True)

    async def list(self) -> list[Session]:
        await self.purge_expired()
        async with self._db.conn.execute("SELECT * FROM sessions ORDER BY last_seen_at DESC") as cur:
            rows = await cur.fetchall()
        return [_row_to_session(r) for r in rows]

    async def revoke(self, session_id: str) -> bool:
        cur = await self._db.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await self._db.conn.commit()
        return cur.rowcount > 0

    async def revoke_all(self) -> None:
        await self._db.conn.execute("DELETE FROM sessions")
        await self._db.conn.commit()

    async def purge_expired(self) -> None:
        await self._db.conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (self._clock(),))
        await self._db.conn.commit()


def _row_to_session(row) -> Session:  # type: ignore[no-untyped-def]
    return Session(
        id=row["id"],
        persistent=bool(row["persistent"]),
        created_at=row["created_at"],
        last_seen_at=row["last_seen_at"],
        expires_at=row["expires_at"],
        user_agent=row["user_agent"],
        ip=row["ip"],
    )
