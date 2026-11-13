"""Cast device discovery (mDNS via zeroconf, plus optional known hosts)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

import zeroconf
from pychromecast.discovery import CastBrowser, SimpleCastListener

from casthome.cast.device import CastDevice
from casthome.cast.types import DeviceInfo, EventSink

log = logging.getLogger(__name__)

DevicesChanged = Callable[[list[DeviceInfo]], None]


def _to_info(cast_info: Any) -> DeviceInfo:
    return DeviceInfo(
        uuid=str(cast_info.uuid),
        name=cast_info.friendly_name or str(cast_info.uuid),
        model=cast_info.model_name or "",
        cast_type=cast_info.cast_type or "cast",
        host=cast_info.host,
        port=cast_info.port,
    )


class CastManager:
    def __init__(self, known_hosts: list[str]) -> None:
        self._known_hosts = known_hosts
        self._zconf: zeroconf.Zeroconf | None = None
        self._browser: CastBrowser | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._devices: dict[str, DeviceInfo] = {}
        self.on_devices_changed: DevicesChanged | None = None

    @property
    def devices(self) -> list[DeviceInfo]:
        return sorted(self._devices.values(), key=lambda d: (d.cast_type != "group", d.name.lower()))

    def get(self, uuid: str) -> DeviceInfo | None:
        return self._devices.get(uuid)

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        listener = SimpleCastListener(
            add_callback=self._on_change,
            remove_callback=lambda uuid, _service, _info: self._on_change(uuid, _service),
            update_callback=self._on_change,
        )

        def _start() -> None:
            self._zconf = zeroconf.Zeroconf()
            self._browser = CastBrowser(listener, self._zconf, self._known_hosts or None)
            self._browser.start_discovery()

        await asyncio.to_thread(_start)
        log.info("Cast discovery started")

    async def stop(self) -> None:
        def _stop() -> None:
            if self._browser:
                self._browser.stop_discovery()
            if self._zconf:
                self._zconf.close()

        await asyncio.to_thread(_stop)

    def _on_change(self, _uuid: UUID, _service: str) -> None:
        # Called from the zeroconf thread: snapshot then hop to the event loop.
        assert self._browser is not None and self._loop is not None
        snapshot = {str(u): _to_info(ci) for u, ci in list(self._browser.devices.items())}
        self._loop.call_soon_threadsafe(self._apply, snapshot)

    def _apply(self, snapshot: dict[str, DeviceInfo]) -> None:
        if snapshot == self._devices:
            return
        added = snapshot.keys() - self._devices.keys()
        removed = self._devices.keys() - snapshot.keys()
        for uuid in added:
            log.info("Cast device found: %s (%s)", snapshot[uuid].name, snapshot[uuid].cast_type)
        for uuid in removed:
            log.info("Cast device lost: %s", self._devices[uuid].name)
        self._devices = snapshot
        if self.on_devices_changed:
            self.on_devices_changed(self.devices)

    async def connect(self, uuid: str, sink: EventSink) -> CastDevice:
        if self._browser is None:
            raise RuntimeError("Discovery not started")
        cast_info = self._browser.devices.get(UUID(uuid))
        if cast_info is None:
            raise LookupError(uuid)
        return await CastDevice.connect(_to_info(cast_info), cast_info, self._zconf, sink)
