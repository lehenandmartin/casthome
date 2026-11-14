"""First-run setup, access modes and settings, through the HTTP API."""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from casthome.appconfig import hash_password, is_local_address, load_secret_key, verify_password
from casthome.config import Settings
from casthome.main import create_app

ND = "http://nd.lan:4533"
GOOD = "sesame"
NAVIDROME = {"url": ND, "public_url": "", "username": "me", "password": GOOD}


def _subsonic(request: httpx.Request) -> httpx.Response:
    q = parse_qs(urlparse(str(request.url)).query)
    salt, token = q.get("s", [""])[0], q.get("t", [""])[0]
    if hashlib.md5((GOOD + salt).encode()).hexdigest() != token:
        body = {"status": "failed", "error": {"code": 40, "message": "Wrong username or password"}}
    else:
        body = {"status": "ok", "type": "navidrome", "serverVersion": "0.64.2"}
    return httpx.Response(200, json={"subsonic-response": body})


def make_settings(tmp_path: Path, **env: str) -> Settings:
    return Settings(_env_file=None, data_dir=tmp_path, frontend_dist=tmp_path / "none", **env)  # type: ignore[call-arg]


class Client:
    """One browser: its own cookies and address."""

    def __init__(self, app, host: str = "81.250.10.7") -> None:  # type: ignore[no-untyped-def]
        transport = httpx.ASGITransport(app=app, client=(host, 50000))
        self.http = httpx.AsyncClient(transport=transport, base_url="http://casthome")

    async def __aenter__(self) -> httpx.AsyncClient:
        return self.http

    async def __aexit__(self, *_exc: object) -> None:
        await self.http.aclose()


@pytest.fixture
async def app_factory(tmp_path: Path):  # type: ignore[no-untyped-def]
    apps = []

    async def build(**env: str):  # type: ignore[no-untyped-def]
        app = create_app(make_settings(tmp_path, **env), start_services=False)
        await app.state.ctx.open()
        apps.append(app)
        return app

    with respx.mock(assert_all_called=False) as router:
        router.route(url__startswith=f"{ND}/rest/").mock(side_effect=_subsonic)
        yield build
    for app in apps:
        await app.state.ctx.db.close()


async def finish_setup(http: httpx.AsyncClient, mode: str = "password", password: str | None = "letmein") -> httpx.Response:
    return await http.post(
        "/api/setup",
        json={"navidrome": NAVIDROME, "access": {"mode": mode, "password": password, "remember": True}},
    )


async def test_fresh_install_runs_the_setup_then_signs_in(app_factory) -> None:  # type: ignore[no-untyped-def]
    app = await app_factory()
    async with Client(app) as http:
        status = (await http.get("/api/status")).json()
        assert status == {"setup_required": True, "setup": {"navidrome": True, "access": True}, "signed_in": False}
        assert (await http.get("/api/auth/me")).json()["code"] == "setup_required"

        bad = {**NAVIDROME, "password": "nope"}
        r = await http.post("/api/setup/test", json=bad)
        assert r.status_code == 400 and r.json()["code"] == "navidrome_rejected_credentials"
        assert (await http.post("/api/setup/test", json=NAVIDROME)).json() == {"ok": True}

        r = await finish_setup(http)
        assert r.status_code == 200 and "casthome_session" in r.cookies
        assert (await http.get("/api/status")).json()["signed_in"] is True
        me = (await http.get("/api/auth/me")).json()
        assert me["username"] == "me" and me["access_mode"] == "password" and not me["open_session"]
        assert (await finish_setup(http)).json()["code"] == "setup_done"

    ctx = app.state.ctx
    assert ctx.config.navidrome.public_url == ND  # blank: same as the server URL
    assert ctx.subsonic.base_url == ND
    assert await ctx.credentials.get_password() == GOOD

    async with Client(app) as other:
        assert (await other.get("/api/home")).json()["code"] == "not_signed_in"
        r = await other.post("/api/auth/login", json={"password": GOOD})
        assert r.status_code == 401  # the Navidrome password is not the CastHome one
        assert (await other.post("/api/auth/login", json={"password": "letmein"})).status_code == 200
        assert (await other.get("/api/auth/me")).status_code == 200


