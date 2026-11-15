// Desktop: where tracks dragged in from a list land in the open queue.
// The queue's upcoming tracks are two parts, each its own list:
//   queued:  "Next in queue" (added by hand, plays first)
//   context: "Next from: <album/playlist>"

export type Zone = 'queued' | 'context';

/** Before row `offset` of a part, or at its end (offset = its length). */
export interface DropTarget {
  zone: Zone;
  offset: number;
}

interface Box {
  top: number;
  height: number;
}

/** One part as shown: its own box and those of its rows, top to bottom. */
export interface ZoneLayout {
  zone: Zone;
  top: number;
  rows: Box[];
}

/** The drop target for a pointer at height `y`, given the parts on screen. */
export function dropTarget(lists: ZoneLayout[], y: number, queuedCount: number, contextCount: number): DropTarget {
  for (const list of lists) {
    const before = list.rows.findIndex((r) => y < r.top + r.height / 2);
    if (before < 0) continue;
    // Above the album's first track, over its heading: end of "Next in queue".
    if (list.zone === 'context' && before === 0 && y < list.top) {
      return { zone: 'queued', offset: queuedCount };
    }
    return { zone: list.zone, offset: before };
  }
  return contextCount > 0 ? { zone: 'context', offset: contextCount } : { zone: 'queued', offset: queuedCount };
}

/** The parts' layout read from the page: `ol[data-zone]` lists inside `root`. */
export function readLayout(root: HTMLElement | undefined): ZoneLayout[] {
  const lists = [...(root?.querySelectorAll<HTMLElement>('ol.list[data-zone]') ?? [])];
  return lists.map((list) => ({
    zone: list.dataset.zone as Zone,
    top: list.getBoundingClientRect().top,
    rows: [...list.children].map((row) => row.getBoundingClientRect()),
  }));
}
