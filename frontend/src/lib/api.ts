import type { AddMode, Album, AlbumListType, ArtistDetail, Artist, Genre, RepeatMode, SearchResult, Song } from './types';

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

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    credentials: 'same-origin',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login') onUnauthorized();
    throw new ApiError(response.status, data.code ?? 'unknown', data.params ?? {});
  }
  return data as T;
}

export const coverUrl = (id: string | null, size = 300): string | null =>
  id ? `/api/cover/${encodeURIComponent(id)}?size=${size}` : null;

export const api = {
  login: (password: string, remember: boolean) =>
    request<{ username: string }>('POST', '/auth/login', { password, remember }),
  logout: () => request<void>('POST', '/auth/logout'),
  me: () => request<{ username: string }>('GET', '/auth/me'),

  albums: (type: AlbumListType = 'newest', size = 40, offset = 0, genre?: string) =>
    request<Album[]>(
      'GET',
      `/library/albums?type=${type}&size=${size}&offset=${offset}` +
        (genre ? `&genre=${encodeURIComponent(genre)}` : ''),
    ),
  artists: () => request<Artist[]>('GET', '/library/artists'),
  artist: (id: string) => request<ArtistDetail>('GET', `/library/artists/${encodeURIComponent(id)}`),
  genres: () => request<Genre[]>('GET', '/library/genres'),
  genreSongs: (genre: string, count = 200) =>
    request<Song[]>('GET', `/library/genres/${encodeURIComponent(genre)}/songs?count=${count}`),
  search: (q: string, limit = 20) =>
    request<SearchResult>('GET', `/library/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  album: (id: string) => request<Album>('GET', `/library/albums/${encodeURIComponent(id)}`),

  selectDevice: (uuid: string) => request<void>('PUT', '/player/device', { uuid }),
  action: (name: 'play' | 'pause' | 'toggle' | 'next' | 'previous' | 'stop') =>
    request<void>('POST', `/player/${name}`),
  seek: (position: number) => request<void>('POST', '/player/seek', { position }),
  jump: (uid: number) => request<void>('POST', '/player/jump', { uid }),
  setMode: (mode: { shuffle?: boolean; repeat?: RepeatMode }) => request<void>('PUT', '/player/mode', mode),
  setVolume: (level: number) => request<void>('PUT', '/player/volume', { level }),

  playAlbum: (albumId: string, startIndex = 0) =>
    request<void>('POST', '/queue', { album_id: albumId, mode: 'now', start_index: startIndex }),
  queueAlbum: (albumId: string, mode: 'next' | 'end') =>
    request<void>('POST', '/queue', { album_id: albumId, mode, replace: false }),
  queueArtist: (artistId: string, mode: AddMode) =>
    request<void>('POST', '/queue', { artist_id: artistId, mode, replace: mode === 'now' }),
  /** Replace the queue with these songs, starting at startIndex. */
  playSongs: (songIds: string[], startIndex = 0) =>
    request<void>('POST', '/queue', { song_ids: songIds, mode: 'now', start_index: startIndex }),
  /** Insert songs without replacing the queue. */
  queueSongs: (songIds: string[], mode: AddMode) =>
    request<void>('POST', '/queue', { song_ids: songIds, mode, replace: false }),
  removeItem: (uid: number) => request<void>('DELETE', `/queue/items/${uid}`),
  moveItem: (uid: number, toIndex: number) => request<void>('POST', '/queue/move', { uid, to_index: toIndex }),
  clearQueue: () => request<void>('DELETE', '/queue'),
};
