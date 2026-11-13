# CastHome

A self-hosted web player that plays your [Navidrome](https://www.navidrome.org/)
library on Google Cast devices (Chromecast, Nest speakers, speaker groups),
from **any browser** (Firefox, Safari/iOS, Chrome…).

- The **server** drives the Cast devices; browsers never use the Cast SDK.
- The **queue lives on the server**: playback goes on to the next track with
  every browser closed.
- **Navidrome stays the source of truth.** The queue *is* your Navidrome play
  queue (`savePlayQueue`), so other Subsonic clients can resume it. No second
  library, no indexing.

> **LAN only.** CastHome is designed for a trusted home network. Do not expose
> it to the Internet. The sign-in page keeps casual visitors out; it is not
> hardened for public exposure.

## Status

Phase 1 (MVP): sign-in with optional "keep me signed in", Cast discovery,
play an album on a device, server-side auto-advance, live state in a minimal UI.

## How it works

```
Browser ──REST (commands)──▶ CastHome ──Subsonic API──▶ Navidrome
   ▲                           │  ▲                         ▲
   └──── WebSocket (state) ────┘  │ Cast protocol           │ /rest/stream?u&t&s
                                  ▼                         │
                            Chromecast ─────────────────────┘
```

The Chromecast downloads audio **directly from Navidrome**, using a token URL
(`t = md5(password + salt)`, random salt per URL) built on
`NAVIDROME_PUBLIC_URL_FOR_CAST`.

Single-user design: one Navidrome account (`NAVIDROME_USERNAME`) and one
queue, played on the device you pick. Signing in checks the password against
Navidrome; the password is then stored **encrypted** (key derived from
`APP_SECRET_KEY`) so the server can keep streaming without a browser. It is
never sent to the frontend.

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
the backend (it finds the root `.env` from any directory and stores its data in
`./data`) and, for frontend work, the Vite dev server, which proxies `/api` to it:

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
  cast/                discovery (zeroconf) and pychromecast adapter
  queue/logic.py       pure queue logic (next/previous/shuffle/repeat/move)
  playback/            coordinator state machine, media payloads, persistence
  api/                 REST routers + WebSocket endpoint
  ws/hub.py            WebSocket broadcast
frontend/src/
  lib/i18n/en.ts       every UI string (add a locale by copying this file)
  lib/store.svelte.ts  app state + WebSocket client
  components/          UI
```
