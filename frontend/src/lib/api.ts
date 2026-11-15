import type {
  AccessForm,
  AddMode,
  AppStatus,
  Me,
  NavidromeForm,
  PlaybackOptions,
  ServerSettings,
  SetupInfo,
  Album,
  AlbumListType,
  Artist,
  ArtistDetail,
  ArtistHighlights,
  HomeData,
  Genre,
  Playlist,
  SessionInfo,
  SongPage,
  SongSort,
  RepeatMode,
  SearchResult,
  Song,
  StarKind,
} from './types';

import * as cache from './cache';

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public params: Record<string, unknown> = {},
  ) {
    super(code);
  }
}

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

// Runs before any command that starts playback, e.g. to pick "This browser"
// when no device was chosen yet.
let beforePlay: () => Promise<void> = async () => {};
export function setBeforePlayHook(hook: () => Promise<void>): void {
  beforePlay = hook;
}

const PLAY_PATHS = new Set(['/player/play', '/player/toggle', '/player/jump', '/radio']);
function startsPlayback(method: string, path: string, body: unknown): boolean {
  if (method !== 'POST') return false;
  if (PLAY_PATHS.has(path)) return true;
  return path === '/queue' && (body as { mode?: string } | undefined)?.mode === 'now';
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  if (startsPlayback(method, path, body)) await beforePlay();
  const response = await fetch(`/api${path}`, {
    method,
    credentials: 'same-origin',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login' && !path.startsWith('/setup')) onUnauthorized();
    throw new ApiError(response.status, data.code ?? 'unknown', data.params ?? {});
  }
  return data as T;
}

/** A GET remembered in the cache (see cache.ts), keyed by its path. */
function get<T>(path: string, maxAge?: number): Promise<T> {
  return cache.remember(path, () => request<T>('GET', path), maxAge);
}

// Paths of the remembered requests, shared with `cached` below.
const paths = {
  albums: (type: AlbumListType, size: number, offset: number, genre?: string, starred = false) =>
    `/library/albums?type=${type}&size=${size}&offset=${offset}` +
    (genre ? `&genre=${encodeURIComponent(genre)}` : '') +
    (starred ? '&starred=true' : ''),
  artists: () => '/library/artists',
  artist: (id: string) => `/library/artists/${encodeURIComponent(id)}`,
  similarArtists: (id: string) => `/library/artists/${encodeURIComponent(id)}/similar`,
  artistHighlights: (id: string) => `/library/artists/${encodeURIComponent(id)}/highlights`,
  genres: () => '/library/genres',
  album: (id: string) => `/library/albums/${encodeURIComponent(id)}`,
  playlists: () => '/playlists',
  playlist: (id: string) => `/playlists/${encodeURIComponent(id)}`,
  songs: (sort: SongSort, offset: number, size: number, starred: boolean, artistId?: string) =>
    `/library/songs?sort=${sort}&offset=${offset}&size=${size}` +
    (starred ? '&starred=true' : '') +
    (artistId ? `&artist_id=${encodeURIComponent(artistId)}` : ''),
};

/** The last response of a request, without asking the server (undefined if never loaded). */
export const cached = {
  artists: () => cache.peek<Artist[]>(paths.artists()),
  artist: (id: string) => cache.peek<ArtistDetail>(paths.artist(id)),
  similarArtists: (id: string) => cache.peek<Artist[]>(paths.similarArtists(id)),
  artistHighlights: (id: string) => cache.peek<ArtistHighlights>(paths.artistHighlights(id)),
  genres: () => cache.peek<Genre[]>(paths.genres()),
  album: (id: string) => cache.peek<Album>(paths.album(id)),
  playlists: () => cache.peek<Playlist[]>(paths.playlists()),
  playlist: (id: string) => cache.peek<Playlist>(paths.playlist(id)),
  /** What a list showed about this album or artist (name, cover...), before its page loads. */
  albumSummary: cache.albumSummary,
  artistSummary: cache.artistSummary,
};

/** Start loading a page's data ahead of time (e.g. when a link is touched). */
export function prefetch(href: string): void {
  const match = href.match(/^#\/(album|artist|playlist)\/(.+)$/);
  if (!match) return;
  const id = decodeURIComponent(match[2]);
  const ignore = () => {};
  if (match[1] === 'album') api.album(id).catch(ignore);
  else if (match[1] === 'artist') api.artist(id).catch(ignore);
  else api.playlist(id).catch(ignore);
}

// `v`: bumped when covers change format, so browsers drop the ones they cached
// for a week (v2: WebP made by CastHome, see backend covers.py).
export const coverUrl = (id: string | null, size = 300): string | null =>
  id ? `/api/cover/${encodeURIComponent(id)}?size=${size}&v=2` : null;

const { rememberAlbums, rememberArtists } = cache;
const withAlbums = (list: Album[]) => (rememberAlbums(list), list);
const withArtists = (list: Artist[]) => (rememberArtists(list), list);
const expirePlaylists = () => cache.expire('/playlists');
// Favourites and ratings show in many pages: they all refresh on their next visit.
const expireLibrary = () => cache.expire('/');

export const api = {
  status: () => request<AppStatus>('GET', '/status'),
  setupInfo: () => request<SetupInfo>('GET', '/setup'),
  setupTest: (navidrome: NavidromeForm) => request<{ ok: true }>('POST', '/setup/test', navidrome),
  setup: (navidrome: NavidromeForm | null, access: AccessForm | null) =>
    request<{ ok: true }>('POST', '/setup', { navidrome, access }),
  settings: () => request<ServerSettings>('GET', '/settings'),
  testNavidrome: (navidrome: NavidromeForm) => request<{ ok: true }>('POST', '/settings/navidrome/test', navidrome),
  updateNavidrome: (navidrome: NavidromeForm) => request<{ ok: true }>('PUT', '/settings/navidrome', navidrome),
  updatePlayback: (playback: PlaybackOptions) => request<{ ok: true }>('PUT', '/settings/playback', playback),
  updateAccess: (access: AccessForm) => request<{ ok: true }>('PUT', '/settings/access', access),

  login: (password: string, remember: boolean) => request<{ ok: true }>('POST', '/auth/login', { password, remember }),
  logout: () => request<void>('POST', '/auth/logout'),
  me: () => request<Me>('GET', '/auth/me'),
  sessions: () => request<SessionInfo[]>('GET', '/sessions'),
  revokeSession: (id: string) => request<void>('DELETE', `/sessions/${encodeURIComponent(id)}`),
  revokeOtherSessions: () => request<void>('DELETE', '/sessions'),

  albums: (type: AlbumListType = 'newest', size = 40, offset = 0, genre?: string, starred = false) =>
    // Random lists are new on every request, as before.
    (type === 'random'
      ? request<Album[]>('GET', paths.albums(type, size, offset, genre, starred))
      : get<Album[]>(paths.albums(type, size, offset, genre, starred))
    ).then(withAlbums),
  artists: () => get<Artist[]>(paths.artists()).then(withArtists),
  artist: (id: string) =>
    get<ArtistDetail>(paths.artist(id)).then((a) => {
      rememberAlbums(a.albums);
      return a;
    }),
  /** Similar artists in the library (Last.fm, then similar tracks), for the artist page. */
  similarArtists: (id: string) => get<Artist[]>(paths.similarArtists(id), 300_000).then(withArtists),
  artistHighlights: (id: string) => get<ArtistHighlights>(paths.artistHighlights(id), 300_000),
  genres: () => get<Genre[]>(paths.genres()),
  genreSongs: (genre: string, count = 200) =>
    request<Song[]>('GET', `/library/genres/${encodeURIComponent(genre)}/songs?count=${count}`),
  search: (q: string, limit = 20) =>
    request<SearchResult>('GET', `/library/search?q=${encodeURIComponent(q)}&limit=${limit}`).then((r) => {
      rememberAlbums(r.albums);
      rememberArtists(r.artists);
      return r;
    }),
  album: (id: string) => get<Album>(paths.album(id)),
  starred: () => request<SearchResult>('GET', '/library/starred'),
  setStarred: (kind: StarKind, id: string, starred: boolean) =>
    request<void>('PUT', '/library/star', { kind, id, starred }).finally(expireLibrary),
  setRating: (id: string, rating: number) =>
    request<void>('PUT', '/library/rating', { id, rating }).finally(expireLibrary),

  playlists: () => get<Playlist[]>(paths.playlists()),
  playlist: (id: string) => get<Playlist>(paths.playlist(id)),
  createPlaylist: (name: string, songIds: string[] = [], fromQueue = false) =>
    request<Playlist>('POST', '/playlists', { name, song_ids: songIds, from_queue: fromQueue }).finally(expirePlaylists),
  updatePlaylist: (id: string, changes: { name?: string; add_song_ids?: string[]; remove_indexes?: number[] }) =>
    request<void>('PATCH', `/playlists/${encodeURIComponent(id)}`, changes).finally(expirePlaylists),
  deletePlaylist: (id: string) =>
    request<void>('DELETE', `/playlists/${encodeURIComponent(id)}`).finally(expirePlaylists),
  playPlaylist: (id: string, startIndex = 0) =>
    request<void>('POST', '/queue', { playlist_id: id, mode: 'now', start_index: startIndex }),
  queuePlaylist: (id: string) =>
    request<void>('POST', '/queue', { playlist_id: id, mode: 'queue', replace: false }),

  selectDevice: (uuid: string) => request<void>('PUT', '/player/device', { uuid }),
  action: (name: 'play' | 'pause' | 'toggle' | 'next' | 'previous' | 'stop') =>
    request<void>('POST', `/player/${name}`),
  seek: (position: number) => request<void>('POST', '/player/seek', { position }),
  jump: (uid: number) => request<void>('POST', '/player/jump', { uid }),
  setMode: (mode: { shuffle?: boolean; repeat?: RepeatMode }) => request<void>('PUT', '/player/mode', mode),
  setVolume: (level: number) => request<void>('PUT', '/player/volume', { level }),

  playAlbum: (albumId: string, startIndex = 0) =>
    request<void>('POST', '/queue', { album_id: albumId, mode: 'now', start_index: startIndex }),
  /** Add to "next in queue": plays after the current track, before the rest of the album. */
  queueAlbum: (albumId: string) =>
    request<void>('POST', '/queue', { album_id: albumId, mode: 'queue', replace: false }),
  playArtist: (artistId: string) => request<void>('POST', '/queue', { artist_id: artistId, mode: 'now' }),
  queueArtist: (artistId: string) =>
    request<void>('POST', '/queue', { artist_id: artistId, mode: 'queue', replace: false }),
  /** Replace the queue with these songs, starting at startIndex. */
  playSongs: (songIds: string[], startIndex = 0, contextName?: string) =>
    request<void>('POST', '/queue', { song_ids: songIds, mode: 'now', start_index: startIndex, context_name: contextName }),
  /** Endless radio: the track, then similar tracks, refilled as it plays. */
  startRadio: (songId: string) => request<{ source: string }>('POST', '/radio', { song_id: songId }),
  /** Artist radio: the artist and similar artists, shuffled, refilled from the artist. */
  startArtistRadio: (artistId: string) => request<{ source: string }>('POST', '/radio', { artist_id: artistId }),
  home: () =>
    request<HomeData>('GET', '/home').then((h) => {
      rememberAlbums([...h.recently_played, ...h.recently_added]);
      rememberArtists(h.favorite_artists);
      return h;
    }),
  /** Every track, paged; 'recent' = most recently added first. `artistId`: that artist's only. */
  songs: (sort: SongSort = 'recent', offset = 0, size = 100, starred = false, artistId?: string) =>
    get<SongPage>(paths.songs(sort, offset, size, starred, artistId)),
  /** Insert songs without replacing the queue. */
  queueSongs: (songIds: string[], mode: AddMode) =>
    request<void>('POST', '/queue', { song_ids: songIds, mode, replace: false }),
  /** Tracks dropped on the queue: at `offset` in "next in queue" or in the album/playlist's upcoming tracks. */
  dropSongs: (songIds: string[], section: 'queued' | 'context', offset: number) =>
    request<void>('POST', '/queue', { song_ids: songIds, mode: 'queue', replace: false, section, offset }),
  removeItem: (uid: number) => request<void>('DELETE', `/queue/items/${uid}`),
  moveItem: (uid: number, toIndex: number, queued?: boolean) =>
    request<void>('POST', '/queue/move', { uid, to_index: toIndex, queued }),
  /** Empty "next in queue" only. */
  clearQueued: () => request<void>('DELETE', '/queue?queued_only=true'),
  clearQueue: () => request<void>('DELETE', '/queue'),
};
