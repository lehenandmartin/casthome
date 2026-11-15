"""A tiny Subsonic server for the end-to-end tests: one artist, one album of
three short silent tracks. Standard library only.

    python fake_subsonic.py [port]

Any user is accepted with the password "sesame" (token sign-in). Endpoints
it does not know answer an empty "ok", which CastHome reads as "nothing".
"""

from __future__ import annotations

import hashlib
import io
import json
import struct
import sys
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PASSWORD = "sesame"
ARTIST = {"id": "ar1", "name": "Fake Artist", "albumCount": 1, "coverArt": "ar1"}
SONGS = [
    {
        "id": f"s{n}",
        "title": title,
        "artist": "Fake Artist",
        "artistId": "ar1",
        "album": "Fake Album",
        "albumId": "al1",
        "coverArt": "al1",
        "track": n,
        "discNumber": 1,
        "duration": 30,
        "suffix": "wav",
        "contentType": "audio/wav",
        "bitRate": 1411,
        "isDir": False,
        "type": "music",
    }
    for n, title in enumerate(["Song One", "Song Two", "Song Three"], start=1)
]
ALBUM = {
    "id": "al1",
    "name": "Fake Album",
    "artist": "Fake Artist",
    "artistId": "ar1",
    "coverArt": "al1",
    "year": 2026,
    "genre": "Test",
    "songCount": len(SONGS),
    "duration": sum(s["duration"] for s in SONGS),
    "created": "2026-01-01T00:00:00Z",
}


def silent_wav(seconds: int = 30, rate: int = 8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(rate)
        w.writeframes(struct.pack("B", 128) * rate * seconds)
    return buf.getvalue()


WAV = silent_wav()
# A 1x1 grey PNG.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c636868680000040401018a1c2f7e0000000049454e44ae426082"
)


def answer(endpoint: str, q: dict[str, str]) -> dict:
    if endpoint == "getAlbumList2":
        return {"albumList2": {"album": [ALBUM] if int(q.get("offset", 0)) == 0 else []}}
    if endpoint == "getAlbum":
        return {"album": {**ALBUM, "song": SONGS}}
    if endpoint == "getArtists":
        return {"artists": {"index": [{"name": "F", "artist": [ARTIST]}]}}
    if endpoint == "getArtist":
        return {"artist": {**ARTIST, "album": [ALBUM]}}
    if endpoint == "getSong":
        song = next((s for s in SONGS if s["id"] == q.get("id")), SONGS[0])
        return {"song": song}
    if endpoint == "getGenres":
        return {"genres": {"genre": [{"value": "Test", "songCount": 3, "albumCount": 1}]}}
    if endpoint == "getSongsByGenre":
        return {"songsByGenre": {"song": SONGS}}
    if endpoint == "search3":
        text = q.get("query", "").strip('"').lower()
        hit = text in "fake album song one two three artist"
        return {"searchResult3": {"artist": [ARTIST], "album": [ALBUM], "song": SONGS} if hit else {}}
    if endpoint == "getStarred2":
        return {"starred2": {}}
    if endpoint == "getPlaylists":
        return {"playlists": {"playlist": []}}
    if endpoint == "getOpenSubsonicExtensions":
        return {"openSubsonicExtensions": []}
    return {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:  # quiet
        pass

    def do_GET(self) -> None:
        self.handle_request(urlparse(self.path).query)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode()
        self.handle_request(urlparse(self.path).query + "&" + body)

    def handle_request(self, query: str) -> None:
        path = urlparse(self.path).path
        if not path.startswith("/rest/"):
            return self.send(404, b"", "text/plain")
        endpoint = path.removeprefix("/rest/").removesuffix(".view")
        q = {k: v[0] for k, v in parse_qs(query).items()}
        salt, token = q.get("s", ""), q.get("t", "")
        if hashlib.md5((PASSWORD + salt).encode()).hexdigest() != token:
            return self.json({"status": "failed", "error": {"code": 40, "message": "Wrong username or password"}})
        if endpoint == "stream":
            return self.send(200, WAV, "audio/wav")
        if endpoint == "getCoverArt":
            return self.send(200, PNG, "image/png")
        self.json({"status": "ok", **answer(endpoint, q)})

    def json(self, payload: dict) -> None:
        body = {"subsonic-response": {"version": "1.16.1", "type": "fake", "openSubsonic": True, **payload}}
        self.send(200, json.dumps(body).encode(), "application/json")

    def send(self, code: int, data: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Accept-Ranges", "none")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_HEAD(self) -> None:
        self.do_GET()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4599
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