async def test_setup_rejects_a_local_cast_url_and_short_password(app_factory) -> None:  # type: ignore[no-untyped-def]
    app = await app_factory()
    async with Client(app) as http:
        r = await http.post("/api/setup/test", json={**NAVIDROME, "public_url": "http://localhost:4533"})
        assert r.json()["code"] == "cast_url_local"
        r = await finish_setup(http, password="abc")
        assert r.json()["code"] == "password_too_short"
        assert (await finish_setup(http, password=None)).json()["code"] == "password_required"
    assert app.state.ctx.config.navidrome is None  # nothing saved


async def test_open_access_needs_no_sign_in(app_factory) -> None:  # type: ignore[no-untyped-def]
    app = await app_factory()
    async with Client(app) as http:
        r = await finish_setup(http, mode="open", password=None)
        assert r.status_code == 200 and "casthome_session" not in r.cookies
    async with Client(app) as anyone:
        assert (await anyone.get("/api/status")).json()["signed_in"] is True
        assert (await anyone.get("/api/auth/me")).json()["open_session"] is True


async def test_lan_access_lets_local_clients_in_only(app_factory) -> None:  # type: ignore[no-untyped-def]
    app = await app_factory()
    async with Client(app, host="192.168.1.20") as http:
        assert (await finish_setup(http, mode="lan")).status_code == 200
    async with Client(app, host="192.168.1.30") as local:
        assert (await local.get("/api/auth/me")).json()["open_session"] is True
    async with Client(app, host="81.250.10.9") as remote:
        assert (await remote.get("/api/auth/me")).status_code == 401
        assert (await remote.post("/api/auth/login", json={"password": "letmein"})).status_code == 200
        assert (await remote.get("/api/auth/me")).json()["open_session"] is False


async def test_changing_access_needs_the_current_password(app_factory) -> None:  # type: ignore[no-untyped-def]
    app = await app_factory()
    async with Client(app) as http, Client(app) as other:
        await finish_setup(http)
        await other.post("/api/auth/login", json={"password": "letmein"})

        r = await http.put("/api/settings/access", json={"mode": "password", "password": "newpass"})
        assert r.status_code == 403
        r = await http.put(
            "/api/settings/access",
            json={"mode": "password", "password": "newpass", "current_password": "letmein"},
        )
        assert r.status_code == 200
        # The new password signs the other devices out, not this one.
        assert (await other.get("/api/auth/me")).status_code == 401
        assert (await http.get("/api/auth/me")).status_code == 200

        r = await http.put("/api/settings/access", json={"mode": "open", "current_password": "newpass"})
        assert r.status_code == 200
        assert not app.state.ctx.config.has_password
        # Back to a password from open access: none is set, so one is needed.
        r = await http.put("/api/settings/access", json={"mode": "password"})
        assert r.json()["code"] == "password_required"


async def test_saved_password_never_goes_to_another_server(app_factory) -> None:  # type: ignore[no-untyped-def]
    app = await app_factory()
    async with Client(app) as http:
        await finish_setup(http)
        same = {**NAVIDROME, "password": None, "public_url": "http://192.168.1.10:4533"}
        assert (await http.put("/api/settings/navidrome", json=same)).json() == {"ok": True}
        assert app.state.ctx.media._config.public_base_url == "http://192.168.1.10:4533"
        moved = {**same, "url": "http://evil.example"}
        assert (await http.put("/api/settings/navidrome", json=moved)).json()["code"] == "password_required"
        settings = (await http.get("/api/settings")).json()
        assert settings["navidrome"]["url"] == ND and settings["navidrome"]["has_password"] is True


