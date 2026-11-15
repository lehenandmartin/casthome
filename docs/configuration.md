# Configuration

Most of CastHome is configured from the browser: the first visit asks for the
music server connection and how to protect CastHome, then **Settings** covers the
rest. This page covers installation details, environment variables, access
modes, reverse proxies and sessions.

- [Installation details](#installation-details)
- [Updating](#updating)
- [Environment variables](#environment-variables)
- [Access](#access)
- [Behind a reverse proxy](#behind-a-reverse-proxy)
- [Sessions](#sessions)
- [Other Subsonic servers](#other-subsonic-servers)

## Installation details

The image is `ghcr.io/lehenandmartin/casthome` (amd64 and arm64, so a
Raspberry Pi works too). Paste [`docker-compose.yml`](../docker-compose.yml)
as a stack in Portainer, Dockge, etc., or use it with `docker compose`.

Everything is saved under `./data`; no `.env` is needed. The setup is open to
whoever opens CastHome first, so do it right after starting it.

**Host network.** `network_mode: host` is **required**: Cast discovery uses
mDNS multicast, which does not cross Docker's bridge network. Docker Desktop
on macOS/Windows does not support this reliably; run CastHome natively there
(see [CONTRIBUTING](../CONTRIBUTING.md#development)).

**Port.** To use another port than 4577, set `PORT` under `environment:` in
`docker-compose.yml` (a `ports:` mapping has no effect with
`network_mode: host`):

```yaml
    environment:
      PORT: "8090"
```

**File ownership.** The container starts as root only to give `./data` to the
user CastHome runs as (`PUID`:`PGID`, default `1000:1000`), then drops to that
user. On a NAS, set `PUID`/`PGID` in `docker-compose.yml` to the owner you
want for the folder.

**Build the image yourself**, from a clone of the repository:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

## Updating

```bash
docker compose pull && docker compose up -d
```

`:latest` is the last release. To control updates, pin a version in
`docker-compose.yml` (`:0.3` takes the fixes of 0.3, `:0.3.0` never moves);
`:main` follows the development branch. The running version is shown in
**Settings → About**. See the [releases](https://github.com/lehenandmartin/casthome/releases) for what changed.

## Environment variables

The music server connection, access and playback options are set in the browser
and apply from the next track, without a restart. Environment variables are
optional, in `.env` or the container environment; see
[`.env.example`](../.env.example). A server value set there wins over the
one saved from the browser and shows as locked in Settings (handy for
scripted installs).

| Variable | Purpose |
|---|---|
| `NAVIDROME_URL` | Music server URL used by the backend (Navidrome or another Subsonic server). |
| `NAVIDROME_PUBLIC_URL_FOR_CAST` | Music server URL used by the Cast devices (defaults to `NAVIDROME_URL`). LAN IP or LAN-resolvable name, never `localhost` or a container name. |
| `NAVIDROME_USERNAME`, `NAVIDROME_PASSWORD` | The music server account to play with. |
| `APP_SECRET_KEY` | Encryption key for the stored music server password (≥ 32 chars). By default one is generated into `data/secret.key`; keep that file with the database. |
| `PORT` | Listening port (default `4577`). |
| `PUID`, `PGID` | User and group CastHome runs as (default `1000`). |
| `COOKIE_SECURE` | `true` when CastHome is behind HTTPS. |
| `FORWARDED_ALLOW_IPS` | Reverse proxies trusted to give the visitor's address (IPs or networks, comma-separated; default `127.0.0.1,::1`). See [Behind a reverse proxy](#behind-a-reverse-proxy). |
| `SESSION_REMEMBER_DAYS` / `SESSION_SHORT_HOURS` | Session lifetimes (both sliding). |
| `STREAM_FORMAT`, `STREAM_MAX_BITRATE` | `raw` (default) streams original files; otherwise a transcoding format of the server (`mp3`, `aac`, `opus`) and a limit in kbps. Also in Settings. |
| `TRANSCODE_FALLBACK_FORMAT` | Format for files Cast cannot play, and retry format after a playback error (default `mp3`). |
| `CAST_PRELOAD_NEXT` | On by default: hand the next track to the device 20 s before the end of the current one to shorten the gap. `false` disables it. Also in Settings. |
| `CAST_KNOWN_HOSTS` | Cast device IPs, when mDNS is blocked. Also in Settings. |
| `SCROBBLE` | On by default: report plays to the music server ("now playing" and scrobbles). `false` disables it. Also in Settings. |
| `SHOW_RATINGS` | On by default: show the 5-star ratings (album pages, action menus) on every device. `false` hides them. Also in Settings. |

## Access

Chosen during the setup, changed in **Settings → Access to CastHome** (the
current CastHome password is asked first):

- **Password** (recommended): a CastHome password on every device.
- **Open at home**: no password from a private address (local network), the
  password from anywhere else. Behind a reverse proxy, see
  [Behind a reverse proxy](#behind-a-reverse-proxy).
- **No password**: anyone who can reach CastHome can use it.

Setting a new password signs every other device out. Sign-in attempts are
rate-limited per address.

The CastHome password is separate from the music server's. If the server later
refuses the saved password (it was changed there), you stay signed in to
CastHome: a banner asks you to update it in **Settings → Music server**, where
the connection can be tested before saving. The saved password is only ever
sent to the server and account it was saved for; pointing CastHome at another
one asks for the password again.

## Behind a reverse proxy

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

Behind HTTPS, also set `COOKIE_SECURE: "true"`.

## Sessions

- **Keep me signed in** checked: a 1-year cookie (`HttpOnly`, `SameSite=Lax`)
  whose expiry slides forward each time you use the app. It survives browser
  and container restarts (sessions are stored in SQLite under `DATA_DIR`).
- Unchecked: a browser-session cookie, also expiring after
  `SESSION_SHORT_HOURS` of inactivity.
- Signed-in devices are listed in Settings, where each can be signed out,
  alone or all others at once, effective immediately (not shown with **No
  password**).

## Other Subsonic servers

CastHome is made for Navidrome (0.50 or later), but works with any server
that speaks the Subsonic API and accepts token sign-in (`t` and `s`
parameters), such as Gonic (tested). It recognises the server from its answers;
with a server other than Navidrome, what needs Navidrome's own API is left
out:

| Feature | Without Navidrome |
|---|---|
| **Tracks** page (every track, sorted) | Hidden: the Subsonic API cannot list every track. Favorite tracks still open from Home and artist pages. |
| Favorite tracks and albums | From `getStarred2`, sorted by CastHome. Sorts by play count or last play depend on what the server reports. |
| *On repeat* (Home) | Hidden: it needs the last play date of each track. |
| *Popular* (artist page) | Only when the server answers `getTopSongs`. |
| Radio | Depends on the server's `getSimilarSongs`/`getSimilarSongs2`; some servers have none. |

The variables keep their `NAVIDROME_` names whatever the server.

The Cast devices stream with a token URL, so a server or account that refuses
token sign-in (an LDAP user, for example) cannot be used: the connection test
says so.
