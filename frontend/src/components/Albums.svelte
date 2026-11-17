<script lang="ts">
  import { api } from '../lib/api';
  import { nearEnd } from '../lib/nearEnd';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Album, AlbumListType } from '../lib/types';
  import AlbumGrid from './AlbumGrid.svelte';
  import SkeletonGrid from './SkeletonGrid.svelte';
  import FavoritesToggle from './FavoritesToggle.svelte';

  const PAGE = 40;
  const TYPES = ['newest', 'recent', 'frequent', 'random', 'alphabeticalByName'] as const;
  type ListType = (typeof TYPES)[number];

  let { type = 'newest', genre, fav = false }: { type?: AlbumListType; genre?: string; fav?: boolean } = $props();
  let selected = $state<ListType>('newest');
  let albums = $state<Album[]>([]);
  let loading = $state(false);
  let done = $state(false);
  // Pages coming from the network (not from memory) arrive in a light cascade.
  let arrive = $state(false);

  const listType = $derived<AlbumListType>(genre ? 'byGenre' : selected);

  const keyOf = () => `${listType}|${genre ?? ''}|${fav}`;

  async function load(reset: boolean) {
    loading = true;
    arrive = true;
    const offset = reset ? 0 : albums.length;
    const requested = listType;
    const key = keyOf();
    await store.run(async () => {
      const page = await api.albums(requested, PAGE, offset, genre, fav && !genre);
      if (requested !== listType) return; // the user switched tabs meanwhile
      albums = reset ? page : [...albums, ...page];
      done = page.length < PAGE || requested === 'random';
      lists.set(key, { albums, done, at: Date.now() });
    });
    loading = false;
  }

  // Coming back to a list: its pages show at once (so Back lands where it was),
  // and the first page is checked in the background.
  async function refreshFirst(key: string) {
    const requested = listType;
    try {
      const page = await api.albums(requested, PAGE, 0, genre, fav && !genre);
      if (requested !== listType || keyOf() !== key) return;
      const same = page.every((a, i) => albums[i]?.id === a.id);
      if (!same) {
        albums = page;
        done = page.length < PAGE;
        lists.set(key, { albums, done, at: Date.now() });
      }
    } catch {
      /* keep what is shown */
    }
  }

  $effect(() => {
    if (TYPES.includes(type as ListType)) selected = type as ListType;
  });

  $effect(() => {
    void listType;
    void genre;
    const key = keyOf();
    const saved = lists.get(key);
    if (saved && Date.now() - saved.at < KEEP_MS) {
      albums = saved.albums;
      done = saved.done;
      arrive = false;
      if (listType !== 'random') refreshFirst(key);
      return;
    }
    albums = [];
    done = false;
    load(true);
  });
</script>

<script lang="ts" module>
  import type { Album as Remembered } from '../lib/types';
  // Lists already browsed during this visit, with every page loaded so far.
  const KEEP_MS = 10 * 60_000;
  const lists = new Map<string, { albums: Remembered[]; done: boolean; at: number }>();
</script>

<section class:arrive>
  {#if !genre}
    <h2>{t('albums.title')}</h2>
    <div class="tabs" role="group" aria-label={t('list.show')}>
      <FavoritesToggle active={fav} />
      {#each TYPES as kind (kind)}
        <button aria-pressed={selected === kind} class:active={selected === kind} onclick={() => (selected = kind)}>
          {t(`albums.${kind}`)}
        </button>
      {/each}
      {#if selected === 'random'}
        <button onclick={() => load(true)}>⟳ {t('albums.reshuffle')}</button>
      {/if}
    </div>
  {/if}
  {#if !loading && albums.length === 0}
    <p class="muted">{fav ? t('favorites.noAlbums') : t('albums.empty')}</p>
  {/if}
  {#if loading && albums.length === 0}
    <SkeletonGrid count={12} />
  {/if}
  <AlbumGrid {albums} />
  {#if !done && albums.length > 0}
    <button use:nearEnd={() => !loading && load(false)} onclick={() => load(false)} disabled={loading}>{t('albums.loadMore')}</button>
  {/if}
</section>

<style>
  .tabs {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    scrollbar-width: none;
    margin-right: -16px;
    padding-right: 16px;
    padding-bottom: 12px;
    margin-bottom: 4px;
  }
  .tabs::-webkit-scrollbar {
    display: none;
  }
  .tabs button {
    flex: none;
    border-radius: 999px;
    font-size: var(--text-sm);
  }
  .tabs .active {
    background: var(--accent);
    color: var(--on-accent);
    border-color: transparent;
  }
</style>
