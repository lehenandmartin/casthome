// Every user-facing string lives here. To add a language, copy this file
// (e.g. fr.ts), translate the values and register it in ./index.ts.
export const en = {
  'app.name': 'CastHome',

  'login.title': 'Sign in',
  'login.subtitleNoUser': 'Use your Navidrome password.',
  'login.password': 'Password',
  'login.remember': 'Keep me signed in on this device',
  'login.submit': 'Sign in',
  'login.submitting': 'Signing in…',

  'nav.albums': 'Albums',
  'nav.queue': 'Queue',
  'nav.signOut': 'Sign out',

  'albums.newest': 'Recently added',
  'albums.empty': 'No albums found.',
  'albums.loadMore': 'Load more',

  'album.play': 'Play',
  'album.playNext': 'Play next',
  'album.addToQueue': 'Add to queue',
  'album.tracks': '{count} tracks',

  'devices.title': 'Play on',
  'devices.none': 'No Cast device found yet. Discovery is running…',
  'devices.choose': 'Choose a device',
  'devices.group': 'Group',
  'devices.disconnected': 'Not connected',

  'player.play': 'Play',
  'player.pause': 'Pause',
  'player.next': 'Next',
  'player.previous': 'Previous',
  'player.shuffle': 'Shuffle',
  'player.repeat.off': 'Repeat: off',
  'player.repeat.all': 'Repeat: all',
  'player.repeat.one': 'Repeat: one',
  'player.volume': 'Volume',
  'player.nothing': 'Nothing playing',
  'player.loading': 'Loading…',

  'queue.title': 'Queue',
  'queue.empty': 'The queue is empty. Pick an album to start.',
  'queue.clear': 'Clear queue',
  'queue.count': '{count} tracks',

  'connection.offline': 'Reconnecting to CastHome…',

  // Error and notification codes sent by the backend
  'error.invalid_credentials': 'Wrong password.',
  'error.too_many_attempts': 'Too many attempts. Try again in a few minutes.',
  'error.not_signed_in': 'Please sign in again.',
  'error.navidrome_unavailable': 'Navidrome is unreachable.',
  'error.navidrome_error': 'Navidrome returned an error: {message}',
  'error.no_device': 'Choose a Cast device first.',
  'error.device_not_found': 'This device is no longer available.',
  'error.device_unreachable': 'The Cast device is unreachable.',
  'error.device_disconnected': 'Lost connection to the Cast device. Reconnecting…',
  'error.device_taken_over': 'Another app is now using the Cast device.',
  'error.track_unplayable': 'Cannot play “{title}”, skipped.',
  'error.too_many_errors': 'Playback stopped after several unplayable tracks.',
  'error.queue_ended': 'End of the queue.',
  'error.nothing_to_play': 'Nothing to play.',
  'error.invalid_queue_index': 'This track is no longer in the queue.',
  'error.forbidden_origin': 'Request blocked (cross-site).',
  'error.navidrome_password_changed': 'Your Navidrome password changed. Please sign in again.',
  'error.unknown': 'Something went wrong.',
} as const;

export type MessageKey = keyof typeof en;
