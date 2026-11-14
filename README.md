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
> it to the Internet. Its own password keeps casual visitors out; it is not
> hardened for public exposure.

## Status

- Phase 1 (MVP): sign-in with optional "keep me signed in", Cast discovery,
  play an album on a device, server-side auto-advance, live state.
- Phase 2: browse albums (recent, most played, random, A–Z), artists, genres;
  search; play now / add to queue for tracks, albums and artists;
  reorder the queue by drag and drop, remove items.
- Phase 3: playlists (play, create, rename, add/remove tracks, delete, save
  the queue as a playlist); favorites (☆ on tracks, albums, artists; a
  *Favorites* filter on the Tracks, Albums and Artists pages); 5-star ratings; scrobbling to Navidrome ("now playing" when
  a track starts, a scrobble after half the track or 4 minutes of actual
  listening; seeking forward does not count; can be turned off in Settings).
- Phase 4: installable PWA; signed-in devices with per-device and "all other
  devices" sign-out, effective immediately; preloading of the next track to
  shorten gaps; the Navidrome play queue is re-read every minute while idle,
  so a queue saved by another Subsonic client is picked up.
- Interface redesign: mobile tab bar and mini player, full-screen Now Playing,
  queue in three parts, device picker grouped by type, track actions as a
  bottom sheet, desktop sidebar; in-browser playback ("This browser"); fixes
  for installed iOS web apps (no reload on navigation, instant startup, safe
  areas).
- Setup from the browser: no `.env` to write. The first visit asks for the
  Navidrome connection and how to protect CastHome (its own password, open on
  the local network only, or open). **Settings** then covers the Navidrome
  connection, playback options (streaming quality, preloading, Cast device
  addresses), language, access and signed-in devices.
- Languages: English (default) and French. *Automatic* picks the first of the
  browser's preferred languages that CastHome has, else English.
- 0.2: action menus on right-click (desktop) and long-press (touch screens)
  for tracks, queue rows, albums, playlists, artists and the current track;
  artist radio; similar artists on artist pages and the artist's other
  albums on album pages; loading placeholders instead of empty pages;
  playlists sorted by last change, created with a *New playlist* button;
  untrusted reverse proxies detected for *Open at home*.
- Smoother navigation: pages already seen open at once from memory and
  refresh in the background; album and artist pages start from what the
  tapped card knew; links are preloaded on touch or hover; Back returns to
  the same scroll position; pages, slow covers and sheets fade in and out;
  loading placeholders only show when loading lasts; long lists load their
  next page before the bottom; play/pause and queue removals react at once.

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

Single-user design: one Navidrome account and one queue, played on the device
you pick. The Navidrome connection is part of CastHome's configuration: its
password is stored **encrypted** (key in `data/secret.key`, generated on first
start) so the server can keep streaming without a browser, and it is never
sent back to the frontend. Opening CastHome is protected separately, by a
CastHome password (not the Navidrome one) or not at all, as you choose.

## Using CastHome

- **Mobile:** tabs at the bottom (Home, Search, Library; Library holds
  playlists, tracks, artists, genres, albums and Settings). Above them,
  the mini player: tap it for the full-screen **Now Playing** view (large
  artwork, seek bar, controls, shuffle/repeat, device, volume, next track).
  Swipe down or use Back to close it. The queue button under *repeat* slides
  the **queue up as a sheet** over the player; Back, the chevron or a swipe
  down on its header returns to the player.
