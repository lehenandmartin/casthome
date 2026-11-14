// Interface options set in Settings and stored by CastHome, so they are the
// same on every device (like scrobbling). The server sends them with /auth/me
// when the app starts; Settings updates them at once when saved.
//
// Each device also remembers the last value it received, to start with it:
// otherwise hidden ratings showed for a moment until the server answered.
//
// ratings: show the 5-star ratings (album pages, action menus). Some people
// never rate anything; they can hide them.

const RATINGS_KEY = 'casthome.showRatings';

function remembered(): boolean {
  try {
    return localStorage.getItem(RATINGS_KEY) !== 'false';
  } catch {
    return true;
  }
}

export const display = $state({ ratings: remembered() });

/** Apply the server's value (and remember it for the next start). */
export function setShowRatings(show: boolean): void {
  display.ratings = show;
  try {
    localStorage.setItem(RATINGS_KEY, String(show));
  } catch {
    /* private browsing: the server's value still applies once it answers */
  }
}
