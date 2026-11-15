<h1 align="center">CastHome</h1>
<h3 align="center">Reliable casting of your <a href="https://www.navidrome.org/">Navidrome</a> library to Google Cast speakers: the speaker streams from the source, your phone is just the remote.</h3>

<p align="center">
  <a href="https://github.com/lehenandmartin/casthome/releases"><img src="https://img.shields.io/github/v/release/lehenandmartin/casthome" alt="Latest release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/lehenandmartin/casthome" alt="License"></a>
  <a href="https://github.com/lehenandmartin/casthome/pkgs/container/casthome"><img src="https://img.shields.io/badge/Docker-amd64%20%7C%20arm64-2496ED?logo=docker&logoColor=white" alt="Docker image for amd64 and arm64"></a>
</p>

<img alt="Screenshot of CastHome" src="https://github.com/user-attachments/assets/4c1ebe9e-f89a-40c3-88d3-85bc6436afd1" />

---

Casting a self-hosted library to Chromecasts or Nest speakers usually goes
through a player app on your phone, and the music depends on that app:
the phone locks, the app is put to sleep or the Wi-Fi blinks, and the cast
drops, stops at the end of the track, or loses its queue.

CastHome takes another approach, inspired by the principle behind Spotify
Connect: a small server on your home network drives the speakers itself, and
**the speaker streams straight from Navidrome**. Your phone, or any browser, is only the remote: pick a speaker,
press play, put the phone away, and the music keeps going, track after track.

**CastHome is a web app, not a native iOS or Android app.** Open it in any
browser, or add it to your home screen to use it like an app (PWA): nothing
to install from a store.

## Why CastHome

- **Playback that doesn't depend on your phone.** The queue lives on the
  server, which moves on to the next track itself. Lock the phone, close
  every tab, switch it off: the speaker keeps playing.
- **Built to stay connected.** A track the speaker cannot play is retried
  transcoded; the next track is preloaded to shorten gaps; after a restart
  CastHome picks the speaker back up where it was, without a gap; when a
  speaker becomes unreachable it holds the position instead of losing it.
- **Any browser is a remote.** The Cast SDK only runs in Chrome; since
  CastHome's server does the casting, Firefox, Safari and iPhones work just as
  well, and several devices can control the same playback.
- **Nothing to sync.** Navidrome stays the only library. The queue is your
  Navidrome play queue, so other Subsonic clients can pick it up.
- **Feels like a streaming app.** A familiar queue (what you add plays next, then the album carries on), endless radio, swipe
  gestures, and an installable app on your home screen.

## Features

- **Speakers and groups:** Chromecast, Google/Nest speakers, TVs and speaker
  groups, or *This browser* to play on the device you are holding. Switch
  device mid-track and it carries on at the same position.
- **Queue:** *Next in queue* before the rest of the album or playlist, drag to
  reorder, swipe to add or remove, save as a playlist.
- **Radio:** endless track radio and artist radio, using Last.fm or
  AudioMuse-AI through Navidrome, with fallbacks when a service is down.
- **Library:** albums, artists, genres, every track with useful sorts,
  search, playlists, favorites, 5-star ratings, similar artists, popular
  tracks.
- **Mobile-first, desktop-ready:** tab bar, mini player and full-screen Now
  Playing on phones; sidebar, queue panel, right-click menus and drag and drop
  on desktop. Installable as an app (PWA), lock-screen controls included.
- **Scrobbling** to Navidrome, shorter gaps by preloading the next
  track, automatic transcoding of files the speakers cannot play.
- **Setup in the browser:** no config file. Sign in to Navidrome, choose how
  to protect CastHome, done.
- English and French.

See the [user guide](docs/usage.md) for the full tour.

## Requirements

- A [Navidrome](https://www.navidrome.org/) server.
- A **Linux host** with Docker (a Raspberry Pi works), on the same network as
  your speakers. CastHome uses Docker's host network for speaker discovery,
  which Docker Desktop on macOS/Windows does not support reliably.
- A home network. CastHome is meant for a trusted LAN; its password keeps
  casual visitors out, but it is not hardened to be exposed to the Internet.

## Quick start

```bash
mkdir casthome && cd casthome && curl -fsSLO https://raw.githubusercontent.com/lehenandmartin/casthome/main/docker-compose.yml && docker compose up -d
```

Or paste [`docker-compose.yml`](docker-compose.yml) as a stack in Portainer,
Dockge, etc.

Then open `http://<host-ip>:4577` **right away** (the setup is open to whoever
comes first): enter your Navidrome URL and account, choose how to protect
CastHome, and play.

To update:

```bash
docker compose pull && docker compose up -d
```

Changing the port, file ownership on a NAS, pinning a version: see
[Configuration](docs/configuration.md).

### Behind a reverse proxy

Add the proxy's address to `FORWARDED_ALLOW_IPS` so CastHome can tell local
visitors from the others; see
[Behind a reverse proxy](docs/configuration.md#behind-a-reverse-proxy).

## Documentation

- [User guide](docs/usage.md): the interface, the queue, radio, gestures,
  installing the app.
- [Configuration](docs/configuration.md): installation details, environment
  variables, access modes, reverse proxy, sessions.
- [Troubleshooting](docs/troubleshooting.md): no speaker found, nothing plays,
  files that skip.
- [How it works](docs/how-it-works.md): architecture, credentials, playback
  rules.
- [Releases](https://github.com/lehenandmartin/casthome/releases): what changed in each version.
- [Contributing](CONTRIBUTING.md): development setup, tests, releases.

## About

This project was built with the assistance of [Claude](https://claude.ai), under the author's direction and review.

## License

[MIT](LICENSE) — © 2026 Martin Le Hénand

Third-party components, bundled in the Docker image: [FastAPI](https://github.com/fastapi/fastapi), [PyChromecast](https://github.com/home-assistant-libs/pychromecast), [aiosqlite](https://github.com/omnilib/aiosqlite), [pydantic-settings](https://github.com/pydantic/pydantic-settings), [Svelte](https://github.com/sveltejs/svelte) and [svelte-dnd-action](https://github.com/isaacHagoel/svelte-dnd-action) (MIT), [Uvicorn](https://github.com/encode/uvicorn) and [HTTPX](https://github.com/encode/httpx) (BSD-3-Clause), [cryptography](https://github.com/pyca/cryptography) (Apache-2.0 or BSD-3-Clause), and [Pillow](https://github.com/python-pillow/Pillow) (MIT-CMU).
