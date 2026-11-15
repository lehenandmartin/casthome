import { describe, expect, it } from 'vitest';
import { byDisc } from './discs';

const song = (disc: number | null, track: number) => ({ disc, track });

describe('byDisc', () => {
  it('keeps a one-disc album in one part, without a heading', () => {
    const songs = [song(1, 1), song(1, 2)];
    expect(byDisc(songs)).toEqual([{ disc: null, title: null, start: 0, songs }]);
    expect(byDisc([song(null, 1), song(null, 2)])[0].disc).toBeNull();
  });

  it('splits by disc, with where each part starts in the album', () => {
    const parts = byDisc([song(1, 1), song(1, 2), song(2, 1), song(2, 2), song(2, 3)]);
    expect(parts.map((p) => [p.disc, p.start, p.songs.length])).toEqual([
      [1, 0, 2],
      [2, 2, 3],
    ]);
  });

  it('counts a track without a disc as disc 1', () => {
    expect(byDisc([song(null, 1), song(2, 1)]).map((p) => p.disc)).toEqual([1, 2]);
  });

  it('names the discs that are tagged, numbers the others', () => {
    const parts = byDisc([song(1, 1), song(2, 1), song(3, 1)], { 1: 'The Fame Monster', 2: '  ', 3: 'The Fame' });
    expect(parts.map((p) => [p.disc, p.title])).toEqual([[1, 'The Fame Monster'], [2, null], [3, 'The Fame']]);
  });
});
