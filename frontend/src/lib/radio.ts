import { api } from './api';
import { store } from './store.svelte';
import type { Artist, Song } from './types';

/** Start an endless radio from a track (similar tracks, refilled as it plays). */
export function startRadio(song: Pick<Song, 'id' | 'title'>): Promise<void> {
  return store.run(async () => {
    await api.startRadio(song.id);
    store.notify('radio_started', { title: song.title }, 'info');
  });
}

/** Start an endless artist radio: the artist and similar artists, shuffled. */
export function startArtistRadio(artist: Pick<Artist, 'id' | 'name'>): Promise<void> {
  return store.run(async () => {
    await api.startArtistRadio(artist.id);
    store.notify('radio_started', { title: artist.name }, 'info');
  });
}
