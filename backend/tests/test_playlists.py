"""Playlists list: most recently changed first."""

from __future__ import annotations

from types import SimpleNamespace

from casthome.api.playlists import list_playlists
from casthome.subsonic.models import Playlist


class FakeSubsonic:
    async def get_playlists(self) -> list[Playlist]:
        return [
            Playlist(id="old", name="Old", changed="2024-01-02T10:00:00Z"),
            Playlist(id="none", name="Never changed", changed=None),
            Playlist(id="new", name="New", changed="2026-11-14T09:30:00Z"),
            Playlist(id="mid", name="Mid", changed="2025-06-01T00:00:00Z"),
        ]


async def test_playlists_come_most_recently_changed_first() -> None:
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ctx=SimpleNamespace(subsonic=FakeSubsonic()))))
    result = await list_playlists(request)  # type: ignore[arg-type]
    assert [p["id"] for p in result] == ["new", "mid", "old", "none"]
