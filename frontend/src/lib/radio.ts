import { api } from './api';
import { store } from './store.svelte';
import type { Song } from './types';

/** Start an endless radio from a track (similar tracks, refilled as it plays). */
export function startRadio(song: Pick<Song, 'id' | 'title'>): Promise<void> {
  return store.run(async () => {
    await api.startRadio(song.id);
    store.notify('radio_started', { title: song.title }, 'info');
  });
}
