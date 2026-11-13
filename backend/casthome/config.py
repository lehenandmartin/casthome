"""Application settings, loaded from environment variables (see .env.example)."""

from __future__ import annotations

import ipaddress
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # The repo-root .env is found whatever the working directory; a .env in the
    # working directory overrides it. Real environment variables win over both.
    model_config = SettingsConfigDict(env_file=(REPO_ROOT / ".env", ".env"), extra="ignore")

    app_secret_key: str = Field(min_length=32)

    navidrome_url: str
    navidrome_public_url_for_cast: str
    navidrome_username: str

    # Docker sets DATA_DIR=/data; running natively, data goes to <repo>/data.
    data_dir: Path = REPO_ROOT / "data"
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"

    cookie_secure: bool = False
    session_remember_days: int = 365
    session_short_hours: int = 12

    # "raw" streams the original file. Any other value is passed as Subsonic `format`.
    stream_format: str = "raw"
    stream_max_bitrate: int = 0
    transcode_fallback_format: str = "mp3"

    # Comma-separated IPs of Cast devices, for networks where mDNS is filtered.
    cast_known_hosts: str = ""

    frontend_dist: Path = REPO_ROOT / "frontend" / "dist"

    @field_validator("app_secret_key")
    @classmethod
    def _not_the_example(cls, value: str) -> str:
        if value.startswith("change-me"):
            raise ValueError("still the example value from .env.example; generate a real secret")
        return value

    @field_validator("navidrome_url", "navidrome_public_url_for_cast")
    @classmethod
    def _strip_slash(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("must be an absolute http(s) URL")
        return value.rstrip("/")

    @field_validator("navidrome_public_url_for_cast")
    @classmethod
    def _reachable_from_cast(cls, value: str) -> str:
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

    @property
    def known_hosts(self) -> list[str]:
        return [h.strip() for h in self.cast_known_hosts.split(",") if h.strip()]

    @property
    def database_path(self) -> Path:
        return self.data_dir / "casthome.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
