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
    starred: bool = False
    user_rating: int = 0
    play_count: int = 0
    # ISO dates, for sorting favorites on servers other than Navidrome.
    created: str | None = None
    played: str | None = None

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
            starred=bool(d.get("starred")),
            user_rating=int(d.get("userRating") or 0),
            play_count=int(d.get("playCount") or 0),
            created=d.get("created"),
            played=d.get("played"),
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
    starred: bool = False
    user_rating: int = 0
    play_count: int = 0
    created: str | None = None
    played: str | None = None
    songs: list[Song] | None = None
    # Names of the discs when they are tagged (OpenSubsonic discTitles), by
    # disc number: "The Fame Monster", "The Fame".
    disc_titles: dict[int, str] = {}

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> Album:
        songs = d.get("song")
        disc_titles = {
            int(item["disc"]): str(item["title"]).strip()
            for item in d.get("discTitles") or []
            if isinstance(item, dict) and item.get("disc") is not None and str(item.get("title") or "").strip()
        }
        return cls(
            id=str(d["id"]),
            name=d.get("name") or d.get("title") or "",
            artist=d.get("artist", ""),
            artist_id=d.get("artistId"),
            cover_art=d.get("coverArt"),
            year=d.get("year"),
            song_count=int(d.get("songCount") or 0),
            duration=float(d.get("duration") or 0),
            starred=bool(d.get("starred")),
            user_rating=int(d.get("userRating") or 0),
            play_count=int(d.get("playCount") or 0),
            created=d.get("created"),
            played=d.get("played"),
            songs=[Song.from_api(s) for s in songs] if songs is not None else None,
            disc_titles=disc_titles,
        )


class Artist(BaseModel):
    id: str
    name: str
    album_count: int = 0
    cover_art: str | None = None
    starred: bool = False

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> Artist:
        return cls(
            id=str(d["id"]),
            name=d.get("name", ""),
            album_count=int(d.get("albumCount") or 0),
            cover_art=d.get("coverArt"),
            starred=bool(d.get("starred")),
        )


class Genre(BaseModel):
    name: str
    song_count: int = 0
    album_count: int = 0

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> Genre:
        return cls(
            name=d.get("value") or d.get("name") or "",
            song_count=int(d.get("songCount") or 0),
            album_count=int(d.get("albumCount") or 0),
        )


class SearchResult(BaseModel):
    """Also used for starred items (getStarred2)."""

    artists: list[Artist]
    albums: list[Album]
    songs: list[Song]

    @classmethod
    def from_api(cls, d: dict[str, Any] | None) -> SearchResult:
        d = d or {}
        return cls(
            artists=[Artist.from_api(a) for a in d.get("artist", [])],
            albums=[Album.from_api(a) for a in d.get("album", [])],
            songs=[Song.from_api(s) for s in d.get("song", [])],
        )


class Playlist(BaseModel):
    id: str
    name: str
    comment: str = ""
    owner: str = ""
    public: bool = False
    song_count: int = 0
    duration: float = 0
    cover_art: str | None = None
    changed: str | None = None
    songs: list[Song] | None = None

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> Playlist:
        entries = d.get("entry")
        return cls(
            id=str(d["id"]),
            name=d.get("name", ""),
            comment=d.get("comment") or "",
            owner=d.get("owner") or "",
            public=bool(d.get("public")),
            song_count=int(d.get("songCount") or 0),
            duration=float(d.get("duration") or 0),
            cover_art=d.get("coverArt"),
            changed=d.get("changed"),
            songs=[Song.from_api(s) for s in entries] if entries is not None else None,
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
