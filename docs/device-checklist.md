# Device checklist

What the automated tests cannot see: real browsers, real phones, real Cast
devices. Run it before tagging a release (see *Releases* in [CONTRIBUTING](../CONTRIBUTING.md#releases)), or
after a change to playback, navigation or the layout. About 20 minutes.

Copy the list into the release notes or an issue and tick as you go. A failed
item gets a line of its own: device, browser version, what happened.

## Before you start

- [ ] `pytest`, `ruff check`, `mypy casthome` (backend) and `npm test`,
      `npm run check`, `npm run build` (frontend) pass.
- [ ] The server runs the version under test (**Settings → About**).
- [ ] At least two albums with covers, one multi-disc album, one track in a
      format Cast does not play (e.g. DSF or ALAC) to check transcoding.

## Every browser (quick pass)

Do this once per browser below, in light and dark mode.

- [ ] Sign in, sign out, sign in again with *Keep me signed in*.
- [ ] Home, Library (albums, artists, tracks, genres, playlists), an album,
      an artist, a genre, a playlist, Search, Settings: no layout overflow,
      no element hidden under the player bar or the tab bar.
- [ ] Back and forward (browser buttons, swipe on iOS) restore the scroll
      position; pages fade in, nothing slides or flashes.
- [ ] Search: tapping the tab opens the keyboard with the field focused.
- [ ] Action menu on a track: play now, add to queue, go to album/artist,
      star, rate (hidden when ratings are switched off in Settings).
- [ ] Now Playing opens and closes smoothly; the queue reorders by drag.
- [ ] Interface errors: none logged by the server (`casthome.client` warnings).

## Browsers and phones

### iPhone — installed app (Add to Home Screen)

- [ ] Opens full screen below the status bar; sign-in is asked once inside it.
- [ ] Links never reload the whole app.
- [ ] Play in the browser ("This browser"): screen locked, app in the
      background, back in the app — playback continues.
- [ ] Lock screen and Dynamic Island show **previous / next** (not ±10 s),
      with the cover and title; both buttons work.
- [ ] Headphone controls (play/pause, next).
- [ ] No volume control for "This browser" (hardware buttons only), and it
      plays at full volume.
- [ ] Leaving the app open for a few minutes then coming back: the state is
      right within a second, no stale track.

### Android — Chrome

- [ ] Add to Home screen (or *Install app* over HTTPS); opens without the
      browser's address bar.
- [ ] Play in the browser with the screen off; notification controls work.
- [ ] Back gesture closes Now Playing / menus before leaving the page.

### Computer — Chrome, Firefox, Safari

- [ ] Wide layout: library grids fill the width, the queue is readable.
- [ ] Keyboard: Tab reaches every control, Escape closes menus and sheets,
      Enter in Search runs it.
- [ ] Play in the browser: seeking, next at the end of a track, the
      transcoded track plays.
- [ ] Two tabs open: commands in one show up in the other at once.

## Cast

### One speaker

- [ ] Pick the speaker: playback moves to it at the same position.
- [ ] Play an album; next/previous; seek; volume; mute.
- [ ] Phone: − and + around the volume slider move it by 5 %. Computer: the
      `+` and `-` keys do the same.
- [ ] Let a track end: the next one starts by itself (with Preloading on,
      without a gap) — also with every browser closed.
- [ ] Edit the queue during the last 20 s of a track: the right track
      follows anyway.
- [ ] The track Cast cannot play is retried transcoded and plays.
- [ ] Restart the server while playing: music does not stop, the interface
      shows *Reconnecting* briefly, then the right state.
- [ ] Unplug the speaker while playing: the player shows buffering and
      holds the position; plug it back: *Playback stopped on the Cast
      device*, and Play resumes where it was.
- [ ] Start something from the Google Home app or a phone: CastHome shows
      *Another app is now using the Cast device* and stops.
- [ ] Scrobbles reach the music server (if scrobbling is on).

### A speaker group

- [ ] Play on the group; tracks chain by themselves.
- [ ] Move playback from the group to one of its speakers and back.

### A TV (Chromecast with a screen)

- [ ] The cover, title and artist show on the TV.
- [ ] Pause/play from the TV remote is reflected in CastHome.
- [ ] Switching the TV to another input or app: CastHome stops cleanly.

## After

- [ ] Server log: no errors or tracebacks during the session.
- [ ] Note anything that failed in the release notes, fixed or not.
