import pytest

from casthome.auth.credentials import CredentialStore
from casthome.auth.crypto import SecretBox
from casthome.auth.sessions import TOUCH_INTERVAL_S, SessionStore
from casthome.db import Database

DAY = 86400.0


class Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
async def db():
    database = Database(":memory:")
    await database.open()
    yield database
    await database.close()


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def store(db, clock) -> SessionStore:
    return SessionStore(db, remember_seconds=365 * DAY, short_seconds=12 * 3600, clock=clock)


async def test_create_and_touch(store):
    token, session = await store.create(persistent=True, user_agent="UA")
    result = await store.touch(token)
    assert result is not None and result.session.id == session.id
    assert result.renewed is False  # within the throttle interval


async def test_unknown_token(store):
    assert await store.touch("nope") is None


async def test_token_is_not_stored_in_clear(store, db):
    token, _ = await store.create(persistent=True)
    async with db.conn.execute("SELECT token_hash FROM sessions") as cur:
        row = await cur.fetchone()
    assert token.encode() not in row["token_hash"]


async def test_sliding_expiry_keeps_active_session_alive(store, clock):
    token, session = await store.create(persistent=True)
    # Use the session every 300 days: it never expires although the lifetime is 365 days.
    for _ in range(5):
        clock.now += 300 * DAY
        result = await store.touch(token)
        assert result is not None and result.renewed
        assert result.session.expires_at == clock.now + 365 * DAY


async def test_persistent_session_expires_when_unused(store, clock):
    token, _ = await store.create(persistent=True)
    clock.now += 366 * DAY
    assert await store.touch(token) is None
    assert await store.list() == []


async def test_short_session_idle_timeout(store, clock):
    token, _ = await store.create(persistent=False)
    clock.now += 11 * 3600
    assert (await store.touch(token)) is not None
    clock.now += 11 * 3600  # still alive: the idle timeout slid on the last touch
    assert (await store.touch(token)) is not None
    clock.now += 13 * 3600
    assert await store.touch(token) is None


async def test_touch_throttles_writes(store, clock):
    token, _ = await store.create(persistent=True)
    clock.now += TOUCH_INTERVAL_S - 1
    assert (await store.touch(token)).renewed is False
    clock.now += 2
    assert (await store.touch(token)).renewed is True


async def test_revoke(store):
    token, session = await store.create(persistent=True)
    other_token, _ = await store.create(persistent=False)
    assert await store.revoke(session.id) is True
    assert await store.touch(token) is None
    assert await store.touch(other_token) is not None
    assert await store.revoke(session.id) is False


async def test_revoke_all(store):
    tokens = [(await store.create(persistent=True))[0] for _ in range(3)]
    await store.revoke_all()
    for token in tokens:
        assert await store.touch(token) is None


async def test_credentials_roundtrip_and_wrong_key(db):
    creds = CredentialStore(db, SecretBox("k" * 40))
    await creds.set_password("sesame")
    async with db.conn.execute("SELECT password_enc FROM credentials") as cur:
        assert b"sesame" not in (await cur.fetchone())["password_enc"]
    assert await CredentialStore(db, SecretBox("k" * 40)).get_password() == "sesame"
    assert await CredentialStore(db, SecretBox("z" * 40)).get_password() is None