async def test_environment_values_are_imported_and_locked(app_factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    app = await app_factory(navidrome_url=ND, navidrome_username="me", navidrome_password=GOOD)
    ctx = app.state.ctx
    assert sorted(ctx.config.locked) == ["password", "url", "username"]
    assert await ctx.setup_needs() == {"navidrome": False, "access": True}
    async with Client(app) as http:
        # Only the access step is left; locked values in the form are ignored.
        r = await http.post(
            "/api/setup", json={"access": {"mode": "password", "password": "letmein"}}
        )
        assert r.status_code == 200
        r = await http.put("/api/settings/navidrome", json={"url": "http://other", "username": "x"})
        assert r.status_code == 200 and ctx.config.navidrome.url == ND
    # Imported into the database: still there without the environment.
    await ctx.db.close()
    again = await app_factory()
    assert again.state.ctx.config.navidrome.url == ND


async def test_rejected_navidrome_password_keeps_browsers_signed_in(app_factory) -> None:  # type: ignore[no-untyped-def]
    app = await app_factory()
    ctx = app.state.ctx
    async with Client(app) as http:
        await finish_setup(http)
        await ctx.credentials.set_password("changed-on-navidrome")
        r = await http.get("/api/playlists")
        assert r.status_code == 502 and r.json()["code"] == "navidrome_credentials_rejected"
        assert ctx.server_snapshot() == {"navidrome_rejected": True}
        assert (await http.get("/api/auth/me")).status_code == 200


def test_secret_key_is_generated_once_and_env_key_is_kept(tmp_path: Path) -> None:
    first = load_secret_key(make_settings(tmp_path))
    assert len(first) >= 32 and load_secret_key(make_settings(tmp_path)) == first
    env_key = "k" * 40
    other = tmp_path / "other"
    assert load_secret_key(make_settings(other, app_secret_key=env_key)) == env_key
    # Written down, so removing APP_SECRET_KEY later keeps the same key.
    assert load_secret_key(make_settings(other)) == env_key


def test_password_hash_and_local_addresses() -> None:
    stored = hash_password("letmein")
    assert verify_password("letmein", stored) and not verify_password("other", stored)
    assert not verify_password("x", "garbage")
    for host in ("192.168.1.2", "10.0.0.3", "127.0.0.1", "::1", "fd00::1", "::ffff:192.168.1.2", "169.254.1.1"):
        assert is_local_address(host), host
    for host in ("81.250.10.7", "8.8.8.8", None, "testclient"):
        assert not is_local_address(host), host


async def test_playback_options_are_saved_and_applied(app_factory) -> None:  # type: ignore[no-untyped-def]
    app = await app_factory()
    ctx = app.state.ctx
    async with Client(app) as http:
        await finish_setup(http)
        playback = (await http.get("/api/settings")).json()["playback"]
        assert playback == {
            "stream_format": "raw", "max_bitrate": 0, "preload_next": True, "known_hosts": [], "locked": []
        }
        body = {"stream_format": "mp3", "max_bitrate": 192, "preload_next": False, "known_hosts": [" 192.168.1.20 ", "tv.lan"]}
        assert (await http.put("/api/settings/playback", json=body)).json() == {"ok": True}
        assert ctx.media._config.stream_format == "mp3" and ctx.media._config.max_bitrate == 192
        assert ctx.coordinator.preload_enabled is False
        assert ctx.cast._known_hosts == ["192.168.1.20", "tv.lan"]
        bad = {**body, "known_hosts": ["not a host!"]}
        assert (await http.put("/api/settings/playback", json=bad)).json()["code"] == "invalid_host"
        assert (await http.put("/api/settings/playback", json={**body, "stream_format": "wav"})).status_code == 400
    # Saved: a restart keeps them.
    await ctx.db.close()
    again = await app_factory()
    assert again.state.ctx.config.playback.stream_format == "mp3"
    assert again.state.ctx.coordinator.preload_enabled is False


async def test_playback_options_set_in_the_environment_are_locked(app_factory) -> None:  # type: ignore[no-untyped-def]
    app = await app_factory(stream_format="opus")
    ctx = app.state.ctx
    assert ctx.config.playback_locked == ["stream_format"]
    async with Client(app) as http:
        await finish_setup(http)
        body = {"stream_format": "mp3", "max_bitrate": 128, "preload_next": True, "known_hosts": []}
        assert (await http.put("/api/settings/playback", json=body)).status_code == 200
    assert ctx.config.playback.stream_format == "opus" and ctx.config.playback.max_bitrate == 128
