// Play/pause, shared by every player bar (mini, full, Now Playing) and the
// space bar, so they all agree. It answers at once (optimistic); the server's
// state takes over when it arrives, or after 3 s.

import { api } from './api';
import { store } from './store.svelte';

export const optimistic = $state<{ value: boolean | null; timer?: ReturnType<typeof setTimeout> }>({ value: null });

/** What the server says: playing, or about to. */
export function actuallyPlaying(): boolean {
  const status = store.player?.status;
  return status === 'playing' || status === 'buffering' || status === 'loading';
}

/** Play if the player shows paused, pause if it shows playing. The action is
 * explicit (not "toggle"): two quick presses give pause then play, even if the
 * server has not confirmed the first one yet. */
export function togglePlayback(): void {
  const play = !(optimistic.value ?? actuallyPlaying());
  optimistic.value = play;
  clearTimeout(optimistic.timer);
  optimistic.timer = setTimeout(() => (optimistic.value = null), 3000);
  store.run(async () => {
    try {
      await api.action(play ? 'play' : 'pause');
    } catch (error) {
      optimistic.value = null;
      throw error;
    }
  });
}
