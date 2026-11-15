// The volume of the device playing, shared by the slider, the −/+ buttons and
// the keyboard (+/−): what they set shows at once everywhere, and goes to the
// server shortly after (a burst of presses sends one request).

import { api } from './api';
import { store } from './store.svelte';

/** One press of − or +. */
export const VOLUME_STEP = 0.05;

const pending = $state<{ level: number | null }>({ level: null });
let timer: ReturnType<typeof setTimeout> | undefined;

/** Can CastHome set the volume? Only on a Cast device: a browser (this one or
 * another) plays at its device's own volume, set with its buttons or system. */
export function volumeAvailable(): boolean {
  const p = store.player;
  return Boolean(p?.connected && p.device_uuid && !p.device_uuid.startsWith('browser:'));
}

/** The volume shown: the one being set, else the device's. */
export function currentVolume(): number {
  return pending.level ?? store.player?.volume ?? 0;
}

export function setVolumeSoon(level: number): void {
  pending.level = Math.max(0, Math.min(1, level));
  clearTimeout(timer);
  timer = setTimeout(async () => {
    const sent = pending.level;
    if (sent === null) return;
    try {
      await store.run(() => api.setVolume(sent));
    } finally {
      if (pending.level === sent) pending.level = null;
    }
  }, 120);
}

/** The next level up or down, on the 5 % grid: 1 % goes to 5 % up, 0 % down. */
export function nextVolume(level: number, direction: 1 | -1, step = VOLUME_STEP): number {
  const units = level / step;
  const next = direction > 0 ? Math.floor(units + 1e-6) + 1 : Math.ceil(units - 1e-6) - 1;
  return Math.max(0, Math.min(1, Math.round(next * step * 100) / 100));
}

export function stepVolume(direction: 1 | -1): void {
  if (volumeAvailable()) setVolumeSoon(nextVolume(currentVolume(), direction));
}
