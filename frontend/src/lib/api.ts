import type { Album, RepeatMode } from './types';

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

  albums: (type = 'newest', size = 40, offset = 0) =>
    request<Album[]>('GET', `/library/albums?type=${type}&size=${size}&offset=${offset}`),
  album: (id: string) => request<Album>('GET', `/library/albums/${encodeURIComponent(id)}`),

  selectDevice: (uuid: string) => request<void>('PUT', '/player/device', { uuid }),
  action: (name: 'play' | 'pause' | 'toggle' | 'next' | 'previous' | 'stop') =>
    request<void>('POST', `/player/${name}`),
  seek: (position: number) => request<void>('POST', '/player/seek', { position }),
  jump: (index: number) => request<void>('POST', '/player/jump', { index }),
  setMode: (mode: { shuffle?: boolean; repeat?: RepeatMode }) => request<void>('PUT', '/player/mode', mode),
  setVolume: (level: number) => request<void>('PUT', '/player/volume', { level }),

  playAlbum: (albumId: string, startIndex = 0) =>
    request<void>('POST', '/queue', { album_id: albumId, mode: 'now', start_index: startIndex }),
  queueAlbum: (albumId: string, mode: 'next' | 'end') =>
    request<void>('POST', '/queue', { album_id: albumId, mode, replace: false }),
  clearQueue: () => request<void>('DELETE', '/queue'),
};
