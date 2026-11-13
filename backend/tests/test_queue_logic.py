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


def ids(q: QueueModel[str]) -> str:
    return "".join(q.items)


def queued(q: QueueModel[str]) -> str:
    return "".join(e.item for e in q.entries if e.queued)


class TestAddToQueue:
    def test_goes_before_the_rest_of_the_album(self):
        q = make("abcde", 1)
        assert q.add(["x"], AddMode.QUEUE) is False
        assert ids(q) == "abxcde" and q.index == 1 and queued(q) == "x"

    def test_keeps_the_order_you_added_them_in(self):
        q = make("abcde", 1)
        q.add(["x"], AddMode.QUEUE)
        q.add(["y", "z"], AddMode.QUEUE)
        assert ids(q) == "abxyzcde" and queued(q) == "xyz"

    def test_plays_queued_then_resumes_album(self):
        q = make("abcd", 0)
        q.add(["x", "y"], AddMode.QUEUE)
        order = []
        while (n := q.next_index(natural=True)) is not None:
            q.jump(n)
            order.append(q.current.item)
        assert "".join(order) == "xybcd"
        assert queued(q) == ""  # consumed as they played

    def test_into_empty_queue_starts_there(self):
        q: QueueModel[str] = QueueModel()
        assert q.add(["x", "y"], AddMode.QUEUE) is True
        assert q.index == 0 and queued(q) == ""

    def test_duplicates_get_distinct_uids(self):
        q = make("aa")
        assert q.entries[0].uid != q.entries[1].uid


class TestPlayNow:
    def test_plays_now_and_keeps_queue_and_album(self):
        q = make("abc", 0)
        q.add(["x"], AddMode.QUEUE)
        assert q.add(["n"], AddMode.NOW) is True
        assert q.current.item == "n" and ids(q) == "anxbc" and queued(q) == "x"

    def test_several_tracks_rest_go_to_front_of_queue(self):
        q = make("abc", 0)
        q.add(["x"], AddMode.QUEUE)
        q.add(["n1", "n2"], AddMode.NOW)
        assert q.current.item == "n1" and queued(q) == "n2x"


class TestPlayContext:
    def test_new_album_keeps_next_in_queue(self):
        q = make("abc", 0)
        q.add(["x", "y"], AddMode.QUEUE)
        q.play_context(list("klmn"), 1)
        assert q.current.item == "l" and ids(q) == "klxymn" and queued(q) == "xy"

    def test_new_album_without_queue(self):
        q = make("abc", 2)
        q.play_context(list("kl"), 0)
        assert ids(q) == "kl" and q.index == 0

    def test_current_queued_track_is_not_kept_twice(self):
        q = make("ab", 0)
        q.add(["x"], AddMode.QUEUE)
        q.jump(1)  # x plays now
        q.play_context(list("kl"), 0)
        assert ids(q) == "kl"


class TestJumpKeepsQueue:
    def test_jumping_ahead_in_the_album_keeps_queue_next(self):
        q = make("abcdef", 0)
        q.add(["x"], AddMode.QUEUE)
        q.jump(ids(q).index("e"))
        assert q.current.item == "e" and ids(q)[q.index + 1] == "x"

    def test_going_back_keeps_queue_next(self):
        q = make("abcd", 2)
        q.add(["x"], AddMode.QUEUE)
        q.jump(q.previous_index())
        assert q.current.item == "b" and ids(q)[q.index + 1] == "x"

    def test_tapping_a_queued_track_plays_it_and_keeps_the_others(self):
        q = make("abc", 0)
        q.add(["x", "y"], AddMode.QUEUE)
        q.jump(ids(q).index("y"))
        assert q.current.item == "y" and queued(q) == "x" and ids(q)[q.index + 1] == "x"


class TestClearQueued:
    def test_clears_only_next_in_queue(self):
        q = make("abc", 0)
        q.add(["x", "y"], AddMode.QUEUE)
        q.clear_queued()
        assert ids(q) == "abc" and q.index == 0


class TestMoveBetweenSections:
    def test_move_album_track_into_queue(self):
        q = make("abcde", 0)
        q.add(["x"], AddMode.QUEUE)
        q.move(ids(q).index("d"), 1, queued=True)
        assert queued(q) == "dx" and ids(q) == "adxbce"

    def test_move_queued_track_into_album(self):
        q = make("abcd", 0)
        q.add(["x", "y"], AddMode.QUEUE)
        q.move(ids(q).index("x"), ids(q).index("c"), queued=False)
        assert queued(q) == "y" and ids(q) == "aybcxd"

    def test_queue_stays_first_even_if_dropped_lower(self):
        q = make("abcd", 0)
        q.add(["x"], AddMode.QUEUE)
        q.move(ids(q).index("x"), 4)  # section unchanged: still queued
        assert ids(q) == "axbcd"


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

    def test_next_in_queue_is_never_shuffled(self):
        q = make("abcdefgh", 0)
        q.add(["x", "y", "z"], AddMode.QUEUE)
        q.set_shuffle(True, random.Random(4))
        assert ids(q)[1:4] == "xyz" and queued(q) == "xyz"
        q.set_shuffle(False)
        assert ids(q) == "axyzbcdefgh"

    def test_added_while_shuffled_stays_next_after_unshuffle(self):
        q = make("abcd", 1)
        q.set_shuffle(True, random.Random(3))
        q.add(["x"], AddMode.QUEUE)
        q.remove(q.items.index("d"))
        q.set_shuffle(False)
        assert ids(q) == "abxc" and queued(q) == "x"

    def test_replace_while_shuffled_shuffles_new_queue(self):
        q = make("ab")
        q.set_shuffle(True)
        q.play_context(list("abcdefghij"), 0)
        assert q.current.item == "a"
        q.set_shuffle(False)
        assert q.items == list("abcdefghij")


def test_clear():
    q = make()
    q.clear()
    assert len(q) == 0 and q.index is None
