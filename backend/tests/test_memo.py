import asyncio

import pytest

from casthome.memo import Memo


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


async def test_reuses_the_value_while_fresh_then_loads_again():
    clock = Clock()
    memo: Memo[int] = Memo(60, clock)
    calls = []

    async def load() -> int:
        calls.append(1)
        return len(calls)

    assert await memo.get(load) == 1
    clock.now = 59
    assert await memo.get(load) == 1
    clock.now = 61
    assert await memo.get(load) == 2


async def test_callers_at_the_same_time_share_one_load():
    memo: Memo[str] = Memo(60)
    calls = []

    async def load() -> str:
        calls.append(1)
        await asyncio.sleep(0)
        return "v"

    assert await asyncio.gather(memo.get(load), memo.get(load)) == ["v", "v"]
    assert calls == [1]


async def test_forget_and_failures():
    memo: Memo[int] = Memo(60)

    async def failing() -> int:
        raise RuntimeError("down")

    with pytest.raises(RuntimeError):
        await memo.get(failing)

    async def one() -> int:
        return 1

    async def two() -> int:
        return 2

    assert await memo.get(one) == 1
    memo.forget()
    assert await memo.get(two) == 2


async def test_a_value_loaded_across_a_forget_is_not_kept():
    memo: Memo[int] = Memo(60)
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow() -> int:
        started.set()
        await release.wait()
        return 1

    task = asyncio.create_task(memo.get(slow))
    await started.wait()
    memo.forget()  # e.g. a favourite changed while loading
    release.set()
    assert await task == 1

    async def fresh() -> int:
        return 2

    assert await memo.get(fresh) == 2
