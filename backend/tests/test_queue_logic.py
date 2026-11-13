import random

import pytest

from casthome.queue.logic import AddMode, QueueModel, RepeatMode


def make(items: str = "abcde", index: int = 0) -> QueueModel[str]:
    q: QueueModel[str] = QueueModel()
    q.replace(list(items), index)
    return q


def test_replace_sets_index_and_clamps():
    assert make("abc", 1).index == 1
    assert make("abc", 10).index == 2
    q: QueueModel[str] = QueueModel()
    q.replace([], 0)
    assert q.index is None and q.current is None


class TestNext:
    def test_advances(self):
        assert make(index=1).next_index(natural=True) == 2

    def test_end_without_repeat(self):
        assert make(index=4).next_index(natural=True) is None

    def test_repeat_all_wraps(self):
        q = make(index=4)
        q.repeat = RepeatMode.ALL
        assert q.next_index(natural=True) == 0

    def test_repeat_one_replays_only_on_natural_end(self):
        q = make(index=2)
        q.repeat = RepeatMode.ONE
        assert q.next_index(natural=True) == 2
        assert q.next_index(natural=False) == 3

    def test_repeat_one_manual_next_wraps_at_end(self):
        q = make(index=4)
        q.repeat = RepeatMode.ONE
        assert q.next_index(natural=False) == 0

    def test_empty(self):
        assert QueueModel().next_index(natural=True) is None


class TestPrevious:
    def test_goes_back(self):
        assert make(index=2).previous_index() == 1

    def test_first_without_repeat_restarts(self):
        assert make(index=0).previous_index() is None

    def test_first_with_repeat_all_wraps(self):
        q = make(index=0)
        q.repeat = RepeatMode.ALL
        assert q.previous_index() == 4


class TestAdd:
    def test_end(self):
        q = make("abc", 1)
        assert q.add(["x"], AddMode.END) is False
        assert q.items == ["a", "b", "c", "x"] and q.index == 1

    def test_next(self):
        q = make("abc", 1)
        assert q.add(["x", "y"], AddMode.NEXT) is False
        assert q.items == ["a", "b", "x", "y", "c"] and q.index == 1

    def test_now(self):
        q = make("abc", 1)
        assert q.add(["x"], AddMode.NOW) is True
        assert q.items == ["a", "b", "x", "c"] and q.current.item == "x"

    def test_into_empty_queue_starts_there(self):
        q: QueueModel[str] = QueueModel()
        assert q.add(["x", "y"], AddMode.END) is True
        assert q.index == 0

    def test_duplicates_get_distinct_uids(self):
        q = make("aa")
        assert q.entries[0].uid != q.entries[1].uid


class TestRemove:
    def test_before_current_shifts_index(self):
        q = make(index=2)
        assert q.remove(0) is False
        assert q.current.item == "c" and q.index == 1

    def test_after_current(self):
        q = make(index=2)
        assert q.remove(4) is False
        assert q.index == 2

    def test_current_moves_to_following(self):
        q = make(index=2)
        assert q.remove(2) is True
        assert q.current.item == "d"

    def test_last_current_ends_queue(self):
        q = make(index=4)
        assert q.remove(4) is True
        assert q.index is None

    def test_last_current_wraps_with_repeat_all(self):
        q = make(index=4)
        q.repeat = RepeatMode.ALL
        q.remove(4)
        assert q.index == 0

    def test_out_of_range(self):
        with pytest.raises(IndexError):
            make().remove(9)


class TestMove:
    @pytest.mark.parametrize(
        ("index", "src", "dst", "expected_items", "expected_index"),
        [
            (2, 2, 0, "cabde", 0),  # moving the current entry
            (2, 0, 4, "bcdea", 1),  # from before to after current
            (2, 4, 0, "eabcd", 3),  # from after to before current
            (2, 3, 4, "abced", 2),  # both after current
            (2, 0, 1, "bacde", 2),  # both before current
            (2, 0, 2, "bcade", 1),  # onto current's position from before
        ],
    )
    def test_move_keeps_current(self, index, src, dst, expected_items, expected_index):
        q = make(index=index)
        current = q.current
        q.move(src, dst)
        assert "".join(q.items) == expected_items
        assert q.index == expected_index
        assert q.current == current


class TestShuffle:
    def test_shuffle_keeps_played_and_current(self):
        q = make("abcdefgh", 2)
        q.set_shuffle(True, random.Random(1))
        assert q.items[:3] == ["a", "b", "c"]
        assert sorted(q.items) == list("abcdefgh")
        assert q.current.item == "c"

    def test_unshuffle_restores_order_and_current(self):
        q = make("abcdefgh", 2)
        q.set_shuffle(True, random.Random(1))
        q.jump(5)
        current = q.current
        q.set_shuffle(False)
        assert q.items == list("abcdefgh")
        assert q.current == current

    def test_items_added_while_shuffled_are_restored_in_place(self):
        q = make("abcd", 1)
        q.set_shuffle(True, random.Random(3))
        q.add(["x"], AddMode.NEXT)
        q.add(["z"], AddMode.END)
        q.remove(q.items.index("d"))
        q.set_shuffle(False)
        assert q.items == ["a", "b", "x", "c", "z"]

    def test_replace_while_shuffled_shuffles_new_queue(self):
        q = make("ab")
        q.set_shuffle(True)
        q.replace(list("abcdefghij"), 0)
        assert q.current.item == "a"
        q.set_shuffle(False)
        assert q.items == list("abcdefghij")


def test_clear():
    q = make()
    q.clear()
    assert len(q) == 0 and q.index is None
