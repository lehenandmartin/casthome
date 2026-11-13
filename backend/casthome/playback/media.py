"""Build what the Cast device loads: stream URL, MIME type and metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from casthome.subsonic.client import NotAuthenticatedError, PasswordProvider
from casthome.subsonic.formats import plan_stream
from casthome.subsonic.models import Song
from casthome.subsonic.tokens import cover_art_url, stream_url

METADATA_TYPE_MUSIC_TRACK = 3


@dataclass(frozen=True)
class CastMedia:
    url: str
    content_type: str
    metadata: dict[str, Any]
    transcoded: bool


@dataclass(frozen=True)
class StreamConfig:
    public_base_url: str
    username: str
    stream_format: str = "raw"
    max_bitrate: int = 0
    fallback_format: str = "mp3"


class MediaBuilder:
    def __init__(self, config: StreamConfig, password_provider: PasswordProvider) -> None:
        self._config = config
        self._password_provider = password_provider

    async def build(self, song: Song, force_fallback: bool = False) -> CastMedia:
        password = await self._password_provider()
        if password is None:
            raise NotAuthenticatedError()
        cfg = self._config
        plan = plan_stream(song, cfg.stream_format, cfg.max_bitrate, cfg.fallback_format, force_fallback)
        url = stream_url(cfg.public_base_url, cfg.username, password, song.id, plan.format, plan.max_bitrate)
        metadata: dict[str, Any] = {
            "metadataType": METADATA_TYPE_MUSIC_TRACK,
            "title": song.title,
            "artist": song.artist,
            "albumName": song.album,
        }
        if song.track:
            metadata["trackNumber"] = song.track
        if song.disc:
            metadata["discNumber"] = song.disc
        if song.cover_art:
            cover = cover_art_url(cfg.public_base_url, cfg.username, password, song.cover_art)
            metadata["images"] = [{"url": cover}]
        return CastMedia(url=url, content_type=plan.content_type, metadata=metadata, transcoded=plan.format is not None)
