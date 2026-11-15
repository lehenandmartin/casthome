<script lang="ts">
  import { api } from '../lib/api';
  import { nearEnd } from '../lib/nearEnd';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Song, SongSort } from '../lib/types';
  import FavoritesToggle from './FavoritesToggle.svelte';
  import SkeletonList from './SkeletonList.svelte';
  import SongList from './SongList.svelte';

  // `artist` (an id, with its `artistName`): only that artist's tracks, e.g.
  // "Favorite tracks" from an artist page.
  let {
    fav = false,
    artist = null,
    artistName = '',
  }: { fav?: boolean; artist?: string | null; artistName?: string } = $props();

  const PAGE = 100;
  const SORTS: SongSort[] = ['recent', 'title', 'artist', 'album', 'frequent', 'played'];
  const SORT_KEY = 'casthome.tracks.sort';

  function savedSort(): SongSort {
    try {
      const value = localStorage.getItem(SORT_KEY) as SongSort | null;
      return value && SORTS.includes(value) ? value : 'recent';
    } catch {
      return 'recent';
    }
  }

  let sort = $state<SongSort>(savedSort());
  let songs = $state<Song[]>([]);
  let total = $state<number | null>(null);
  let loading = $state(false);
  // Pages coming from the network (not from memory) arrive in a light cascade.
  let arrive = $state(false);

  const keyOf = () => `${sort}|${fav}|${artist ?? ''}`;

  async function load(reset: boolean) {
    loading = true;
    arrive = true;
    const requested = sort;
    const requestedFav = fav;
    const requestedArtist = artist;
    const key = keyOf();
    const offset = reset ? 0 : songs.length;
    await store.run(async () => {
      const page = await api.songs(requested, offset, PAGE, fav, artist ?? undefined);
      if (requested !== sort || requestedFav !== fav || requestedArtist !== artist) return; // changed meanwhile
      songs = reset ? page.items : [...songs, ...page.items];
      total = page.total;
      lists.set(key, { songs, total, at: Date.now() });
    });
    loading = false;
  }

  // Coming back to a list: its pages show at once (so Back lands where it was),
  // and the first page is checked in the background.
  async function refreshFirst(key: string) {
    try {
      const page = await api.songs(sort, 0, PAGE, fav, artist ?? undefined);
      if (keyOf() !== key) return;
      const same = page.total === total && page.items.every((s, i) => songs[i]?.id === s.id);
      if (!same) {
        songs = page.items;
        total = page.total;
        lists.set(key, { songs, total, at: Date.now() });
      }
    } catch {
      /* keep what is shown */
    }
  }

  function choose(next: SongSort) {
    if (next === sort) return;
    sort = next;
    try {
      localStorage.setItem(SORT_KEY, next);
    } catch {
      /* ignore */
    }
  }

  $effect(() => {
    void sort;
    void fav;
    void artist;
    const key = keyOf();
    const saved = lists.get(key);
    if (saved && Date.now() - saved.at < KEEP_MS) {
      songs = saved.songs;
      total = saved.total;
      arrive = false;
      refreshFirst(key);
      return;
    }
    songs = [];
    total = null;
    load(true);
  });

  const more = $derived(total !== null && songs.length < total);

  // Tapping a track plays the loaded list from there (as an unnamed "Next up").
  function play(index: number) {
    const ids = songs.map((s) => s.id);
    store.run(() => api.playSongs(ids, index, title));
  }

  const title = $derived(
    artist
      ? t(fav ? 'artist.likedTitle' : 'artist.tracksTitle', { name: artistName })
      : fav
        ? t('favorites.tracksContext')
        : t('tracks.title'),
  );
</script>

<script lang="ts" module>
  import type { Song as Remembered } from '../lib/types';
  // Lists already browsed during this visit, with every page loaded so far.
  const KEEP_MS = 10 * 60_000;
  const lists = new Map<string, { songs: Remembered[]; total: number | null; at: number }>();
</script>

<section class:arrive>
  <h2>{title}</h2>
  {#if total !== null}<p class="muted count">{total === 1 ? t('tracks.one') : t('tracks.count', { count: total })}</p>{/if}
  <div class="tabs" role="tablist">
    {#if store.capabilities.all_tracks}<FavoritesToggle active={fav} />{/if}
    {#each SORTS as kind (kind)}
      <button role="tab" aria-selected={sort === kind} class:active={sort === kind} onclick={() => choose(kind)}>
        {t(`tracks.sort.${kind}`)}
      </button>
    {/each}
  </div>

  {#if !loading && total === 0}
    <p class="muted">{fav ? t('favorites.noTracks') : t('tracks.empty')}</p>
  {/if}

  {#if loading && songs.length === 0}
    <SkeletonList count={12} />
  {/if}
  <SongList {songs} onplay={play} />

  {#if more}
    <button class="more" use:nearEnd={() => !loading && load(false)} onclick={() => load(false)} disabled={loading}>
      {loading ? t('player.loading') : t('albums.loadMore')}
    </button>
  {/if}
</section>

<style>
  h2 {
    margin-bottom: 2px;
  }
  .count {
    margin: 0 0 10px;
  }
  .tabs {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    scrollbar-width: none;
    padding-bottom: 12px;
    margin-right: -16px;
    padding-right: 16px;
  }
  .tabs::-webkit-scrollbar {
    display: none;
  }
  .tabs button {
    flex: none;
    font-size: 0.9rem;
  }
  .tabs .active {
    background: var(--accent);
    color: var(--on-accent);
  }
  .more {
    display: block;
    margin: 16px auto 0;
  }
</style>
