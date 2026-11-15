# Troubleshooting

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
pulling the new image (or, in development, `npm run build`), close the app
completely (swipe it away) and reopen it.

**"Reconnecting to CastHome…" stays on screen.** The WebSocket cannot reach the
server: check CastHome is running and reachable from the phone. Playback on a
Cast device continues meanwhile; the app catches up when it reconnects.

**Some files skip.** Cast cannot play WMA, APE, ALAC, DSD or > 96 kHz files.
CastHome transcodes those (and retries after an error) with
`TRANSCODE_FALLBACK_FORMAT`; make sure transcoding (ffmpeg) works on the music server.

**"Open at home" asks for the password at home.** CastHome is behind a reverse
proxy it does not trust. See
[Behind a reverse proxy](configuration.md#behind-a-reverse-proxy).
