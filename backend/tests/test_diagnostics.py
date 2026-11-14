import logging

from casthome.api import diagnostics
from tests.test_setup import Client, finish_setup

ERROR = {"message": "TypeError: x is null", "stack": "at a (App.svelte:1)\nat b (main.ts:2)", "page": "#/album/1", "agent": "iPhone"}


async def test_interface_errors_are_logged(app_factory, caplog) -> None:  # type: ignore[no-untyped-def]
    app = await app_factory()
    async with Client(app) as http:
        await finish_setup(http)
        with caplog.at_level(logging.WARNING, logger="casthome.client"):
            assert (await http.post("/api/client-errors", json=ERROR)).status_code == 204
    assert "TypeError: x is null" in caplog.text and "#/album/1" in caplog.text and "App.svelte:1" in caplog.text


async def test_interface_errors_need_a_session_and_are_limited(app_factory, caplog, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    app = await app_factory()
    async with Client(app) as http:
        assert (await http.post("/api/client-errors", json=ERROR)).status_code == 401
        await finish_setup(http)
        monkeypatch.setattr(diagnostics, "MAX_PER_MINUTE", 2)
        diagnostics._recent.clear()
        with caplog.at_level(logging.WARNING, logger="casthome.client"):
            for _ in range(4):
                assert (await http.post("/api/client-errors", json=ERROR)).status_code == 204
    assert caplog.text.count("TypeError: x is null") == 2
