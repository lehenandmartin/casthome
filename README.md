# CastHome

A self-hosted web player that plays your [Navidrome](https://www.navidrome.org/)
library on Google Cast devices (Chromecast, Nest speakers, speaker groups) or
in the browser itself, from **any browser** (Firefox, Safari/iOS, Chrome…).
Mobile-first, installable on the home screen.

- The **server** drives the Cast devices; browsers never use the Cast SDK.
- **No device chosen? It plays in the browser** you are using, still with the
  queue on the server.
- The **queue lives on the server**: playback goes on to the next track with
  every browser closed.
- **Navidrome stays the source of truth.** The queue *is* your Navidrome play
  queue (`savePlayQueue`), so other Subsonic clients can resume it. No second
  library, no indexing.

> **LAN only.** CastHome is designed for a trusted home network. Do not expose
> it to the Internet. The sign-in page keeps casual visitors out; it is not
> hardened for public exposure.

## Status

- Phase 1 (MVP): sign-in with optional "keep me signed in", Cast discovery,
  play an album on a device, server-side auto-advance, live state.
- Phase 2: browse albums (recent, most played, random, A–Z), artists, genres;
  search; play now / play next / add to queue for tracks, albums and artists;
  reorder the queue by drag and drop, remove items.
- Phase 3: playlists (play, create, rename, add/remove tracks, delete, save
  the queue as a playlist); favorites (☆ on tracks, albums, artists, plus a
  Favorites page); 5-star ratings; scrobbling to Navidrome ("now playing" when
  a track starts, a scrobble after half the track or 4 minutes of actual
  listening; seeking forward does not count).
- Phase 4: installable PWA; "Account" page listing signed-in devices, with
  per-device and "all other devices" sign-out (takes effect immediately);
  preloading of the next track to shorten gaps (`CAST_PRELOAD_NEXT`); the Navidrome
  play queue is re-read every minute while idle, so a queue saved by another
  Subsonic client is picked up.
- Interface redesign: mobile tab bar and mini player, full-screen Now Playing,
  queue in three parts, device picker grouped by type, track actions as a
  bottom sheet, desktop sidebar; in-browser playback ("This browser"); fixes
  for installed iOS web apps (no reload on navigation, instant startup, safe
  areas).

## How it works

```
Browser ──REST (commands)──▶ CastHome ──Subsonic API──▶ Navidrome
   ▲                           │  ▲                         ▲
   └──── WebSocket (state) ────┘  │ Cast protocol           │ /rest/stream?u&t&s
                                  ▼                         │
                            Chromecast ─────────────────────┘

"This browser" as the device:
Browser ◀── WebSocket: load / play / pause … ── CastHome
   │  ─── WebSocket: playing / paused / ended ──▶   │
   └──── <audio> GET /api/stream/<id> (cookie) ───▶ │ ──▶ Navidrome
```

The Chromecast downloads audio **directly from Navidrome**, using a token URL
(`t = md5(password + salt)`, random salt per URL) built on
`NAVIDROME_PUBLIC_URL_FOR_CAST`. A browser used as the device gets its audio
through CastHome instead, so it never sees Navidrome credentials.

Single-user design: one Navidrome account (`NAVIDROME_USERNAME`) and one
queue, played on the device you pick. Signing in checks the password against
Navidrome; the password is then stored **encrypted** (key derived from
`APP_SECRET_KEY`) so the server can keep streaming without a browser. It is
never sent to the frontend.

## Using CastHome

- **Mobile:** tabs at the bottom (Home, Search, Library, Queue; Library holds
  playlists, favorites, artists, genres and your account). Above them, the
  mini player: tap it for the full-screen **Now Playing** view (large artwork,
  seek bar, controls, shuffle/repeat, device, volume, next track). Swipe down
  or use Back to close it.
- **Desktop:** sidebar on the left, full player bar at the bottom.
- **Queue:** *Now playing*, *Up next* (drag the handle to reorder, ✕ to
  remove, tap to jump) and *Played* (collapsed). The menu saves the queue as a
  playlist or clears it.
- **Choosing where to play:** the device button (mini player, Now Playing or
  player bar) opens the list: *This browser*, then speaker groups, then
  speakers and TVs, with the active device's volume. Switching device carries
  on at the same position.
- **Track actions:** `⋯` on a track opens a sheet: play now, play next, add to
  queue, add to playlist, go to album or artist, rating.

## Install (Docker, Linux host)

```bash
cp .env.example .env   # then edit it
docker compose up -d --build
```

Open `http://<host-ip>:8080`.

`network_mode: host` is **required**: Cast discovery uses mDNS multicast,
which does not cross Docker's bridge network. Docker Desktop on macOS/Windows
does not support this reliably; run CastHome natively there (see Development).

## Configuration

All settings are environment variables; see [`.env.example`](.env.example).

| Variable | Purpose |
|---|---|
| `APP_SECRET_KEY` | Encrypts the stored password (≥ 32 chars). Changing it forces a new sign-in. |
| `NAVIDROME_URL` | Navidrome URL used by the backend. |
| `NAVIDROME_PUBLIC_URL_FOR_CAST` | Navidrome URL used by the Cast devices. LAN IP or LAN-resolvable name, never `localhost` or a container name. |
| `NAVIDROME_USERNAME` | The Navidrome account to play with. |
| `COOKIE_SECURE` | `true` when CastHome is behind HTTPS. |
| `SESSION_REMEMBER_DAYS` / `SESSION_SHORT_HOURS` | Session lifetimes (both sliding). |
| `STREAM_FORMAT`, `STREAM_MAX_BITRATE` | `raw` (default) streams original files; otherwise a Navidrome transcoding format. |
| `TRANSCODE_FALLBACK_FORMAT` | Format for files Cast cannot play, and retry format after a playback error (default `mp3`). |
| `CAST_PRELOAD_NEXT` | On by default: hand the next track to the device 20 s before the end of the current one to shorten the gap. `false` disables it. |
| `CAST_KNOWN_HOSTS` | Cast device IPs, when mDNS is blocked. |

### Sessions

- **Keep me signed in** checked: a 1-year cookie (`HttpOnly`, `SameSite=Lax`)
  whose expiry slides forward each time you use the app. It survives browser
  and container restarts (sessions are stored in SQLite under `DATA_DIR`).
- Unchecked: a browser-session cookie, also expiring after
  `SESSION_SHORT_HOURS` of inactivity.
- If the Navidrome password changes, every session is signed out and you are
  asked to sign in again.

### Playback rules

| Cast reports | Meaning | CastHome does |
|---|---|---|
| `IDLE` / `FINISHED` | track ended | plays the next track (repeat one/all honoured) |
| `IDLE` / `ERROR` | cannot play | retries once transcoded to mp3, then skips and shows a notice |
| `IDLE` / `CANCELLED` or `INTERRUPTED` | stopped from a remote or another app | stops, no auto-advance |
| another app launched | device taken over | stops and shows a notice |

After a CastHome restart, the queue is restored from Navidrome. If the device
is still playing the current track, CastHome re-attaches to it without a gap.
Otherwise it waits, paused, and never auto-plays.

### Playing in the browser

Until you pick a Cast device, pressing Play plays in the browser you are
using ("This browser" in the device list). The server still owns the queue
and moves on to the next track; the tab only plays what it is told over its
WebSocket and reports back. Audio goes through CastHome's `/api/stream/<id>`
proxy with your session cookie (Range requests supported, so seeking works),
so Navidrome credentials never reach the browser. Files the browser cannot
play are retried transcoded, as with Cast. Lock-screen and headset controls
work through the Media Session API.

Closing or reloading that tab stops playback (there is nothing left to play
on). On iOS, the volume slider is hidden for the browser (Safari only follows
the hardware buttons), and Safari may suspend background tabs: for long
listening with the screen locked, use a Cast device.

### Install as an app (PWA)

- **iPhone/iPad (Safari):** Share → *Add to Home Screen*. Works over plain HTTP.
  The home-screen app has its own cookies: sign in once inside it.
- **Android/desktop Chrome:** *Install app* in the menu. Chrome only offers it
  over **HTTPS** (or `localhost`); over plain-HTTP LAN access, use *Add to
  Home screen*, which creates a shortcut without offline shell.

The service worker only caches the app shell (HTML, JS, CSS, icons). The API
and the WebSocket always go to the server. Icons are generated by
`python3 scripts/make_icons.py`.

Details that matter for the installed iOS app:

- Internal links are handled by a small client-side router (`history.pushState`),
  because an installed iOS web app may otherwise reload the whole page on each
  link tap.
- The last known player, queue and device list are kept on the device
  (`localStorage`) and shown instantly at startup, then replaced by the
  server's state as soon as the WebSocket opens. They are cleared on sign-out.
- The page always fills the screen and starts below the status bar's blur;
  the "Reconnecting…" notice only appears after 3 s without a connection.

### Preloading

By default (`CAST_PRELOAD_NEXT=true`), the next track is queued on the receiver
(`QUEUE_INSERT`) about 20 seconds before the current one ends, so the device
buffers it and switches with a shorter gap. CastHome stays in charge: when the
device switches, CastHome checks that it is still the right track (the queue
may have been edited during those 20 seconds) and loads the right one
otherwise. If the device does not switch within a few seconds, CastHome loads
the next track itself.

## Troubleshooting

**No Cast device found.**
- Docker: check `network_mode: host`, and run on Linux.
- The host must be on the same subnet/VLAN as the devices, or mDNS must be
  relayed (Avahi reflector, router "mDNS repeater").
- Firewall: allow UDP 5353 (mDNS) and outgoing TCP 8009 (Cast).
- Workaround: list device IPs in `CAST_KNOWN_HOSTS`.

**The device shows the track, then nothing plays / error notices.**
The Chromecast cannot reach `NAVIDROME_PUBLIC_URL_FOR_CAST`. From another LAN
machine, open `<that URL>/rest/ping` and check you get a response (an auth
error is fine). `localhost`, `127.0.0.1` and Docker service names are refused
at startup for this reason.

**HTTPS.** Cast devices reject self-signed certificates. Use plain HTTP on the
LAN, or a publicly trusted certificate (e.g. Let's Encrypt via DNS challenge)
on a name the devices can resolve.

**The installed app still shows the old version after an update.** Rebuild the
frontend (`npm run build`), then close the app completely (swipe it away) and
reopen it.

**"Reconnecting to CastHome…" stays on screen.** The WebSocket cannot reach the
server: check CastHome is running and reachable from the phone. Playback on a
Cast device continues meanwhile; the app catches up when it reconnects.

**Some files skip.** Cast cannot play WMA, APE, ALAC, DSD or > 96 kHz files.
CastHome transcodes those (and retries after an error) with
`TRANSCODE_FALLBACK_FORMAT`; make sure transcoding (ffmpeg) works in Navidrome.

## Development

Requirements: Python 3.12, Node 20+.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e "backend[dev]"
cd frontend && npm install && cd ..
```

Copy `.env.example` to `.env` at the repository root and fill it in. Then run
the backend (it finds the root `.env` from any directory, stores its data in
`./data` and serves the built frontend from `frontend/dist`, so run
`npm run build` after frontend changes) and, for frontend work, the Vite dev
server, which proxies `/api` to it:

```bash
.venv/bin/python -m casthome.main
```

```bash
cd frontend && npm run dev
```

Tests and checks:

```bash
cd backend && ../.venv/bin/python -m pytest
```

```bash
cd frontend && npm run check && npm run build
```

### Layout

```
backend/casthome/
  config.py            settings (env)
  db.py                SQLite + migrations
  auth/                sessions, encrypted credentials
  subsonic/            Subsonic client, token URLs, Cast format policy
  cast/                discovery (zeroconf), pychromecast adapter,
                       browser.py: a browser tab driven like a Cast device
  queue/logic.py       pure queue logic (next/previous/shuffle/repeat/move)
  playback/            coordinator state machine, media payloads, persistence
  scrobble/            scrobbling rules
  api/                 REST routers, WebSocket endpoint, stream.py (audio proxy)
  ws/hub.py            WebSocket broadcast and per-tab messages
frontend/src/
  lib/i18n/en.ts            every UI string (add a locale by copying this file)
  lib/store.svelte.ts       app state, WebSocket client, startup cache
  lib/router.svelte.ts      hash routing without page loads
  lib/browserPlayer.ts      <audio> player for "This browser", Media Session
  lib/icons.ts              SVG icon set
  components/               UI (PlayerBar, NowPlaying, QueueView, DevicePicker…)
frontend/public/            manifest, service worker, icons
scripts/make_icons.py       regenerates the PWA icons
```