- **Settings** (sidebar bottom on desktop, in Library on mobile):
  - *Navidrome*: server, account and Cast URL, with a connection test before
    saving.
  - *Playback*: streaming quality and maximum bitrate, preloading, scrobbling,
    Cast device addresses.
  - *Language*: automatic (this browser's language), English or French; saved
    on the device, applied at once.
  - *Access to CastHome*: password, open at home, or no password; this
    device's sign-out.
  - *Signed-in devices*: every browser signed in, each can be signed out.
  - *About*: CastHome version (and the commit, for images built by GitHub),
    with a link to the repository.
- **Artist page:** *Favorite tracks* opens that artist's starred tracks
  (features included) with the Tracks page sorts; *Popular* lists their most
  popular tracks in your library (Last.fm popularity through Navidrome's
  `getTopSongs`; without it, your most played), 5 shown, 10 with *See more*.
  At the bottom, *Similar artists* (up to 18): Last.fm's similar artists in
  your library (`getArtistInfo2`), then the artists most present among
  similar tracks; never the artist again, a duo with them ("Madonna &
  Charli xcx" on Madonna's page) or an artist without albums. They appear
  all at once, once their pictures are loaded, and only in full rows for the
  screen width (all of them when there is less than a row).
- **Playlists:** most recently changed first; *New playlist* asks for a
  name and opens the new (empty) playlist.
- **Album page:** at the bottom, *More by <artist>*: the artist's other
  albums, in full rows like *Similar artists* (hidden when there are none).
- **Loading:** pages and lists show grey placeholder shapes while they load
  (no animation when the system asks for reduced motion).
- **Favorites:** a ★ *Favorites* filter on the Tracks, Albums and Artists
  pages shows only what you starred, with that page's sorts; it is kept in
  the address (`?fav=1`), so links and Back keep it.
- **Home:** quick-access tiles (favorite tracks, recently played albums,
  recently edited playlists), then
  rows: recently played, recently added, your favorite artists (or your most
  played ones if none are starred), *On repeat* (your most played tracks
  among those played in the last 30 days: Navidrome keeps a total play count
  and the last play date per track, not a play history) and your playlists,
  most recently edited first. Each row links to the full list; the complete
  album grid is under Library > Albums.
- **Desktop:** sidebar on the left, full player bar at the bottom. The queue
  button (player bar or sidebar) opens the **queue as a panel on the right**,
  next to the page you are browsing; it stays open across pages and is
  remembered.
- **Queue** (works like Spotify's): *Now playing*, then **Next in queue** (the
  tracks you added with *Add to queue*, in the order you added them), then
  **Next from: <album or playlist>** (the rest of what you started), then
  *Played* (collapsed). *Add to queue* always goes to *Next in queue*, so an
  added track plays right after the current one and the album then carries on
  where it was. Starting another album keeps *Next in queue*; shuffle never
  mixes it. Drag the handle to reorder, including between the two parts; ✕
  removes, a tap jumps. *Clear* empties *Next in queue* only; the menu saves
  the whole queue as a playlist or clears everything.
- **Choosing where to play:** the device button (mini player, Now Playing or
  player bar) opens the list: *This browser*, then speaker groups, then
  speakers and TVs, with the active device's volume. Switching device carries
  on at the same position.
- **Tracks** (in Library): every track, newest additions first by default;
  also A–Z, by artist, by album, most played and recently played. Your choice
  is remembered on the device. Tapping a track plays the loaded list from it.
  Navidrome's Subsonic API cannot list tracks this way, so this page uses
  Navidrome's own API (`/api/song`, signed in with the same account).
- **Radio:** *Start radio* (track menu, or the Now Playing view) plays the
  track, then similar tracks, and keeps adding more as it plays (endless, no
  repeats). Started from the track being played, that track carries on
  where it is (no restart) and the similar tracks follow it. Tracks in *Next
  in queue* stay first; starting an album or a playlist ends the radio.
  Sources, tried in order so the radio still works
  when a service behind Navidrome is down: `getSimilarSongs` on the track
  (AudioMuse-AI sonic similarity when that plugin is active, else Last.fm and
  other agents), then `getSimilarSongs2` on the artist, then the artist's top
  tracks. The queue shows which source was used.
- **Artist radio:** *Start radio* on an artist page (or the artist's menu)
  plays the artist and similar artists, shuffled, opening with one of the
  artist's tracks. Source: `getSimilarSongs2` on the artist, asked for 200
  tracks at once (Last.fm data through Navidrome), else the artist's top
  tracks. The artist makes up at most a third of each batch, spread through
  it (never two in a row), and each batch uses at most a quarter of the
  artist's tracks left, so a small catalogue comes back over several
  batches. Each refill asks again, skipping what the queue already has; once
  only the artist's own tracks are left, the radio carries on from the last
  track like a track radio. AudioMuse-AI does not apply: it only works from a
  track.
- **Swipe gestures (touch screens):** swipe a track right to add it to *Next
  in queue* (any track list; in the queue, a track from the album or playlist
  moves to *Next in queue*), swipe left in the queue to remove it. A coloured
  background shows the action; a short swipe springs back and does nothing.
  On touch screens the queue has no ✕ (swipe left instead) and the reorder
  handle sits on the right, under the thumb.
- **Track actions:** `⋯` on a track opens a sheet: play now, add to queue, add
  to playlist, go to album or artist, rating.
- **Right-click (mouse or trackpad) or long-press (touch screens):** opens
  the item's menu, at the pointer with a mouse, as a sheet on touch screens, on
  - tracks: the same actions as `⋯`;
  - queue rows: play now, move to *Next in queue* (album or playlist rows),
    radio, add to playlist, go to album or artist, rating, remove;
  - albums (grids, Home): play, add to queue, favorite, rating, go to artist;
  - playlists (Playlists, Home): play, add to queue, rename, delete;
  - artists (Artists, Search, Home): play all, add to queue, radio, favorite;
  - the current track (player bar, Now Playing, queue): favorite, radio, add
    to playlist, go to album or artist, rating.

  Arrow keys move through the menu, Escape closes it, and a right-click
  elsewhere opens the menu there. Shift + right-click keeps the browser's own
  menu. A long-press (half a second, without moving) never plays or opens
  the item; moving the finger scrolls or swipes as before, and the queue's
  drag handle keeps its own long-press.

## Install (Docker, Linux host)

No need to clone the repository: the image is published on GitHub
(`ghcr.io/lehenandmartin/casthome`, amd64 and arm64, so a Raspberry Pi works
too). Get the compose file and start it:

```bash
mkdir casthome && cd casthome && curl -fsSLO https://raw.githubusercontent.com/lehenandmartin/casthome/main/docker-compose.yml && docker compose up -d
```

Or paste [`docker-compose.yml`](docker-compose.yml) as a stack in Portainer,
Dockge, etc.

Open `http://<host-ip>:4577` and follow the setup: Navidrome URL, username
and password (checked right away), then how to protect CastHome. Everything is
saved under `./data`; no `.env` is needed.

The setup is open to whoever opens CastHome first, so do it right after
starting it.

The container starts as root only to give `./data` to the user CastHome runs
as (`PUID`:`PGID`, default `1000:1000`), then drops to that user. On a NAS, set
`PUID`/`PGID` in `docker-compose.yml` to the owner you want for the folder.

To use another port than 4577, set `PORT` under `environment:` in
`docker-compose.yml` (a `ports:` mapping has no effect with
`network_mode: host`):

```yaml
    environment:
      PORT: "8090"
```

`network_mode: host` is **required**: Cast discovery uses mDNS multicast,
which does not cross Docker's bridge network. Docker Desktop on macOS/Windows
does not support this reliably; run CastHome natively there (see Development).

### Update

```bash
docker compose pull && docker compose up -d
```

`:latest` is the last release. To control updates, pin a version in
`docker-compose.yml` (`:0.1` takes the fixes of 0.1, `:0.1.0` never moves);
`:main` follows the development branch. The running version is shown in
**Settings → About**, with a link to this repository.

### Build the image yourself

From a clone of the repository:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

## Configuration

The Navidrome connection and access are set in the browser (first-run setup,
then **Settings**), and so are the playback options in **Settings → Playback**:
streaming quality and maximum bitrate, preloading of the next track,
scrobbling to Navidrome, and Cast
device addresses for networks where discovery does not find them. They apply
from the next track, without a restart. Environment variables are optional, in `.env` or the
container environment; see [`.env.example`](.env.example). A Navidrome value
set there wins over the one saved from the browser and shows as locked in
Settings (handy for scripted installs).

| Variable | Purpose |
|---|---|
| `NAVIDROME_URL` | Navidrome URL used by the backend. |
| `NAVIDROME_PUBLIC_URL_FOR_CAST` | Navidrome URL used by the Cast devices (defaults to `NAVIDROME_URL`). LAN IP or LAN-resolvable name, never `localhost` or a container name. |
| `NAVIDROME_USERNAME`, `NAVIDROME_PASSWORD` | The Navidrome account to play with. |
| `APP_SECRET_KEY` | Encryption key for the stored Navidrome password (≥ 32 chars). By default one is generated into `data/secret.key`; keep that file with the database. |
| `COOKIE_SECURE` | `true` when CastHome is behind HTTPS. |
| `FORWARDED_ALLOW_IPS` | Reverse proxies trusted to give the visitor's address (IPs or networks, comma-separated; default `127.0.0.1,::1`). See [Behind a reverse proxy](#behind-a-reverse-proxy). |
| `SESSION_REMEMBER_DAYS` / `SESSION_SHORT_HOURS` | Session lifetimes (both sliding). |
| `STREAM_FORMAT`, `STREAM_MAX_BITRATE` | `raw` (default) streams original files; otherwise a Navidrome transcoding format (`mp3`, `aac`, `opus`) and a limit in kbps. Also in Settings. |
| `TRANSCODE_FALLBACK_FORMAT` | Format for files Cast cannot play, and retry format after a playback error (default `mp3`). |
| `CAST_PRELOAD_NEXT` | On by default: hand the next track to the device 20 s before the end of the current one to shorten the gap. `false` disables it. Also in Settings. |
| `CAST_KNOWN_HOSTS` | Cast device IPs, when mDNS is blocked. Also in Settings. |
| `SCROBBLE` | On by default: report plays to Navidrome ("now playing" and scrobbles). `false` disables it. Also in Settings. |

### Access

Chosen during the setup, changed in **Settings → Access to CastHome** (the
current CastHome password is asked first):

- **Password** (recommended): a CastHome password on every device.
- **Open at home**: no password from a private address (local network), the
  password from anywhere else. Behind a reverse proxy, see
  [Behind a reverse proxy](#behind-a-reverse-proxy).
- **No password**: anyone who can reach CastHome can use it.

Setting a new password signs every other device out. Sign-in attempts are
rate-limited per address.

If Navidrome later refuses the saved password (it was changed there), you stay
signed in to CastHome: a banner asks you to update it in **Settings →
Navidrome**, where the connection can be tested before saving. The saved
password is only ever sent to the server and account it was saved for;
pointing CastHome at another one asks for the password again.

### Behind a reverse proxy

Behind a reverse proxy (Nginx Proxy Manager, Traefik, Caddy…), CastHome
receives every request from the proxy. To tell visitors apart, it reads the
visitor's address from the `X-Forwarded-For` header, but only from proxies
listed in `FORWARDED_ALLOW_IPS` (default `127.0.0.1,::1`, so a proxy in Docker
or on another machine is **not** trusted). Add the address the proxy connects
from, a comma-separated list of IPs or networks:

```yaml
    environment:
      # Proxy in Docker on the same host (Docker gateways, 172.17.0.1…):
      FORWARDED_ALLOW_IPS: "172.16.0.0/12"
      # Or a proxy on another machine: its LAN address, e.g. "192.168.1.5".
```

Until the proxy is trusted, **Open at home** asks for the password from
everyone coming through it (CastHome cannot tell who is local), and
**Settings → Access to CastHome** shows a warning with the proxy's address.
Choosing **Open at home** shows the address CastHome sees for your device and
whether it counts as local; check it from outside (e.g. on mobile data) after
the change. A visitor cannot fake a local address: the proxy appends the real
one to the header, and only the address added by the last trusted proxy is
used.

### Sessions

- **Keep me signed in** checked: a 1-year cookie (`HttpOnly`, `SameSite=Lax`)
  whose expiry slides forward each time you use the app. It survives browser
  and container restarts (sessions are stored in SQLite under `DATA_DIR`).
- Unchecked: a browser-session cookie, also expiring after
  `SESSION_SHORT_HOURS` of inactivity.
- Signed-in devices are listed in Settings, where each can be signed out
  (not shown with **No password**).

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

By default (switch in **Settings → Playback**, or `CAST_PRELOAD_NEXT`), the next
track is queued on the receiver
(`QUEUE_INSERT`) about 20 seconds before the current one ends, so the device
buffers it and switches with a shorter gap. CastHome stays in charge: when the
device switches, CastHome checks that it is still the right track (the queue
may have been edited during those 20 seconds) and loads the right one
otherwise. If the device does not switch within a few seconds, CastHome loads
the next track itself.

## Troubleshooting

**`Permission denied: '/data/…'` at start.** CastHome cannot write to its data
folder. With the provided image this is fixed at start; if you run it with
`user:` or a custom image, give the folder to that user
(`chown -R 1000:1000 ./data`) or set `PUID`/`PGID`.

**No Cast device found.**
- Docker: check `network_mode: host`, and run on Linux.
- The host must be on the same subnet/VLAN as the devices, or mDNS must be
  relayed (Avahi reflector, router "mDNS repeater").
- Firewall: allow UDP 5353 (mDNS) and outgoing TCP 8009 (Cast).
- Workaround: list device IPs in **Settings → Playback → Cast device addresses**
  (or `CAST_KNOWN_HOSTS`).

**The device shows the track, then nothing plays / error notices.**
The Chromecast cannot reach `NAVIDROME_PUBLIC_URL_FOR_CAST`. From another LAN
machine, open `<that URL>/rest/ping` and check you get a response (an auth
error is fine). `localhost`, `127.0.0.1` and Docker service names are refused
when saving the connection for this reason.

**HTTPS.** Cast devices reject self-signed certificates. Use plain HTTP on the
LAN, or a publicly trusted certificate (e.g. Let's Encrypt via DNS challenge)
on a name the devices can resolve.

**The installed app still shows the old version after an update.** After
pulling the new image (or, in development, `npm run build`), close the app completely (swipe it away) and
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

Run the backend (it stores its data in `./data`, reads an optional `.env` at
the repository root from any directory, and serves the built frontend from `frontend/dist`, so run
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

UI text never goes in components: add each string to `lib/i18n/en.ts` and its
French version to `lib/i18n/fr.ts` (`npm run check` fails if one is missing).

### Releases

The version lives in one place: `__version__` in
`backend/casthome/__init__.py` (the API and **Settings → About** report it).
Every push to `main` publishes the `:main` image (GitHub Actions,
[`.github/workflows/docker.yml`](.github/workflows/docker.yml)). To release:

1. Set `__version__` to the new version (e.g. `0.2.0`) and commit.
2. Tag and push: `git tag v0.2.0 && git push origin main v0.2.0`.

The workflow checks the tag matches `__version__`, then publishes `:0.2.0`,
`:0.2`, `:0` and `:latest`.

### Layout

```
backend/casthome/
  __init__.py          __version__ (the only place to change it)
  config.py            optional environment settings
  appconfig.py         configuration saved from the browser, access modes,
                       CastHome password hashing, encryption key file
  db.py                SQLite + migrations
  auth/                sessions, encrypted Navidrome password
  subsonic/            Subsonic client, token URLs, Cast format policy
  cast/                discovery (zeroconf), pychromecast adapter,
                       browser.py: a browser tab driven like a Cast device
  queue/logic.py       pure queue logic (next/previous/shuffle/repeat/move)
  playback/            coordinator state machine, media payloads, persistence
  scrobble/            scrobbling rules
  api/                 REST routers (setup.py first-run setup, server.py
                       settings), WebSocket endpoint, stream.py (audio proxy)
  ws/hub.py            WebSocket broadcast and per-tab messages
frontend/src/
  lib/i18n/en.ts            every UI string, in English (the default)
  lib/i18n/fr.ts            French translation (same keys, checked by the compiler)
  lib/i18n/lang.svelte.ts   language choice (automatic or per device)
  lib/store.svelte.ts       app state, WebSocket client, startup cache
  lib/router.svelte.ts      hash routing without page loads
  lib/browserPlayer.ts      <audio> player for "This browser", Media Session
  lib/icons.ts              SVG icon set
  lib/contextMenu.svelte.ts the action menu (⋯ sheet or right-click), shown by
                            components/ContextMenu.svelte
  lib/menus.ts              menu entries for tracks, queue, albums, playlists,
                            artists
  components/               UI (PlayerBar, NowPlaying, QueueView, DevicePicker…)
frontend/public/            manifest, service worker, icons
scripts/make_icons.py       regenerates the PWA icons
```

## License

[MIT](LICENSE)
