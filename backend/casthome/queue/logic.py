"""Pure play-queue logic: no I/O, fully unit-tested.

Entries carry a stable `uid` so the same song can appear several times and
the pre-shuffle order can be restored.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Generic, TypeVar

T = TypeVar("T")


class RepeatMode(StrEnum):
    OFF = "off"
    ALL = "all"
    ONE = "one"


class AddMode(StrEnum):
    NOW = "now"
    NEXT = "next"
    END = "end"


@dataclass(frozen=True)
class Entry(Generic[T]):
    uid: int
    item: T


@dataclass
class QueueModel(Generic[T]):
    entries: list[Entry[T]] = field(default_factory=list)
    index: int | None = None
    repeat: RepeatMode = RepeatMode.OFF
    shuffle: bool = False
    # uids in their order before shuffle was enabled (None when not shuffled)
    original_order: list[int] | None = None
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

    def _wrap(self, items: list[T]) -> list[Entry[T]]:
        return [Entry(next(self._uids), item) for item in items]

    # --- mutations -----------------------------------------------------------

    def replace(self, items: list[T], start_index: int = 0) -> None:
        self.entries = self._wrap(items)
        self.index = min(max(start_index, 0), len(items) - 1) if items else None
        self.original_order = None
        if self.shuffle:
            self._shuffle_upcoming(random.Random(), keep_original=False)

    def clear(self) -> None:
        self.entries = []
        self.index = None
        self.original_order = [] if self.shuffle else None

    def add(self, items: list[T], mode: AddMode) -> bool:
        """Insert items. Returns True when the current entry changed."""
        if not items:
            return False
        new = self._wrap(items)
        if self.index is None:
            # Nothing is current: append and start at the first added entry.
            start = len(self.entries)
            self.entries.extend(new)
            self._original_extend(new, after_uid=None)
            self.index = start
            return True
        if mode == AddMode.END:
            self.entries.extend(new)
            self._original_extend(new, after_uid=None)
            return False
        current_uid = self.entries[self.index].uid
        insert_at = self.index + 1
        self.entries[insert_at:insert_at] = new
        self._original_extend(new, after_uid=current_uid)
        if mode == AddMode.NOW:
            self.index = insert_at
            return True
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
        return True

    def move(self, from_pos: int, to_pos: int) -> None:
        n = len(self.entries)
        if not (0 <= from_pos < n and 0 <= to_pos < n):
            raise IndexError((from_pos, to_pos))
        entry = self.entries.pop(from_pos)
        self.entries.insert(to_pos, entry)
        if self.index is None:
            return
        if self.index == from_pos:
            self.index = to_pos
        elif from_pos < self.index <= to_pos:
            self.index -= 1
        elif to_pos <= self.index < from_pos:
            self.index += 1

    def jump(self, position: int) -> None:
        if not (0 <= position < len(self.entries)):
            raise IndexError(position)
        self.index = position

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
            self._shuffle_upcoming(rng or random.Random(), keep_original=True)
        else:
            self._restore_original()

    def _shuffle_upcoming(self, rng: random.Random, keep_original: bool) -> None:
        self.original_order = [e.uid for e in self.entries] if keep_original or self.original_order is None else self.original_order
        start = 0 if self.index is None else self.index + 1
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

    def _original_extend(self, new: list[Entry[T]], after_uid: int | None) -> None:
        if self.original_order is None:
            return
        uids = [e.uid for e in new]
        if after_uid is None or after_uid not in self.original_order:
            self.original_order.extend(uids)
        else:
            pos = self.original_order.index(after_uid) + 1
            self.original_order[pos:pos] = uids
