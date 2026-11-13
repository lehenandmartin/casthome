"""Pure play-queue logic: no I/O, fully unit-tested.

The queue works like Spotify's, in two parts after the current track:

    [played …] [current] [next in queue …] [next from the album/playlist …]

- "Next in queue" holds the tracks you added yourself ("Add to queue"). They
  always play right after the current track, in the order you added them,
  before the rest of what you were listening to. They are never shuffled,
  and starting another album keeps them.
- "Next from …" (the *context*) is the album, playlist or list you started.

Entries flagged `queued` are exactly the not-yet-played "next in queue"
tracks: the flag is cleared when a track becomes current, and `_normalize`
keeps every queued entry right after the current one.

Entries carry a stable `uid` so the same song can appear several times and
the pre-shuffle order can be restored.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Generic, TypeVar

T = TypeVar("T")


class RepeatMode(StrEnum):
    OFF = "off"
    ALL = "all"
    ONE = "one"


class AddMode(StrEnum):
    NOW = "now"  # play it right away, then carry on with the queue
    QUEUE = "queue"  # add to "next in queue"


@dataclass(frozen=True)
class Entry(Generic[T]):
    uid: int
    item: T
    queued: bool = False  # in "next in queue" (added by hand, not played yet)


@dataclass
class QueueModel(Generic[T]):
    entries: list[Entry[T]] = field(default_factory=list)
    index: int | None = None
    repeat: RepeatMode = RepeatMode.OFF
    shuffle: bool = False
    # uids in their order before shuffle was enabled (None when not shuffled)
    original_order: list[int] | None = None
    # What "next from …" refers to (album or playlist name), for display.
    context_name: str | None = None
    _uids: itertools.count = field(default_factory=lambda: itertools.count(1), repr=False)

    # --- read helpers --------------------------------------------------------

    def __len__(self) -> int:
        return len(self.entries)

    @property
    def current(self) -> Entry[T] | None:
        if self.index is None or not (0 <= self.index < len(self.entries)):
            return None
        return self.entries[self.index]

    @property
    def items(self) -> list[T]:
        return [e.item for e in self.entries]

    @property
    def queued_count(self) -> int:
        return sum(1 for e in self.entries if e.queued)

    def _wrap(self, items: list[T], queued: bool = False) -> list[Entry[T]]:
        return [Entry(next(self._uids), item, queued) for item in items]

    def _context_start(self) -> int:
        """Position of the first upcoming context entry."""
        base = 0 if self.index is None else self.index + 1
        return base + sum(1 for e in self.entries[base:] if e.queued)

    # --- mutations -----------------------------------------------------------

    def play_context(self, items: list[T], start_index: int = 0, name: str | None = None) -> None:
        """Start a new album/playlist/list. Tracks in "next in queue" are kept
        and play right after the chosen track."""
        self.context_name = name
        pending = [e for i, e in enumerate(self.entries) if e.queued and i != self.index]
        new = self._wrap(items)
        if not new:
            self.entries, self.index = pending, (0 if pending else None)
            self._consume_current()
            self.original_order = [e.uid for e in self.entries] if self.shuffle else None
            return
        start = min(max(start_index, 0), len(new) - 1)
        self.entries = new[: start + 1] + pending + new[start + 1 :]
        self.index = start
        self.original_order = None
        if self.shuffle:
            self._shuffle_context(random.Random(), keep_original=True)

    def replace(self, items: list[T], start_index: int = 0) -> None:
        """Replace everything, "next in queue" included (used when restoring)."""
        self.entries = self._wrap(items)
        self.index = min(max(start_index, 0), len(items) - 1) if items else None
        self.original_order = None
        if self.shuffle:
            self._shuffle_context(random.Random(), keep_original=True)

    def clear(self) -> None:
        self.entries = []
        self.index = None
        self.context_name = None
        self.original_order = [] if self.shuffle else None

    def clear_queued(self) -> None:
        """Empty "next in queue" only (Spotify's "Clear queue")."""
        removed = {e.uid for e in self.entries if e.queued}
        current_uid = self.current.uid if self.current else None
        self.entries = [e for e in self.entries if e.uid not in removed]
        if self.original_order is not None:
            self.original_order = [u for u in self.original_order if u not in removed]
        if current_uid is not None:
            self.index = next(i for i, e in enumerate(self.entries) if e.uid == current_uid)

    def add(self, items: list[T], mode: AddMode) -> bool:
        """Insert items. Returns True when the current entry changed."""
        if not items:
            return False
        if self.index is None:
            # Nothing is current: the items become what is playing.
            new = self._wrap(items)
            start = len(self.entries)
            self.entries.extend(new)
            self._original_insert(new, after_uid=None)
            self.index = start
            return True
        if mode == AddMode.NOW:
            new = self._wrap(items)
            current_uid = self.entries[self.index].uid
            insert_at = self.index + 1
            self.entries[insert_at:insert_at] = new
            self._original_insert(new, after_uid=current_uid)
            self.index = insert_at
            # The first one plays now; any others go to the front of "next in queue".
            for i in range(insert_at + 1, insert_at + len(new)):
                self.entries[i] = replace(self.entries[i], queued=True)
            self._normalize()
            return True
        # Add to the end of "next in queue", i.e. before the rest of the album.
        new = self._wrap(items, queued=True)
        insert_at = self._context_start()
        before_uid = self.entries[insert_at - 1].uid
        self.entries[insert_at:insert_at] = new
        self._original_insert(new, after_uid=before_uid)
        return False

    def remove(self, position: int) -> bool:
        """Remove an entry. Returns True when the current entry was removed."""
        if not (0 <= position < len(self.entries)):
            raise IndexError(position)
        removed = self.entries.pop(position)
        if self.original_order is not None:
            self.original_order.remove(removed.uid)
        if self.index is None:
            return False
        if position < self.index:
            self.index -= 1
            return False
        if position > self.index:
            return False
        # Current removed: the following entry (now at the same position) becomes current.
        if not self.entries:
            self.index = None
        elif self.index >= len(self.entries):
            self.index = 0 if self.repeat == RepeatMode.ALL else None
        self._consume_current()
        self._normalize()
        return True

    def move(self, from_pos: int, to_pos: int, queued: bool | None = None) -> None:
        """Move an entry. `queued` puts it in (True) or out of (False) "next in
        queue"; None keeps its section."""
        n = len(self.entries)
        if not (0 <= from_pos < n and 0 <= to_pos < n):
            raise IndexError((from_pos, to_pos))
        entry = self.entries.pop(from_pos)
        if queued is not None and from_pos != self.index:
            entry = replace(entry, queued=queued)
        self.entries.insert(to_pos, entry)
        if self.index is not None:
            if self.index == from_pos:
                self.index = to_pos
            elif from_pos < self.index <= to_pos:
                self.index -= 1
            elif to_pos <= self.index < from_pos:
                self.index += 1
        if self.index is not None and to_pos <= self.index and entry.queued and entry.uid != self.entries[self.index].uid:
            # Dragged above the current track: it is no longer "next".
            self.entries[to_pos] = replace(entry, queued=False)
        self._normalize()

    def jump(self, position: int) -> None:
        if not (0 <= position < len(self.entries)):
            raise IndexError(position)
        self.index = position
        self._consume_current()
        self._normalize()

    # --- navigation ----------------------------------------------------------

    def next_index(self, natural: bool) -> int | None:
        """Index to play after the current one; None means the queue ended.

        `natural` is True when the track finished by itself: only then does
        repeat-one replay the same track.
        """
        if self.index is None or not self.entries:
            return None
        if natural and self.repeat == RepeatMode.ONE:
            return self.index
        if self.index + 1 < len(self.entries):
            return self.index + 1
        if self.repeat in (RepeatMode.ALL, RepeatMode.ONE):
            return 0
        return None

    def previous_index(self) -> int | None:
        """Index of the previous entry; None means 'restart the current one'."""
        if self.index is None or not self.entries:
            return None
        if self.index > 0:
            return self.index - 1
        if self.repeat == RepeatMode.ALL:
            return len(self.entries) - 1
        return None

    # --- shuffle -------------------------------------------------------------

    def set_shuffle(self, enabled: bool, rng: random.Random | None = None) -> None:
        if enabled == self.shuffle:
            return
        self.shuffle = enabled
        if enabled:
            self._shuffle_context(rng or random.Random(), keep_original=True)
        else:
            self._restore_original()

    def _shuffle_context(self, rng: random.Random, keep_original: bool) -> None:
        """Shuffle the upcoming album/playlist tracks; "next in queue" stays as is."""
        if keep_original or self.original_order is None:
            self.original_order = [e.uid for e in self.entries]
        start = self._context_start()
        upcoming = self.entries[start:]
        rng.shuffle(upcoming)
        self.entries[start:] = upcoming

    def _restore_original(self) -> None:
        order = self.original_order or []
        rank = {uid: i for i, uid in enumerate(order)}
        current_uid = self.current.uid if self.current else None
        self.entries.sort(key=lambda e: rank.get(e.uid, len(rank)))
        self.original_order = None
        if current_uid is not None:
            self.index = next(i for i, e in enumerate(self.entries) if e.uid == current_uid)
        self._normalize()

    def _original_insert(self, new: list[Entry[T]], after_uid: int | None) -> None:
        if self.original_order is None:
            return
        uids = [e.uid for e in new]
        if after_uid is None or after_uid not in self.original_order:
            self.original_order.extend(uids)
        else:
            pos = self.original_order.index(after_uid) + 1
            self.original_order[pos:pos] = uids

    # --- invariants ----------------------------------------------------------

    def _consume_current(self) -> None:
        """A track that becomes current is no longer "next in queue"."""
        if self.index is not None and 0 <= self.index < len(self.entries) and self.entries[self.index].queued:
            self.entries[self.index] = replace(self.entries[self.index], queued=False)

    def _normalize(self) -> None:
        """Keep every "next in queue" entry right after the current one, in order."""
        if self.index is None:
            return
        current = self.entries[self.index]
        queued = [e for e in self.entries if e.queued and e.uid != current.uid]
        if not queued:
            return
        rest = [e for e in self.entries if not e.queued or e.uid == current.uid]
        position = next(i for i, e in enumerate(rest) if e.uid == current.uid)
        self.entries = rest[: position + 1] + queued + rest[position + 1 :]
        self.index = position
