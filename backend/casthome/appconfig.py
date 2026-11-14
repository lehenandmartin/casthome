"""Configuration entered from the browser, saved in the database.

Environment variables (see config.py) still win field by field: a value set
there is used as is and shows as locked in the browser.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import ipaddress
import logging
import os
import secrets
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from casthome.config import Settings
from casthome.db import Database

log = logging.getLogger(__name__)

NAVIDROME_KEY = "config.navidrome"
ACCESS_KEY = "config.access"
PLAYBACK_KEY = "config.playback"


class AccessMode(StrEnum):
    PASSWORD = "password"  # a CastHome password everywhere
    OPEN = "open"  # no sign-in at all
    LAN = "lan"  # no sign-in from the local network, the password from anywhere else


@dataclass(frozen=True)
class NavidromeConfig:
    url: str
    public_url: str  # as reached by Cast devices
    username: str


# Fields an environment variable can lock.
NAVIDROME_FIELDS = ("url", "public_url", "username", "password")


@dataclass(frozen=True)
class PlaybackConfig:
    stream_format: str  # "raw" (original files) or a Navidrome transcoding format
    max_bitrate: int  # kbps when transcoding, 0 = no limit
    preload_next: bool
    known_hosts: tuple[str, ...]  # Cast device addresses, when mDNS is blocked
    scrobble: bool = True  # report plays to Navidrome
    show_ratings: bool = True  # show the 5-star ratings in the interface (every device)


# Playback field -> environment setting (see config.py).
PLAYBACK_ENV = {
    "stream_format": "stream_format",
    "max_bitrate": "stream_max_bitrate",
    "preload_next": "cast_preload_next",
    "known_hosts": "cast_known_hosts",
    "scrobble": "scrobble",
    "show_ratings": "show_ratings",
}


def load_secret_key(settings: Settings) -> str:
    """APP_SECRET_KEY if set, else the key generated on first start.

    The key in use is always written to <data_dir>/secret.key, so an install
    that started with APP_SECRET_KEY keeps working once it is removed.
    """
    path: Path = settings.secret_key_path
    existing = path.read_text().strip() if path.is_file() else None
    key = settings.app_secret_key or existing or secrets.token_urlsafe(48)
    if key != existing:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(key + "\n")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        if existing is None:
            log.info("Saved the encryption key to %s", path)
    return key


# --- CastHome password -------------------------------------------------------

_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = _scrypt(password, salt, **_SCRYPT)
    b64 = base64.b64encode
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${b64(salt).decode()}${b64(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        actual = _scrypt(password, base64.b64decode(salt), int(n), int(r), int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, base64.b64decode(digest))


def is_local_address(host: str | None) -> bool:
    """Private, loopback or link-local address: a client on the local network."""
    if not host:
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_private or address.is_loopback or address.is_link_local


class ConfigStore:
    def __init__(self, db: Database, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._saved_navidrome: dict[str, str] = {}
        self.access_mode: AccessMode | None = None
        self._password_hash: str | None = None
        self._saved_playback: dict[str, object] = {}

    async def load(self) -> None:
        self._saved_navidrome = dict(await self._db.get_state(NAVIDROME_KEY, {}) or {})
        access = await self._db.get_state(ACCESS_KEY, None) or {}
        try:
            self.access_mode = AccessMode(access["mode"]) if access.get("mode") else None
        except ValueError:
            self.access_mode = None
        self._password_hash = access.get("password_hash")
        self._saved_playback = dict(await self._db.get_state(PLAYBACK_KEY, {}) or {})
        await self._import_environment()

    async def _import_environment(self) -> None:
        """Copy Navidrome values set in the environment to the database once,
        so they survive removing them from .env later."""
        env = self._env_navidrome()
        missing = {k: v for k, v in env.items() if v and k != "password" and not self._saved_navidrome.get(k)}
        if missing:
            self._saved_navidrome.update(missing)
            await self._db.set_state(NAVIDROME_KEY, self._saved_navidrome)

    def _env_navidrome(self) -> dict[str, str | None]:
        s = self._settings
        return {
            "url": s.navidrome_url,
            "public_url": s.navidrome_public_url_for_cast,
            "username": s.navidrome_username,
            "password": s.navidrome_password,
        }

    # --- Navidrome -----------------------------------------------------------

    @property
    def locked(self) -> list[str]:
        """Navidrome fields set by environment variables."""
        return [k for k, v in self._env_navidrome().items() if v]

    @property
    def env_password(self) -> str | None:
        return self._settings.navidrome_password

    def _value(self, field: str) -> str | None:
        return self._env_navidrome().get(field) or self._saved_navidrome.get(field) or None

    @property
    def navidrome(self) -> NavidromeConfig | None:
        url, public_url, username = self._value("url"), self._value("public_url"), self._value("username")
        if not (url and username):
            return None
        return NavidromeConfig(url=url, public_url=public_url or url, username=username)

    def navidrome_fields(self) -> dict[str, str]:
        """Current values, as shown in the forms (empty when unset)."""
        return {k: self._value(k) or "" for k in ("url", "public_url", "username")}

    async def save_navidrome(self, config: NavidromeConfig) -> None:
        self._saved_navidrome = asdict(config)
        await self._db.set_state(NAVIDROME_KEY, self._saved_navidrome)

    # --- playback ------------------------------------------------------------

    @property
    def playback_locked(self) -> list[str]:
        """Playback fields set by environment variables."""
        explicit = self._settings.model_fields_set
        return [field for field, env in PLAYBACK_ENV.items() if env in explicit]

    @property
    def playback(self) -> PlaybackConfig:
        s = self._settings
        env = {
            "stream_format": s.stream_format,
            "max_bitrate": s.stream_max_bitrate,
            "preload_next": s.cast_preload_next,
            "known_hosts": tuple(s.known_hosts),
            "scrobble": s.scrobble,
            "show_ratings": s.show_ratings,
        }
        locked = set(self.playback_locked)
        values = {}
        for field, default in env.items():
            saved = self._saved_playback.get(field)
            values[field] = default if field in locked or saved is None else saved
        values["known_hosts"] = tuple(values["known_hosts"])  # type: ignore[arg-type]
        return PlaybackConfig(**values)  # type: ignore[arg-type]

    async def save_playback(self, config: PlaybackConfig) -> None:
        saved = asdict(config)
        saved["known_hosts"] = list(config.known_hosts)
        # Locked fields keep following the environment.
        for field in self.playback_locked:
            saved.pop(field, None)
        self._saved_playback = saved
        await self._db.set_state(PLAYBACK_KEY, saved)

    # --- access ----------------------------------------------------------------

    @property
    def has_password(self) -> bool:
        return self._password_hash is not None

    async def check_password(self, password: str) -> bool:
        if self._password_hash is None:
            return False
        return await asyncio.to_thread(verify_password, password, self._password_hash)

    async def set_access(self, mode: AccessMode, password: str | None = None) -> None:
        """Set the access mode. `password` replaces the current one; an open
        mode drops it, a protected mode without a new one keeps it."""
        if mode is AccessMode.OPEN:
            password_hash = None
        elif password is not None:
            password_hash = await asyncio.to_thread(hash_password, password)
        else:
            password_hash = self._password_hash
        if mode is not AccessMode.OPEN and password_hash is None:
            raise ValueError("a password is required for this access mode")
        await self._db.set_state(ACCESS_KEY, {"mode": mode.value, "password_hash": password_hash})
        self.access_mode = mode
        self._password_hash = password_hash

    def open_for(self, client_host: str | None) -> bool:
        """True when this client gets in without signing in."""
        if self.access_mode is AccessMode.OPEN:
            return True
        return self.access_mode is AccessMode.LAN and is_local_address(client_host)
