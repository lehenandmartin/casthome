"""Normalized DTOs for the parts of the Subsonic API we use."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Song(BaseModel):
    id: str
    title: str
    artist: str = ""
    artist_id: str | None = None
    album: str = ""
    album_id: str | None = None
    cover_art: str | None = None
    duration: float = 0
    track: int | None = None
    disc: int | None = None
    suffix: str = ""
    content_type: str = ""
    bit_rate: int | None = None
    sampling_rate: int | None = None
    bit_depth: int | None = None

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> Song:
        return cls(
            id=str(d["id"]),
            title=d.get("title", ""),
            artist=d.get("artist", ""),
            artist_id=d.get("artistId"),
            album=d.get("album", ""),
            album_id=d.get("albumId"),
            cover_art=d.get("coverArt"),
            duration=float(d.get("duration") or 0),
            track=d.get("track"),
            disc=d.get("discNumber"),
            suffix=(d.get("suffix") or "").lower(),
            content_type=d.get("contentType", ""),
            bit_rate=d.get("bitRate"),
            sampling_rate=d.get("samplingRate"),
            bit_depth=d.get("bitDepth"),
        )


class Album(BaseModel):
    id: str
    name: str
    artist: str = ""
    artist_id: str | None = None
    cover_art: str | None = None
    year: int | None = None
    song_count: int = 0
    duration: float = 0
    songs: list[Song] | None = None

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> Album:
        songs = d.get("song")
        return cls(
            id=str(d["id"]),
            name=d.get("name") or d.get("title") or "",
            artist=d.get("artist", ""),
            artist_id=d.get("artistId"),
            cover_art=d.get("coverArt"),
            year=d.get("year"),
            song_count=int(d.get("songCount") or 0),
            duration=float(d.get("duration") or 0),
            songs=[Song.from_api(s) for s in songs] if songs is not None else None,
        )


class PlayQueue(BaseModel):
    songs: list[Song]
    current_id: str | None = None
    position_ms: int = 0
    changed: str | None = None
    changed_by: str | None = None

    @classmethod
    def from_api(cls, d: dict[str, Any] | None) -> PlayQueue:
        d = d or {}
        current = d.get("current")
        return cls(
            songs=[Song.from_api(s) for s in d.get("entry", [])],
            current_id=str(current) if current is not None else None,
            position_ms=int(d.get("position") or 0),
            changed=d.get("changed"),
            changed_by=d.get("changedBy"),
        )
