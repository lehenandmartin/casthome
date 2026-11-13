import hashlib
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from casthome.subsonic.client import InvalidCredentialsError, NavidromeUnavailableError, SubsonicClient
from casthome.subsonic.formats import is_cast_native, plan_stream
from casthome.subsonic.models import Song
from casthome.subsonic.tokens import auth_params, make_token, stream_url


def test_token_is_md5_of_password_and_salt():
    assert make_token("sesame", "c19b2d") == hashlib.md5(b"sesamec19b2d").hexdigest()


def test_auth_params_use_random_salt():
    a, b = auth_params("me", "pw"), auth_params("me", "pw")
    assert a["s"] != b["s"]
    assert a["t"] == make_token("pw", a["s"])
    assert a["u"] == "me" and a["c"] == "CastHome"
    assert "p" not in a  # the clear password is never put in a URL


def test_stream_url_original():
    url = stream_url("http://192.168.1.10:4533/", "me", "pw", "song1", salt="abc")
    parsed = urlparse(url)
    q = parse_qs(parsed.query)
    assert parsed.netloc == "192.168.1.10:4533" and parsed.path == "/rest/stream"
    assert q["id"] == ["song1"] and q["s"] == ["abc"] and q["t"] == [make_token("pw", "abc")]
    assert "format" not in q and "maxBitRate" not in q


def test_stream_url_transcoded():
    q = parse_qs(urlparse(stream_url("http://nd", "me", "pw", "x", fmt="mp3", max_bitrate=320)).query)
    assert q["format"] == ["mp3"] and q["maxBitRate"] == ["320"] and q["estimateContentLength"] == ["true"]


def song(**kw) -> Song:
    return Song(id="1", title="t", **kw)


@pytest.mark.parametrize(
    ("kw", "native"),
    [
        ({"suffix": "flac", "sampling_rate": 44100}, True),
        ({"suffix": "flac", "sampling_rate": 192000}, False),
        ({"suffix": "flac", "bit_depth": 32}, False),
        ({"suffix": "mp3"}, True),
        ({"suffix": "wma"}, False),
        ({"suffix": "dsf"}, False),
    ],
)
def test_cast_native(kw, native):
    assert is_cast_native(song(**kw)) is native


def test_plan_stream_raw_native_keeps_original():
    plan = plan_stream(song(suffix="flac", content_type="audio/flac"), "raw", 320, "mp3")
    assert plan.format is None and plan.max_bitrate == 0 and plan.content_type == "audio/flac"


def test_plan_stream_falls_back_for_unsupported():
    plan = plan_stream(song(suffix="wma"), "raw", 0, "mp3")
    assert plan.format == "mp3" and plan.content_type == "audio/mpeg"


def test_plan_stream_configured_format_and_forced_fallback():
    assert plan_stream(song(suffix="flac"), "opus", 192, "mp3").format == "opus"
    assert plan_stream(song(suffix="flac"), "raw", 0, "mp3", force_fallback=True).format == "mp3"


async def _pw() -> str:
    return "pw"


@respx.mock
async def test_client_maps_wrong_credentials_and_fires_callback():
    respx.get(url__startswith="http://nd/rest/ping").mock(
        return_value=httpx.Response(
            200, json={"subsonic-response": {"status": "failed", "error": {"code": 40, "message": "Wrong"}}}
        )
    )
    client = SubsonicClient("http://nd", "me", _pw)
    fired = []

    async def on_invalid() -> None:
        fired.append(True)

    client.on_invalid_credentials = on_invalid
    with pytest.raises(InvalidCredentialsError):
        await client.ping()
    assert fired == [True]
    # An explicit password (login attempt) must not invalidate the stored one.
    with pytest.raises(InvalidCredentialsError):
        await client.ping(password="other")
    assert fired == [True]
    await client.aclose()


@respx.mock
async def test_client_sends_auth_and_params_together():
    route = respx.get(url__startswith="http://nd/rest/getAlbum").mock(
        return_value=httpx.Response(200, json={"subsonic-response": {"status": "ok", "album": {"id": "a1"}}})
    )
    client = SubsonicClient("http://nd", "me", _pw)
    await client.get_album("a1")
    q = parse_qs(urlparse(str(route.calls.last.request.url)).query)
    assert q["id"] == ["a1"] and q["u"] == ["me"] and q["f"] == ["json"]
    assert q["t"] == [make_token("pw", q["s"][0])]
    await client.aclose()


