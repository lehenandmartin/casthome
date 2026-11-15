"""Wires all services together; one instance per running app."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from casthome.appconfig import ConfigStore, NavidromeConfig, load_secret_key
from casthome.auth.credentials import CredentialStore
from casthome.auth.crypto import SecretBox
from casthome.auth.sessions import SessionStore
from casthome.background import spawn
from casthome.cast.browser import BrowserTarget, client_id_of
from casthome.cast.manager import CastManager
from casthome.cast.types import ConnectionEvent
from casthome.cast.types import CastTarget, EventSink
from casthome.config import Settings
from casthome.covers import CoverCache
from casthome.memo import Memo
from casthome.db import Database
from casthome.playback.coordinator import Notifier, PlaybackCoordinator
from casthome.playback.media import MediaBuilder, StreamConfig
from casthome.playback.persistence import NavidromeQueueStore
from casthome.playback.radio import make_artist_radio_builder, make_radio_builder
from casthome.scrobble.scrobbler import Scrobbler
from casthome.subsonic.client import SubsonicClient
from casthome.subsonic.models import SearchResult, Song
from casthome.subsonic.native import NativeClient
from casthome.ws.hub import Hub

log = logging.getLogger(__name__)


# Home page: favourites (a large answer, ~0.15 s) and "On repeat" (several
# pages scanned) are reused this long; a favourite changed in CastHome
# forgets the first at once.
STARRED_TTL_S = 60
ON_REPEAT_TTL_S = 120


@dataclass
class AppContext:
    settings: Settings
    db: Database
    config: ConfigStore
    sessions: SessionStore
    credentials: CredentialStore
    subsonic: SubsonicClient
    native: NativeClient
    cast: CastManager
    coordinator: PlaybackCoordinator
    hub: Hub
    media: MediaBuilder
    # Covers converted for the browser (WebP), kept in <data_dir>/covers.
    covers: CoverCache = field(default_factory=lambda: CoverCache(Path('covers')))
    # Slow Navidrome answers the Home page reuses for a short while (api/home.py).
    starred_memo: Memo[SearchResult] = field(default_factory=lambda: Memo(STARRED_TTL_S))
    on_repeat_memo: Memo[list[Song]] = field(default_factory=lambda: Memo(ON_REPEAT_TTL_S))

    @classmethod
    def build(cls, settings: Settings) -> AppContext:
        db = Database(settings.database_path)
        sessions = SessionStore(
            db,
            remember_seconds=settings.session_remember_days * 86400,
            short_seconds=settings.session_short_hours * 3600,
        )
        config = ConfigStore(db, settings)
        credentials = CredentialStore(db, SecretBox(load_secret_key(settings)), settings.navidrome_password)

        async def password() -> str | None:
            # No password until a server and an account are set up.
            return await credentials.get_password() if config.navidrome else None

        # Server and account are filled in by apply_navidrome() once the config is loaded.
        subsonic = SubsonicClient("", "", password)
        native = NativeClient("", "", password, subsonic.http)
        cast = CastManager(settings.known_hosts)
        media = MediaBuilder(
            StreamConfig(
                public_base_url="",
                username="",
                stream_format=settings.stream_format,
                max_bitrate=settings.stream_max_bitrate,
                fallback_format=settings.transcode_fallback_format,
            ),
            password,
        )

        hub = Hub()

        async def connector(uuid: str, sink: EventSink) -> CastTarget:
            client_id = client_id_of(uuid)
            if client_id is not None:
                if not hub.has_client(client_id):
                    raise LookupError(f"browser tab {client_id} is not connected")
                return BrowserTarget(client_id, hub.client_names.get(client_id) or "Web browser", hub, sink)
            return await cast.connect(uuid, sink)

        async def scrobble(song_id: str, submission: bool, time_ms: int | None) -> None:
            if not config.playback.scrobble:
                return  # turned off in Settings
            # Fire and forget: a slow or failing Navidrome must not delay playback.
            async def send() -> None:
                try:
                    await subsonic.scrobble(song_id, submission, time_ms)
                    log.info("Scrobbled %s (%s)", song_id, "played" if submission else "now playing")
                except Exception as exc:  # noqa: BLE001
                    log.warning("Scrobble failed for %s: %s", song_id, exc)

            spawn(send(), name='scrobble')

        coordinator = PlaybackCoordinator(
            connector,
            media,
            NavidromeQueueStore(db, subsonic),
            scrobbler=Scrobbler(scrobble),
            preload_next=settings.cast_preload_next,
            radio_builder=make_radio_builder(subsonic),
            artist_radio_builder=make_artist_radio_builder(subsonic),
        )
        ctx = cls(settings, db, config, sessions, credentials, subsonic, native, cast, coordinator, hub, media)
        ctx.covers = CoverCache(settings.data_dir / 'covers')
        coordinator.notifier = Notifier(
            player_changed=lambda: hub.publish("player", ctx.player_snapshot),
            queue_changed=lambda: hub.publish("queue", coordinator.queue_snapshot),
            notify=lambda level, code, params: hub.send_now(
                "notification", {"level": level, "code": code, "params": params}
            ),
        )

        def devices_changed(_devices: object) -> None:
            hub.publish("devices", ctx.devices_snapshot)
            coordinator.on_devices_changed({d.uuid for d in cast.devices})

        cast.on_devices_changed = devices_changed

        def client_gone(client_id: str) -> None:
            target = coordinator.target
            if isinstance(target, BrowserTarget) and target.client_id == client_id:
                target.sink(ConnectionEvent(connected=False))

        hub.on_client_gone = client_gone

        def credentials_state(rejected: bool) -> None:
            if rejected:
                log.warning("Navidrome rejected the stored password; update it in Settings")
            hub.publish("server", ctx.server_snapshot)

        subsonic.on_credentials_state = credentials_state
        native.on_rejected = lambda: subsonic.set_credentials_rejected(True)
        return ctx

    async def open(self) -> None:
        """Open the database and load the saved configuration."""
        await self.db.open()
        await self.config.load()
        self.apply_navidrome()
        self.apply_playback()

    def apply_playback(self) -> None:
        """Use the current playback options; they apply from the next track."""
        cfg = self.config.playback
        self.media.configure_stream(cfg.stream_format, cfg.max_bitrate)
        self.coordinator.preload_enabled = cfg.preload_next
        self.cast.set_known_hosts(list(cfg.known_hosts))

    def apply_navidrome(self) -> None:
        """Use the current Navidrome server and account everywhere."""
        cfg = self.config.navidrome or NavidromeConfig(url="", public_url="", username="")
        self.subsonic.configure(cfg.url, cfg.username)
        self.native.configure(cfg.url, cfg.username)
        self.media.configure(cfg.public_url, cfg.username)
        # Another library or account: what was remembered is no longer right.
        self.starred_memo.forget()
        self.on_repeat_memo.forget()

    async def setup_needs(self) -> dict[str, bool]:
        """What the first-run setup still has to ask."""
        navidrome = self.config.navidrome is None or await self.credentials.get_password() is None
        return {"navidrome": navidrome, "access": self.config.access_mode is None}

    def server_snapshot(self) -> dict:
        return {"navidrome_rejected": self.subsonic.credentials_rejected}

    def player_snapshot(self) -> dict:
        uuid = self.coordinator.device_uuid
        target = self.coordinator.target
        if target is not None:
            name: str | None = target.info.name
        else:
            info = self.cast.get(uuid) if uuid else None
            name = info.name if info else None
        return self.coordinator.player_snapshot(name)

    def browser_report(self, client_id: str, msg_type: str, data: dict) -> None:
        """Status from the tab used as "This browser"; ignored from any other tab."""
        target = self.coordinator.target
        if not isinstance(target, BrowserTarget) or target.client_id != client_id:
            return
        if msg_type == "browser_status":
            target.report_status(data)
        elif msg_type == "browser_volume":
            target.report_volume(data)

    def devices_snapshot(self) -> list[dict]:
        return [d.__dict__ for d in self.cast.devices]

    def full_snapshot(self) -> dict:
        return {
            "player": self.player_snapshot(),
            "queue": self.coordinator.queue_snapshot(),
            "devices": self.devices_snapshot(),
            "server": self.server_snapshot(),
        }
