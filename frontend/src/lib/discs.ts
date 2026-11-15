// Albums on several discs: their tracks in parts, one per disc, so each part
// can have its own heading ("Disc 1", "Disc 2", or the disc's own name when it
// is tagged, e.g. "The Fame Monster" / "The Fame"); the track numbers restart
// on every disc, which reads as a jumble without them.

export interface DiscPart<T> {
  /** The disc number, or null when the album is on one disc (no heading). */
  disc: number | null;
  /** The disc's name when it is tagged, else null ("Disc 2"). */
  title: string | null;
  /** Position of the part's first track in the whole album (to play from there). */
  start: number;
  songs: T[];
}

export function byDisc<T extends { disc: number | null }>(
  songs: T[],
  titles: Record<number, string> = {},
): DiscPart<T>[] {
  const discs = new Set(songs.map((s) => s.disc ?? 1));
  if (discs.size < 2) return [{ disc: null, title: null, start: 0, songs }];
  const parts: DiscPart<T>[] = [];
  songs.forEach((song, i) => {
    const disc = song.disc ?? 1;
    const last = parts.at(-1);
    if (last && last.disc === disc) last.songs.push(song);
    else parts.push({ disc, title: titles[disc]?.trim() || null, start: i, songs: [song] });
  });
  return parts;
}