@respx.mock
async def test_save_play_queue_uses_form_post_when_supported():
    respx.get(url__startswith="http://nd/rest/getOpenSubsonicExtensions").mock(
        return_value=httpx.Response(
            200, json={"subsonic-response": {"status": "ok", "openSubsonicExtensions": [{"name": "formPost"}]}}
        )
    )
    route = respx.post(url__startswith="http://nd/rest/savePlayQueue").mock(
        return_value=httpx.Response(200, json={"subsonic-response": {"status": "ok"}})
    )
    client = SubsonicClient("http://nd", "me", _pw)
    await client.save_play_queue(["a", "b", "a"], "b", 1500)
    request = route.calls.last.request
    form = parse_qs(request.content.decode())
    assert form["id"] == ["a", "b", "a"] and form["current"] == ["b"] and form["position"] == ["1500"]
    assert "t" in parse_qs(urlparse(str(request.url)).query)
    await client.aclose()


@respx.mock
async def test_client_unavailable():
    respx.get(url__startswith="http://nd/rest/ping").mock(side_effect=httpx.ConnectError("down"))
    client = SubsonicClient("http://nd", "me", _pw)
    with pytest.raises(NavidromeUnavailableError):
        await client.ping()
    await client.aclose()


def _ok(**extra):
    return httpx.Response(200, json={"subsonic-response": {"status": "ok", **extra}})


@respx.mock
async def test_star_uses_the_right_parameter_per_kind():
    star = respx.get(url__startswith="http://nd/rest/star").mock(return_value=_ok())
    unstar = respx.get(url__startswith="http://nd/rest/unstar").mock(return_value=_ok())
    client = SubsonicClient("http://nd", "me", _pw)
    await client.set_starred("album", "al1", True)
    assert parse_qs(urlparse(str(star.calls.last.request.url)).query)["albumId"] == ["al1"]
    await client.set_starred("song", "s1", False)
    assert parse_qs(urlparse(str(unstar.calls.last.request.url)).query)["id"] == ["s1"]
    await client.aclose()


@respx.mock
async def test_scrobble_and_rating_params():
    scrobble = respx.get(url__startswith="http://nd/rest/scrobble").mock(return_value=_ok())
    rating = respx.get(url__startswith="http://nd/rest/setRating").mock(return_value=_ok())
    client = SubsonicClient("http://nd", "me", _pw)
    await client.scrobble("s1", True, 1234)
    q = parse_qs(urlparse(str(scrobble.calls.last.request.url)).query)
    assert q["id"] == ["s1"] and q["submission"] == ["true"] and q["time"] == ["1234"]
    await client.set_rating("s1", 9)
    assert parse_qs(urlparse(str(rating.calls.last.request.url)).query)["rating"] == ["5"]
    await client.aclose()


@respx.mock
async def test_update_playlist_sends_repeated_params():
    respx.get(url__startswith="http://nd/rest/getOpenSubsonicExtensions").mock(return_value=_ok(openSubsonicExtensions=[]))
    route = respx.get(url__startswith="http://nd/rest/updatePlaylist").mock(return_value=_ok())
    client = SubsonicClient("http://nd", "me", _pw)
    await client.update_playlist("p1", name="New", add_song_ids=["a", "b"], remove_indexes=[0, 3])
    q = parse_qs(urlparse(str(route.calls.last.request.url)).query)
    assert q["playlistId"] == ["p1"] and q["name"] == ["New"]
    assert q["songIdToAdd"] == ["a", "b"] and q["songIndexToRemove"] == ["0", "3"]
    await client.aclose()


@respx.mock
async def test_create_playlist_returns_created_playlist():
    respx.get(url__startswith="http://nd/rest/getOpenSubsonicExtensions").mock(return_value=_ok(openSubsonicExtensions=[]))
    respx.get(url__startswith="http://nd/rest/createPlaylist").mock(
        return_value=_ok(playlist={"id": "p9", "name": "Mix", "songCount": 2})
    )
    client = SubsonicClient("http://nd", "me", _pw)
    playlist = await client.create_playlist("Mix", ["a", "b"])
    assert playlist.id == "p9" and playlist.song_count == 2
    await client.aclose()
