import { describe, expect, it } from 'vitest';
import { dropTarget, type ZoneLayout } from './queueDrop';

// Rows 50 px high. "Next in queue" from 100 (2 rows), album heading at 200-230,
// album tracks from 230 (3 rows).
const rows = (top: number, n: number) => Array.from({ length: n }, (_, i) => ({ top: top + i * 50, height: 50 }));
const both: ZoneLayout[] = [
  { zone: 'queued', top: 100, rows: rows(100, 2) },
  { zone: 'context', top: 230, rows: rows(230, 3) },
];

describe('dropTarget', () => {
  it('lands before the row under the pointer, by its middle', () => {
    expect(dropTarget(both, 110, 2, 3)).toEqual({ zone: 'queued', offset: 0 });
    expect(dropTarget(both, 130, 2, 3)).toEqual({ zone: 'queued', offset: 1 });
    expect(dropTarget(both, 260, 2, 3)).toEqual({ zone: 'context', offset: 1 });
  });

  it('over the album heading: end of "Next in queue"', () => {
    expect(dropTarget(both, 210, 2, 3)).toEqual({ zone: 'queued', offset: 2 });
  });

  it('below everything: end of the album', () => {
    expect(dropTarget(both, 900, 2, 3)).toEqual({ zone: 'context', offset: 3 });
  });

  it('no album: end of "Next in queue"', () => {
    expect(dropTarget([both[0]], 900, 2, 0)).toEqual({ zone: 'queued', offset: 2 });
    expect(dropTarget([], 50, 0, 0)).toEqual({ zone: 'queued', offset: 0 });
  });
});
