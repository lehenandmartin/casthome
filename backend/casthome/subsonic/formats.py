"""Decide whether a song can be streamed as-is to a Cast device."""

from __future__ import annotations

from dataclasses import dataclass

from casthome.subsonic.models import Song

# Containers/codecs the Default Media Receiver plays natively. ".m4a" may hold
# ALAC, which Cast cannot play: that case is caught at runtime by the
# error-then-transcode fallback.
CAST_NATIVE_SUFFIXES = {"mp3", "flac", "aac", "m4a", "mp4", "ogg", "oga", "opus", "wav", "webm"}
MAX_NATIVE_SAMPLE_RATE = 96_000
MAX_NATIVE_BIT_DEPTH = 24

FORMAT_MIME = {
    "mp3": "audio/mpeg",
    "aac": "audio/aac",
    "opus": "audio/ogg",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
}

SUFFIX_MIME = {
    "mp3": "audio/mpeg",
    "flac": "audio/flac",
    "aac": "audio/aac",
    "m4a": "audio/mp4",
    "mp4": "audio/mp4",
    "ogg": "audio/ogg",
    "oga": "audio/ogg",
    "opus": "audio/ogg",
    "wav": "audio/wav",
    "webm": "audio/webm",
}


@dataclass(frozen=True)
class StreamPlan:
    format: str | None  # None = original file
    max_bitrate: int
    content_type: str


def is_cast_native(song: Song) -> bool:
    if song.suffix not in CAST_NATIVE_SUFFIXES:
        return False
    if song.sampling_rate and song.sampling_rate > MAX_NATIVE_SAMPLE_RATE:
        return False
    if song.bit_depth and song.bit_depth > MAX_NATIVE_BIT_DEPTH:
        return False
    return True


def plan_stream(
    song: Song,
    configured_format: str,
    max_bitrate: int,
    fallback_format: str,
    force_fallback: bool = False,
) -> StreamPlan:
    fmt: str | None
    if force_fallback:
        fmt = fallback_format
    elif configured_format and configured_format != "raw":
        fmt = configured_format
    elif not is_cast_native(song):
        fmt = fallback_format
    else:
        fmt = None

    if fmt is None:
        content_type = song.content_type or SUFFIX_MIME.get(song.suffix, "audio/mpeg")
        # The original is streamed: maxBitRate would make Navidrome transcode anyway.
        return StreamPlan(format=None, max_bitrate=0, content_type=content_type)
    return StreamPlan(format=fmt, max_bitrate=max_bitrate, content_type=FORMAT_MIME.get(fmt, "audio/mpeg"))
