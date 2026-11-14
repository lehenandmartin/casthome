// Memory of library responses for the visit, so pages already seen (or
// prefetched) show at once and refresh in the background.
//
// - `remember(key, fetcher)`: one request per key at a time; a response younger
//   than `maxAge` is reused without asking the server again.
// - `peek(key)`: the last response, if any (whatever its age).
// - Album and artist summaries met in any list are kept too, so a detail page
//   can draw its header before its own request returns.
import type { Album, Artist } from './types';

const MAX_ENTRIES = 200;
const entries = new Map<string, { value: unknown; at: number }>();
const inflight = new Map<string, Promise<unknown>>();

export function peek<T>(key: string): T | undefined {
  return entries.get(key)?.value as T | undefined;
}

export function isFresh(key: string, maxAge: number): boolean {
  const entry = entries.get(key);
  return Boolean(entry && Date.now() - entry.at < maxAge);
}

export function store(key: string, value: unknown): void {
  entries.delete(key); // re-inserted last: the map keeps recency order
  entries.set(key, { value, at: Date.now() });
  while (entries.size > MAX_ENTRIES) entries.delete(entries.keys().next().value as string);
}

export function remember<T>(key: string, fetcher: () => Promise<T>, maxAge = 15_000): Promise<T> {
  if (isFresh(key, maxAge)) return Promise.resolve(peek<T>(key) as T);
  const pending = inflight.get(key);
  if (pending) return pending as Promise<T>;
  const request = fetcher()
    .then((value) => {
      store(key, value);
      return value;
    })
    .finally(() => inflight.delete(key));
  inflight.set(key, request);
  return request;
}

/** After a change: responses whose key starts with `prefix` are still shown
 *  at once, but the next request asks the server again. */
export function expire(prefix: string): void {
  for (const [key, entry] of entries) if (key.startsWith(prefix)) entry.at = 0;
}

// --- summaries -------------------------------------------------------------

const albums = new Map<string, Album>();
const artists = new Map<string, Artist>();

export function rememberAlbums(list: Album[] | null | undefined): void {
  for (const album of list ?? []) {
    if (albums.size > 2000) albums.delete(albums.keys().next().value as string);
    albums.set(album.id, { ...album, songs: undefined });
  }
}

export function rememberArtists(list: Artist[] | null | undefined): void {
  for (const artist of list ?? []) {
    if (artists.size > 2000) artists.delete(artists.keys().next().value as string);
    artists.set(artist.id, artist);
  }
}

export const albumSummary = (id: string): Album | undefined => albums.get(id);
export const artistSummary = (id: string): Artist | undefined => artists.get(id);
