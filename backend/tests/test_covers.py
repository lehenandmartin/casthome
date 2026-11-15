import asyncio
import io
import os

from PIL import Image

from casthome.covers import CoverCache


def png(size: int = 600, color: tuple[int, int, int] = (200, 30, 90)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (size, size), color).save(out, "PNG")
    return out.getvalue()


def fetcher(data: bytes | None, calls: list[int]):
    async def fetch():
        calls.append(1)
        await asyncio.sleep(0)
        return None if data is None else (data, "image/png")

    return fetch


async def test_converts_to_webp_at_the_size_asked_and_keeps_it(tmp_path):
    cache = CoverCache(tmp_path)
    calls: list[int] = []
    cover = await cache.get("al-1", 300, True, fetcher(png(), calls))
    assert cover is not None and cover.content_type == "image/webp"
    with Image.open(io.BytesIO(cover.data)) as image:
        assert image.format == "WEBP" and image.size == (300, 300)
    again = await cache.get("al-1", 300, True, fetcher(png(), calls))
    assert again == cover and calls == [1]  # second time from the disk


async def test_jpeg_for_browsers_without_webp_and_never_scaled_up(tmp_path):
    cover = await CoverCache(tmp_path).get("al-2", 600, False, fetcher(png(200), []))
    assert cover is not None and cover.content_type == "image/jpeg"
    with Image.open(io.BytesIO(cover.data)) as image:
        assert image.format == "JPEG" and image.size == (200, 200)


async def test_same_cover_asked_twice_at_once_is_fetched_once(tmp_path):
    cache = CoverCache(tmp_path)
    calls: list[int] = []
    a, b = await asyncio.gather(
        cache.get("al-3", 300, True, fetcher(png(), calls)), cache.get("al-3", 300, True, fetcher(png(), calls))
    )
    assert a == b and calls == [1]


async def test_missing_or_unreadable_covers(tmp_path):
    cache = CoverCache(tmp_path)
    assert await cache.get("none", 300, True, fetcher(None, [])) is None
    sent_as_is = await cache.get("bad", 300, True, fetcher(b"not an image", []))
    assert sent_as_is is not None and sent_as_is.data == b"not an image" and sent_as_is.content_type == "image/png"


async def test_prune_keeps_the_most_recently_used(tmp_path):
    cache = CoverCache(tmp_path)
    for i in range(4):
        await cache.get(f"al-{i}", 300, True, fetcher(png(color=(i * 50, 0, 0)), []))
    files = sorted(tmp_path.glob("*/*.webp"))
    sizes = sum(f.stat().st_size for f in files)
    newest = max(files, key=lambda f: f.stat().st_mtime)
    for n, f in enumerate(files):  # make the order of use explicit
        os.utime(f, (1000 + n, 1000 + n))
    os.utime(newest, (5000, 5000))
    cache.max_bytes = sizes // 2
    cache.prune()
    left = list(tmp_path.glob("*/*.webp"))
    assert newest in left and sum(f.stat().st_size for f in left) <= sizes // 2
