"""Queue persistence.

The queue itself (song ids, current song, position) lives in Navidrome's play
queue (getPlayQueue / savePlayQueue), so other Subsonic clients can resume it.
SQLite only keeps what Navidrome cannot store: exact current index (the same
song may appear twice), shuffle/repeat modes, pre-shuffle order and the
selected Cast device.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import Protocol

from casthome.db import Database
from casthome.queue.logic import QueueModel, RepeatMode
from casthome.subsonic.client import SubsonicClient
from casthome.subsonic.models import Song
from casthome.subsonic.tokens import CLIENT_NAME

log = logging.getLogger(__name__)

STATE_KEY = "player"


@dataclass
class LoadedQueue:
    model: QueueModel[Song]
    position: float
    device_uuid: str | None
    changed: str | None


class QueueStore(Protocol):
    async def load(self) -> LoadedQueue: ...
    async def save(self, model: QueueModel[Song], position: float, device_uuid: str | None) -> None: ...
    async def fetch_if_changed_elsewhere(self, last_changed: str | None) -> LoadedQueue | None: ...


class NavidromeQueueStore:
    def __init__(self, db: Database, client: SubsonicClient) -> None:
        self._db = db
        self._client = client

    async def _local(self) -> dict:
        return await self._db.get_state(STATE_KEY, {}) or {}

    async def save(self, model: QueueModel[Song], position: float, device_uuid: str | None) -> None:
        ids = [e.item.id for e in model.entries]
        radio_source = model.radio_source if model.radio else None
        current = model.current
        original_positions: list[int] | None = None
        if model.original_order is not None:
            pos_by_uid = {e.uid: i for i, e in enumerate(model.entries)}
            original_positions = [pos_by_uid[u] for u in model.original_order if u in pos_by_uid]
        await self._db.set_state(
            STATE_KEY,
            {
                "ids": ids,
                "index": model.index,
                "queued_positions": [i for i, e in enumerate(model.entries) if e.queued],
                "context_name": model.context_name,
                "radio": model.radio,
                "radio_source": radio_source,
                "repeat": model.repeat.value,
                "shuffle": model.shuffle,
                "original_positions": original_positions,
                "device_uuid": device_uuid,
                "position": position,
            },
        )
        await self._client.save_play_queue(ids, current.item.id if current else None, int(position * 1000))

    async def load(self) -> LoadedQueue:
        local = await self._local()
        remote = await self._client.get_play_queue()
        return self._merge(local, remote.songs, remote.current_id, remote.position_ms, remote.changed)

    async def fetch_if_changed_elsewhere(self, last_changed: str | None) -> LoadedQueue | None:
        remote = await self._client.get_play_queue()
        if remote.changed == last_changed or remote.changed_by == CLIENT_NAME:
            return None
        log.info("Navidrome play queue was changed by %s; reloading it", remote.changed_by)
        local = await self._local()
        return self._merge(local, remote.songs, remote.current_id, remote.position_ms, remote.changed)

    @staticmethod
    def _merge(
        local: dict, songs: list[Song], current_id: str | None, position_ms: int, changed: str | None
    ) -> LoadedQueue:
        model: QueueModel[Song] = QueueModel()
        model.repeat = RepeatMode(local.get("repeat", "off"))
        model.entries = model._wrap(songs)
        ids = [s.id for s in songs]
        same_queue = local.get("ids") == ids
        index: int | None = None
        if same_queue and local.get("index") is not None and local["index"] < len(ids):
            index = local["index"]
        elif current_id in ids:
            index = ids.index(current_id)  # type: ignore[arg-type]
        elif ids:
            index = 0
        model.index = index
        if same_queue:
            # Navidrome only stores a flat list: restore the "next in queue" split.
            for position in local.get("queued_positions") or []:
                if 0 <= position < len(model.entries) and position != index:
                    model.entries[position] = replace(model.entries[position], queued=True)
            model.context_name = local.get("context_name")
            model.radio = bool(local.get("radio"))
            model.radio_source = local.get("radio_source")
        if same_queue and local.get("shuffle"):
            model.shuffle = True
            positions = local.get("original_positions") or []
            if sorted(positions) == list(range(len(ids))):
                model.original_order = [model.entries[p].uid for p in positions]
            else:
                model.original_order = [e.uid for e in model.entries]
        return LoadedQueue(
            model=model,
            position=position_ms / 1000,
            device_uuid=local.get("device_uuid"),
            changed=changed,
        )
