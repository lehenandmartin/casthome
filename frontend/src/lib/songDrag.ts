// Desktop: a track dragged from a list (album, playlist, search...) and dropped
// on the open queue panel, at a place in it. Native drag and drop: the queue's
// own reordering (svelte-dnd-action) works with pointer events and is not
// affected.

import type { Song } from './types';

const TYPE = 'application/x-casthome-songs';

/** Start dragging `song` from a list row. */
export function startSongDrag(event: DragEvent, song: Song): void {
  const data = event.dataTransfer;
  if (!data) return;
  data.effectAllowed = 'copy';
  data.setData(TYPE, JSON.stringify([song.id]));
  // Firefox only starts a drag with some data; also what lands in a text field.
  data.setData('text/plain', `${song.title} — ${song.artist}`);
}

/** Is a track being dragged over us? (Its data can only be read on drop.) */
export function carriesSongs(event: DragEvent): boolean {
  return event.dataTransfer?.types.includes(TYPE) ?? false;
}

/** The ids of the dropped tracks, or null for anything else. */
export function droppedSongs(event: DragEvent): string[] | null {
  try {
    const ids: unknown = JSON.parse(event.dataTransfer?.getData(TYPE) || 'null');
    return Array.isArray(ids) && ids.every((id) => typeof id === 'string') && ids.length > 0 ? ids : null;
  } catch {
    return null;
  }
}
