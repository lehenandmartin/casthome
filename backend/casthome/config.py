"""Application settings, loaded from environment variables (see .env.example)."""

from __future__ import annotations

import ipaddress
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def normalize_url(value: str) -> str:
    """An absolute http(s) URL, without trailing slash."""
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("must be an absolute http(s) URL")
    return value.rstrip("/")


def check_cast_url(value: str) -> str:
    """Cast devices fetch audio from this URL: it cannot point at this machine's loopback."""
    host = urlparse(value).hostname or ""
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("must be reachable from Cast devices; localhost is not")
    try:
        is_loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_loopback = False  # a host name, not an IP literal
    if is_loopback:
        raise ValueError("must be reachable from Cast devices; loopback is not")
    return value


class Settings(BaseSettings):
    # The repo-root .env is found whatever the working directory; a .env in the
    # working directory overrides it. Real environment variables win over both.
    model_config = SettingsConfigDict(env_file=(REPO_ROOT / ".env", ".env"), extra="ignore")

    # Everything below is optional: CastHome is configured from the browser on
    # first use. A value set here wins over the one saved from the browser, and
    # shows as locked there.
    # Without APP_SECRET_KEY, a key is generated once into <data_dir>/secret.key.
    app_secret_key: str | None = Field(default=None, min_length=32)

    navidrome_url: str | None = None
    navidrome_public_url_for_cast: str | None = None
    navidrome_username: str | None = None
    navidrome_password: str | None = None

    # Docker sets DATA_DIR=/data; running natively, data goes to <repo>/data.
    data_dir: Path = REPO_ROOT / "data"
    host: str = "0.0.0.0"
    port: int = 4577
    log_level: str = "INFO"

    cookie_secure: bool = False
    session_remember_days: int = 365
    session_short_hours: int = 12

    # "raw" streams the original file. Any other value is passed as Subsonic `format`.
    stream_format: str = "raw"
    stream_max_bitrate: int = 0
    transcode_fallback_format: str = "mp3"

    # Hand the next track to the Cast device ~20 s before the end of the
    # current one, to shorten the silence between tracks.
    cast_preload_next: bool = True

    # Report plays to Navidrome ("now playing", then a scrobble).
    scrobble: bool = True

    # Comma-separated IPs of Cast devices, for networks where mDNS is filtered.
    cast_known_hosts: str = ""

    frontend_dist: Path = REPO_ROOT / "frontend" / "dist"

    @field_validator("app_secret_key")
    @classmethod
    def _not_the_example(cls, value: str | None) -> str | None:
        if value is not None and value.startswith("change-me"):
            raise ValueError("still the example value from .env.example; generate a real secret or remove it")
        return value

    @field_validator(
        "app_secret_key",
        "navidrome_url",
        "navidrome_public_url_for_cast",
        "navidrome_username",
        "navidrome_password",
        mode="before",
    )
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("navidrome_url")
    @classmethod
    def _check_url(cls, value: str | None) -> str | None:
        return normalize_url(value) if value else None

    @field_validator("navidrome_public_url_for_cast")
    @classmethod
    def _check_cast_url(cls, value: str | None) -> str | None:
        return check_cast_url(normalize_url(value)) if value else None

    @property
    def known_hosts(self) -> list[str]:
        return [h.strip() for h in self.cast_known_hosts.split(",") if h.strip()]

    @property
    def database_path(self) -> Path:
        return self.data_dir / "casthome.db"

    @property
    def secret_key_path(self) -> Path:
        return self.data_dir / "secret.key"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
