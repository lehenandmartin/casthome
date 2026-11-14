import { beforeEach, describe, expect, it, vi } from 'vitest';
import { albumSummary, expire, isFresh, peek, remember, rememberAlbums, store } from './cache';
import type { Album } from './types';

const album = (id: string): Album => ({
  id,
  name: `Album ${id}`,
  artist: 'Artist',
  artist_id: 'ar1',
  cover_art: `al-${id}`,
  year: 2024,
  song_count: 10,
  duration: 2400,
  starred: false,
  user_rating: 0,
  songs: [],
});

describe('remember', () => {
  beforeEach(() => vi.useRealTimers());

  it('asks the server once for requests in flight at the same time', async () => {
    const fetcher = vi.fn(async () => 'value');
    const [a, b] = await Promise.all([remember('/same', fetcher), remember('/same', fetcher)]);
    expect(a).toBe('value');
    expect(b).toBe('value');
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('reuses a fresh response and asks again once it is old', async () => {
    vi.useFakeTimers();
    const fetcher = vi.fn(async () => Date.now());
    await remember('/fresh', fetcher, 1000);
    await remember('/fresh', fetcher, 1000);
    expect(fetcher).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(1500);
    await remember('/fresh', fetcher, 1000);
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it('does not keep a failed request', async () => {
    const failing = vi.fn(async () => {
      throw new Error('down');
    });
    await expect(remember('/fails', failing)).rejects.toThrow('down');
    expect(peek('/fails')).toBeUndefined();
    const ok = vi.fn(async () => 'back');
    expect(await remember('/fails', ok)).toBe('back');
  });
});

describe('expire', () => {
  it('keeps showing the old response but asks the server next time', async () => {
    store('/library/albums/1', 'old');
    expect(isFresh('/library/albums/1', 60_000)).toBe(true);
    expire('/library');
    expect(peek('/library/albums/1')).toBe('old');
    expect(isFresh('/library/albums/1', 60_000)).toBe(false);
    const fetcher = vi.fn(async () => 'new');
    expect(await remember('/library/albums/1', fetcher)).toBe('new');
  });

  it('only touches keys with the prefix', () => {
    store('/playlists', 'kept');
    expire('/library');
    expect(isFresh('/playlists', 60_000)).toBe(true);
  });
});

describe('summaries', () => {
  it('remembers albums from lists without their tracks', () => {
    rememberAlbums([album('a1')]);
    expect(albumSummary('a1')?.name).toBe('Album a1');
    expect(albumSummary('a1')?.songs).toBeUndefined();
  });
});
