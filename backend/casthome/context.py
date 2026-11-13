"""Wires all services together; one instance per running app."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from casthome.auth.credentials import CredentialStore
from casthome.auth.crypto import SecretBox
from casthome.auth.sessions import SessionStore
from casthome.cast.manager import CastManager
from casthome.cast.types import CastTarget, EventSink
from casthome.config import Settings
from casthome.db import Database
from casthome.playback.coordinator import Notifier, PlaybackCoordinator
from casthome.playback.media import MediaBuilder, StreamConfig
from casthome.playback.persistence import NavidromeQueueStore
from casthome.scrobble.scrobbler import Scrobbler
from casthome.subsonic.client import SubsonicClient
from casthome.ws.hub import Hub

log = logging.getLogger(__name__)


@dataclass
class AppContext:
    settings: Settings
    db: Database
    sessions: SessionStore
    credentials: CredentialStore
    subsonic: SubsonicClient
    cast: CastManager
    coordinator: PlaybackCoordinator
    hub: Hub

    @classmethod
    def build(cls, settings: Settings) -> AppContext:
        db = Database(settings.database_path)
        sessions = SessionStore(
            db,
            remember_seconds=settings.session_remember_days * 86400,
            short_seconds=settings.session_short_hours * 3600,
        )
        credentials = CredentialStore(db, SecretBox(settings.app_secret_key))
        subsonic = SubsonicClient(settings.navidrome_url, settings.navidrome_username, credentials.get_password)
        cast = CastManager(settings.known_hosts)
        media = MediaBuilder(
            StreamConfig(
                public_base_url=settings.navidrome_public_url_for_cast,
                username=settings.navidrome_username,
                stream_format=settings.stream_format,
                max_bitrate=settings.stream_max_bitrate,
                fallback_format=settings.transcode_fallback_format,
            ),
            credentials.get_password,
        )

        async def connector(uuid: str, sink: EventSink) -> CastTarget:
            return await cast.connect(uuid, sink)

        async def scrobble(song_id: str, submission: bool, time_ms: int | None) -> None:
            # Fire and forget: a slow or failing Navidrome must not delay playback.
            async def send() -> None:
                try:
                    await subsonic.scrobble(song_id, submission, time_ms)
                    log.info("Scrobbled %s (%s)", song_id, "played" if submission else "now playing")
                except Exception as exc:  # noqa: BLE001
                    log.warning("Scrobble failed for %s: %s", song_id, exc)

            asyncio.create_task(send())

        hub = Hub()
        coordinator = PlaybackCoordinator(
            connector, media, NavidromeQueueStore(db, subsonic), scrobbler=Scrobbler(scrobble)
        )
        ctx = cls(settings, db, sessions, credentials, subsonic, cast, coordinator, hub)
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
        subsonic.on_invalid_credentials = ctx.invalidate_credentials
        return ctx

    def player_snapshot(self) -> dict:
        uuid = self.coordinator.device_uuid
        info = self.cast.get(uuid) if uuid else None
        return self.coordinator.player_snapshot(info.name if info else None)

    def devices_snapshot(self) -> list[dict]:
        return [d.__dict__ for d in self.cast.devices]

    def full_snapshot(self) -> dict:
        return {
            "player": self.player_snapshot(),
            "queue": self.coordinator.queue_snapshot(),
            "devices": self.devices_snapshot(),
        }

    async def invalidate_credentials(self) -> None:
        """The Navidrome password changed: forget it and sign every browser out."""
        log.warning("Navidrome rejected the stored password; signing out every session")
        await self.credentials.clear()
        await self.sessions.revoke_all()
        self.hub.send_now("auth_expired", {"reason": "navidrome_password_changed"})
