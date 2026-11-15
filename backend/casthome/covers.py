"""Cover art for the browser: WebP at the size asked for, kept on disk.

Navidrome sends covers in their original format (often a heavy PNG, ~90 kB
for 300 px). CastHome converts each one once, at the size the page asks for,
to WebP (or JPEG for a browser that does not take WebP), about 5 to 10 times
lighter, and keeps the result in <data_dir>/covers. The folder is capped:
the least recently used files go first.

A cover that cannot be converted is sent as Navidrome gave it.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

log = logging.getLogger(__name__)

MAX_BYTES = 300 * 1024 * 1024  # disk space for converted covers
PRUNE_EVERY = 200  # check the folder's size every this many new files
WEBP_QUALITY = 80
JPEG_QUALITY = 82

# (bytes, content type) of the original cover, or None when there is none.
Fetch = Callable[[], Awaitable[tuple[bytes, str] | None]]


@dataclass(frozen=True)
class Cover:
    data: bytes
    content_type: str


def convert(data: bytes, size: int, fmt: str) -> bytes:
    """`data` scaled down to fit `size` (never up) and encoded as WEBP or JPEG."""
    with Image.open(io.BytesIO(data)) as source:
        source.load()
        image: Image.Image = source
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "transparency" in image.info or image.mode in ("LA", "PA") else "RGB")
        if fmt == "JPEG" and image.mode == "RGBA":
            image = image.convert("RGB")
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        if fmt == "WEBP":
            image.save(out, "WEBP", quality=WEBP_QUALITY, method=4)
        else:
            image.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        return out.getvalue()


class CoverCache:
    def __init__(self, folder: Path, max_bytes: int = MAX_BYTES) -> None:
        self.folder = folder
        self.max_bytes = max_bytes
        self._inflight: dict[Path, asyncio.Future[Cover | None]] = {}
        self._written = 0

    def _path(self, cover_id: str, size: int, fmt: str) -> Path:
        key = hashlib.sha1(f"{cover_id}\n{size}".encode()).hexdigest()
        return self.folder / key[:2] / f"{key}.{'webp' if fmt == 'WEBP' else 'jpg'}"

    async def get(self, cover_id: str, size: int, webp: bool, fetch: Fetch) -> Cover | None:
        fmt = "WEBP" if webp else "JPEG"
        content_type = "image/webp" if webp else "image/jpeg"
        path = self._path(cover_id, size, fmt)
        try:
            data = await asyncio.to_thread(path.read_bytes)
            os.utime(path)  # recently used: kept when the folder is pruned
            return Cover(data, content_type)
        except FileNotFoundError:
            pass
        # One conversion per cover at a time (a page asks for the same one twice).
        pending = self._inflight.get(path)
        if pending is not None:
            return await pending
        future: asyncio.Future[Cover | None] = asyncio.get_running_loop().create_future()
        self._inflight[path] = future
        try:
            result = await self._make(path, size, fmt, content_type, fetch)
            future.set_result(result)
            return result
        except BaseException as exc:
            future.set_exception(exc)
            # Nobody else may be waiting: mark the exception as seen.
            future.exception()
            raise
        finally:
            del self._inflight[path]

    async def _make(self, path: Path, size: int, fmt: str, content_type: str, fetch: Fetch) -> Cover | None:
        original = await fetch()
        if original is None:
            return None
        data, original_type = original
        try:
            converted = await asyncio.to_thread(convert, data, size, fmt)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            log.info("Cover not converted (%s); sent as is", exc)
            return Cover(data, original_type)
        try:
            await asyncio.to_thread(self._write, path, converted)
        except OSError as exc:
            log.warning("Cover not kept on disk: %s", exc)
        return Cover(converted, content_type)

    def _write(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        self._written += 1
        if self._written % PRUNE_EVERY == 0:
            self.prune()

    def prune(self) -> None:
        """Delete the least recently used covers beyond `max_bytes`."""
        files = []
        total = 0
        for entry in self.folder.glob("*/*"):
            if entry.suffix not in (".webp", ".jpg"):
                continue
            st = entry.stat()
            files.append((st.st_mtime, st.st_size, entry))
            total += st.st_size
        if total <= self.max_bytes:
            return
        files.sort()
        started = time.monotonic()
        for _mtime, size, entry in files:
            if total <= self.max_bytes * 0.9:
                break
            entry.unlink(missing_ok=True)
            total -= size
        log.info("Cover cache pruned to %d MB in %.2fs", total // (1024 * 1024), time.monotonic() - started)
