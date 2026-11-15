"""The pychromecast listener: which connection statuses reach the player."""

from __future__ import annotations

from typing import Any

from pychromecast.socket_client import ConnectionStatus

from casthome.cast.device import _Listener
from casthome.cast.types import ConnectionEvent


class _Loop:
    """Runs call_soon_threadsafe callbacks at once."""

    def call_soon_threadsafe(self, fn: Any, *args: Any) -> None:
        fn(*args)


def _statuses(*names: str) -> list[object]:
    events: list[object] = []
    listener = _Listener(_Loop(), events.append)  # type: ignore[arg-type]
    for name in names:
        listener.new_connection_status(ConnectionStatus(name, None, None))
    return events


def test_connecting_is_not_reported_as_a_loss() -> None:
    # What a Google Home Mini sends when CastHome connects to it.
    assert _statuses("CONNECTING", "CONNECTED") == [ConnectionEvent(connected=True)]


def test_a_real_loss_and_the_reconnection_are_reported() -> None:
    assert _statuses("CONNECTED", "LOST", "CONNECTING", "FAILED", "CONNECTING", "CONNECTED") == [
        ConnectionEvent(connected=True),
        ConnectionEvent(connected=False),
        ConnectionEvent(connected=False),
        ConnectionEvent(connected=True),
    ]
