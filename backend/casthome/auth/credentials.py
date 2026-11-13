"""The single Navidrome password, encrypted at rest, cached in memory."""

from __future__ import annotations

import time

from casthome.auth.crypto import SecretBox
from casthome.db import Database


class CredentialStore:
    def __init__(self, db: Database, box: SecretBox) -> None:
        self._db = db
        self._box = box
        self._cached: str | None = None
        self._loaded = False

    async def get_password(self) -> str | None:
        if not self._loaded:
            async with self._db.conn.execute("SELECT password_enc FROM credentials WHERE id = 1") as cur:
                row = await cur.fetchone()
            self._cached = self._box.decrypt(row["password_enc"]) if row else None
            self._loaded = True
        return self._cached

    async def set_password(self, password: str) -> None:
        await self._db.conn.execute(
            "INSERT INTO credentials (id, password_enc, updated_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET password_enc = excluded.password_enc, updated_at = excluded.updated_at",
            (self._box.encrypt(password), time.time()),
        )
        await self._db.conn.commit()
        self._cached = password
        self._loaded = True

    async def clear(self) -> None:
        await self._db.conn.execute("DELETE FROM credentials")
        await self._db.conn.commit()
        self._cached = None
        self._loaded = True
