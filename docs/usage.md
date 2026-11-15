# Using CastHome

Most of CastHome explains itself. This page covers what is not obvious from
the interface.

## The queue

*Now playing*, then **Next in queue** (the tracks you added with *Add to
queue*, in the order you added them), then **Next from: <album or
playlist>** (the rest of what you started), then *Played* (collapsed).

- *Add to queue* always goes to *Next in queue*: an added track plays right
  after the current one, then the album carries on where it was.
- Starting another album keeps *Next in queue*; shuffle never mixes it.
- *Clear* empties *Next in queue* only; the queue's menu clears everything or
  saves the whole queue as a playlist.
- On desktop, tracks can be dragged from any list into the open queue panel.

## Gestures and menus

- **Swipe (touch screens):** swipe a track right to add it to *Next in
  queue*; swipe left in the queue to remove it. In the queue, the reorder
  handle sits on the right, under the thumb.
- **Long-press (touch) or right-click (mouse):** opens the menu of a track,
  queue row, album, playlist, artist or the current track. Arrow keys move
  through it, Escape closes it. Shift + right-click keeps the browser's own
  menu.
- **Keyboard (computer):** Space plays or pauses, `/` opens the search.
  Neither works while typing in a field, and Space keeps ticking a focused
  checkbox.

## Radio

*Start radio* on a track (its menu, or Now Playing) or on an artist plays it,
then similar music, and keeps adding more as it plays. Started from the
track being played, that track carries on without restarting. Tracks in
*Next in queue* stay first; starting an album or a playlist ends the radio.

Similar tracks come from the music server. On Navidrome: AudioMuse-AI when
that plugin is active (track radio only), else Last.fm and its other agents, with
fallbacks so the radio still works when one of them is down. The queue shows
which source was used.

## Install as an app

- **iPhone/iPad (Safari):** Share → *Add to Home Screen*. Works over plain
  HTTP. The home-screen app has its own cookies: sign in once inside it.
- **Android/desktop Chrome:** *Install app* in the menu, offered only over
  **HTTPS**. Over plain HTTP, *Add to Home screen* creates a shortcut
  instead.

After an update, close the installed app completely (swipe it away) and
reopen it to get the new version.

## Playing in the browser

Until you pick a Cast device, Play uses the browser you are on (*This
browser* in the device list). The server still owns the queue; lock-screen
and headset controls work.

Closing or reloading that tab stops playback. On iOS, Safari may suspend a
background tab and only follows the hardware volume buttons: for long
listening with the screen locked, use a Cast device.

## Good to know

- **Scrobbling** (on by default, in Settings → Playback): "now playing" when
  a track starts, a scrobble after half the track or 4 minutes of actual
  listening; seeking forward does not count.
- **Favorites filter:** the ★ filter on the Tracks, Albums and Artists pages
  is kept in the address (`?fav=1`), so links and Back keep it.
- **Ratings** can be hidden for every device in Settings → Playback.
- **Language:** English, French, German or Spanish, in Settings → Language
  (automatic follows the browser's language), chosen on each device.
