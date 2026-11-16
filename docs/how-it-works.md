# How it works

```
Browser ──REST (commands)──▶ CastHome ──Subsonic API──▶ Music server
   ▲                           │  ▲                         ▲
   └──── WebSocket (state) ────┘  │ Cast protocol           │ /rest/stream?u&t&s
                                  ▼                         │
                            Chromecast ─────────────────────┘

"This browser" as the device:
Browser ◀── WebSocket: load / play / pause … ── CastHome
   │  ─── WebSocket: playing / paused / ended ──▶   │
   └──── <audio> GET /api/stream/<id> (cookie) ───▶ │ ──▶ Music server
```

- The **server** drives the Cast devices; browsers never use the Cast SDK,
  which is why any browser works.
- The **queue lives on the server**: playback goes on to the next track with
  every browser closed.
- **The music server stays the source of truth.** The queue *is* its play
  queue (`savePlayQueue`), so other Subsonic clients can resume it, and it is
  re-read when a CastHome screen opens, then every minute while idle with a
  screen open, so a queue saved by another client is picked up. With no
  screen open and nothing playing, CastHome does not call the music server.
  No second library, no indexing.

## Audio and credentials

The Chromecast downloads audio **directly from the music server**, using a token URL
(`t = md5(password + salt)`, random salt per URL) built on
`NAVIDROME_PUBLIC_URL_FOR_CAST`. A browser used as the device gets its audio
through CastHome instead, so it never sees the server's credentials.

Single-user design: one music server account and one queue, played on the device
you pick. The music server connection is part of CastHome's configuration: its
password is stored **encrypted** (key in `data/secret.key`, generated on first
start) so the server can keep streaming without a browser, and it is never
sent back to the frontend. Opening CastHome is protected separately, by a
CastHome password (not the music server's) or not at all, as you choose.

## Playback rules

| Cast reports | Meaning | CastHome does |
|---|---|---|
| `IDLE` / `FINISHED` | track ended | plays the next track (repeat one/all honoured) |
| `IDLE` / `ERROR` | cannot play | retries once transcoded to mp3, then skips and shows a notice |
| `IDLE` / `CANCELLED` or `INTERRUPTED` | stopped from a remote or another app | stops, no auto-advance |
| another app launched | device taken over | stops and shows a notice |

After a CastHome restart, the queue is restored from the music server. If the device
is still playing the current track, CastHome re-attaches to it without a gap.
Otherwise it waits, paused, and never auto-plays. While a Cast device is
unreachable, CastHome holds the position.

## Preloading

By default (switch in **Settings → Playback**, or `CAST_PRELOAD_NEXT`), the
next track is queued on the receiver (`QUEUE_INSERT`) about 20 seconds before
the current one ends, so the device buffers it and switches with a shorter
gap. CastHome stays in charge: when the device switches, CastHome checks that
it is still the right track (the queue may have been edited during those 20
seconds) and loads the right one otherwise. If the device does not switch
within a few seconds, CastHome loads the next track itself.

## Playing in the browser

When "This browser" is the device, the server still owns the queue and moves
on to the next track; the tab only plays what it is told over its WebSocket
and reports back. Audio goes through CastHome's `/api/stream/<id>` proxy with
your session cookie (Range requests supported, so seeking works). Files the
browser cannot play are retried transcoded, as with Cast. Lock-screen and
headset controls work through the Media Session API.
