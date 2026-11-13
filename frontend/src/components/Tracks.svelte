<script lang="ts">
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Song, SongSort } from '../lib/types';
  import SongList from './SongList.svelte';

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

  async function load(reset: boolean) {
    loading = true;
    const requested = sort;
    const offset = reset ? 0 : songs.length;
    await store.run(async () => {
      const page = await api.songs(requested, offset, PAGE);
      if (requested !== sort) return; // sort changed meanwhile
      songs = reset ? page.items : [...songs, ...page.items];
      total = page.total;
    });
    loading = false;
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
    songs = [];
    total = null;
    load(true);
  });

  const more = $derived(total !== null && songs.length < total);

  // Tapping a track plays the loaded list from there (as an unnamed "Next up").
  function play(index: number) {
    const ids = songs.map((s) => s.id);
    store.run(() => api.playSongs(ids, index, t('tracks.title')));
  }
</script>

<section>
  <h2>{t('tracks.title')}</h2>
  {#if total !== null}<p class="muted count">{t('tracks.count', { count: total })}</p>{/if}
  <div class="tabs" role="tablist">
    {#each SORTS as kind (kind)}
      <button role="tab" aria-selected={sort === kind} class:active={sort === kind} onclick={() => choose(kind)}>
        {t(`tracks.sort.${kind}`)}
      </button>
    {/each}
  </div>

  {#if !loading && total === 0}
    <p class="muted">{t('tracks.empty')}</p>
  {/if}

  <SongList {songs} onplay={play} />

  {#if more}
    <button class="more" onclick={() => load(false)} disabled={loading}>
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
