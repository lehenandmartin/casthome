// Interface options set in Settings and stored by CastHome, so they are the
// same on every device (like scrobbling). The server sends them with /auth/me
// when the app starts; Settings updates them at once when saved.
//
// ratings: show the 5-star ratings (album pages, action menus). Some people
// never rate anything; they can hide them.

export const display = $state({ ratings: true });
