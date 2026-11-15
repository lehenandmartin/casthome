"""Limit on password guesses."""

from __future__ import annotations

from casthome.auth.throttle import LoginThrottle, retry_after


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_blocks_after_the_last_attempt_until_the_first_expires() -> None:
    clock = Clock()
    t = LoginThrottle(max_attempts=3, window_s=60, clock=clock)
    assert [t.check("a") for _ in range(3)] == [None, None, None]
    clock.now += 10
    assert t.check("a") == 50  # the first guess expires 60 s after it was made
    assert t.check("b") is None  # per address
    clock.now += 51
    assert t.check("a") is None


def test_a_correct_password_clears_the_address() -> None:
    t = LoginThrottle(max_attempts=2, window_s=60, clock=Clock())
    t.check("a")
    t.check("a")
    t.passed("a")
    assert t.check("a") is None


def test_expired_addresses_are_forgotten() -> None:
    clock = Clock()
    t = LoginThrottle(max_attempts=3, window_s=60, clock=clock)
    for i in range(50):
        t.check(f"10.0.0.{i}")
    assert t.tracked() == 50
    clock.now += 61
    t.check("10.0.1.1")
    assert t.tracked() == 1


def test_the_table_is_bounded() -> None:
    t = LoginThrottle(max_attempts=3, window_s=60, max_addresses=10, clock=Clock())
    for i in range(25):
        t.check(f"10.0.0.{i}")
    assert t.tracked() == 10


def test_retry_after_is_whole_seconds_at_least_one() -> None:
    assert retry_after(0.2) == "1"
    assert retry_after(41.3) == "42"
