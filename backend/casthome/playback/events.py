"""What the Cast device reports: the media status (playing, finished, error),
the receiver (volume, another app) and the connection.

How an IDLE status is interpreted (only for the media we loaded last):
- FINISHED     natural end -> advance (repeat-one replays)
- ERROR        unplayable -> retry once transcoded, else skip and notify
- CANCELLED    stopped from elsewhere (remote, Google Home app) -> stopped
- INTERRUPTED  another media replaced ours -> stopped
Statuses for an older media (our previous load) are ignored.
"""

from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlparse

from casthome.cast.types import (
    DEFAULT_MEDIA_RECEIVER_APP_ID,
    CastEvent,
    ConnectionEvent,
    LoadFailedEvent,
    MediaEvent,
    ReceiverEvent,
)
from casthome.playback.state import PlaybackError, Status

from casthome.playback.preload import Preloading

log = logging.getLogger(__name__)


class DeviceEvents(Preloading):
    # --- internals: device events --------------------------------------------

    async def _event_worker(self) -> None:
        while True:
            event = await self._events.get()
            try:
                async with self._lock:
                    await self._handle_event(event)
            except PlaybackError as exc:
                self.notifier.notify("error", exc.code, exc.params)
            except Exception:  # noqa: BLE001 - keep the worker alive
                log.exception("Error while handling Cast event %r", event)

    async def _handle_event(self, event: CastEvent) -> None:
        if isinstance(event, MediaEvent):
            await self._on_media(event)
        elif isinstance(event, LoadFailedEvent):
            if self._expected_content_id is not None:
                await self._on_error()
        elif isinstance(event, ReceiverEvent):
            await self._on_receiver(event)
        elif isinstance(event, ConnectionEvent):
            if not event.connected and self._is_browser():
                # The tab that was playing closed: there is nothing to reconnect to.
                log.info("The browser used for playback went away")
                self._expected_content_id = None
                self._clear_preload()
                self.status = Status.STOPPED
                self.target = None
                self.connected = False
                self.device_uuid = None
                self.notifier.player_changed()
                self._schedule_save()
                return
            if event.connected != self.connected:
                self.connected = event.connected
                if not event.connected:
                    # Nothing is known to play until the device answers again: hold
                    # the position at the device's last report (the loss is noticed
                    # up to ~20 s late; moving on would skip music on resume).
                    if self.status in (Status.PLAYING, Status.BUFFERING):
                        self._set_position(self.position)
                        self.status = Status.BUFFERING
                    self.notifier.notify("warning", "device_disconnected", {})
                elif self.target is not None:
                    await self.target.request_status()
                self.notifier.player_changed()

    def _matches_reattach(self, content_id: str | None) -> bool:
        if not self._reattach_song_id or not content_id:
            return False
        query = parse_qs(urlparse(content_id).query)
        return query.get("id") == [self._reattach_song_id] and query.get("c") == ["CastHome"]

    async def _on_media(self, ev: MediaEvent) -> None:
        if self._preload is not None and ev.content_id == self._preload.url:
            if ev.player_state in ("PLAYING", "PAUSED", "BUFFERING"):
                await self._switch_to_preloaded()
                if self._expected_content_id != ev.content_id:
                    return  # the preload was stale and has been replaced
            elif ev.player_state == "IDLE" and ev.idle_reason == "ERROR":
                log.info("Preloaded track failed on the receiver; loading it normally")
                self._clear_preload()
                await self._advance(natural=True)
                return
        if self._expected_content_id is None:
            if ev.player_state in ("PLAYING", "PAUSED", "BUFFERING") and self._matches_reattach(ev.content_id):
                log.info("Re-attached to media already playing on the device")
                self._expected_content_id = ev.content_id
                self._seen_active = True
                self._reattach_song_id = None
                self._transcoded = "format=" in (ev.content_id or "")
                if self._scrobbler is not None and self.queue.current is not None:
                    self._scrobbler.track_loaded(self.queue.current.item.id, self.queue.current.item.duration)
            else:
                return
        if ev.content_id and ev.content_id != self._expected_content_id:
            return  # status for a media we replaced

        if ev.player_state in ("PLAYING", "PAUSED", "BUFFERING"):
            first = not self._seen_active
            self._seen_active = True
            before = (self.status, self.duration)
            self.status = {"PLAYING": Status.PLAYING, "PAUSED": Status.PAUSED}.get(ev.player_state, Status.BUFFERING)
            if ev.player_state == "PLAYING":
                self._consecutive_errors = 0
            if ev.duration:
                self.duration = ev.duration
            # Resuming mid-track, devices first report buffering at 0 s before
            # seeking: keep the start position (the progress bar jumped to 0).
            if not (first and ev.player_state == "BUFFERING" and ev.current_time < 0.5 and self.position > 1):
                self._set_position(ev.current_time)
            # Polled every few seconds: tell the browsers only when something they
            # cannot work out themselves changed (they move the position on locally).
            if (self.status, self.duration) != before or self._position_drifted():
                self.notifier.player_changed()
            await self._report_progress(ev)
            if ev.player_state == "PLAYING":
                await self._maybe_preload(ev)
            return

        if ev.player_state != "IDLE":
            return
        if ev.idle_reason == "ERROR":
            await self._on_error()
        elif ev.idle_reason == "FINISHED" and self._seen_active:
            if self._preload is not None:
                # The receiver moves on to the preloaded track by itself.
                self._start_preload_watchdog()
                return
            self._expected_content_id = None
            await self._advance(natural=True)
        elif ev.idle_reason in ("CANCELLED", "INTERRUPTED") and self._seen_active:
            log.info("Playback stopped from outside CastHome (%s)", ev.idle_reason)
            self._expected_content_id = None
            self.status = Status.STOPPED
            self.notifier.player_changed()
            self._schedule_save()

    async def _report_progress(self, ev: MediaEvent) -> None:
        if self._scrobbler is None or self.queue.current is None:
            return
        if ev.player_state == "PLAYING":
            await self._scrobbler.progress(self.queue.current.item.id, ev.current_time)
        else:
            self._scrobbler.stopped()

    async def _on_receiver(self, ev: ReceiverEvent) -> None:
        changed = (ev.volume_level, ev.volume_muted) != (self.volume, self.muted)
        self.volume, self.muted = ev.volume_level, ev.volume_muted
        if (
            self._expected_content_id is not None
            and self._seen_active
            and ev.app_id != DEFAULT_MEDIA_RECEIVER_APP_ID
        ):
            self._expected_content_id = None
            self.status = Status.STOPPED  # the position is kept: Play resumes there
            if ev.app_id is None:
                # No app at all: the device restarted (power cut) or was told to stop.
                log.info("Playback stopped on the device (no app running)")
                self.notifier.notify("warning", "device_stopped", {})
            else:
                log.info("Another app took over the device (%s)", ev.app_id)
                self.notifier.notify("warning", "device_taken_over", {})
            self._schedule_save()
            changed = True
        if changed:
            self.notifier.player_changed()
