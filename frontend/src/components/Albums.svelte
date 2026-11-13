<script lang="ts">
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Album, AlbumListType } from '../lib/types';
  import AlbumGrid from './AlbumGrid.svelte';

  const PAGE = 40;
  const TYPES = ['newest', 'recent', 'frequent', 'random', 'alphabeticalByName'] as const;
  type ListType = (typeof TYPES)[number];

  let { type = 'newest', genre }: { type?: AlbumListType; genre?: string } = $props();
  let selected = $state<ListType>('newest');
  let albums = $state<Album[]>([]);
  let loading = $state(false);
  let done = $state(false);

  const listType = $derived<AlbumListType>(genre ? 'byGenre' : selected);

  async function load(reset: boolean) {
    loading = true;
    const offset = reset ? 0 : albums.length;
    const requested = listType;
    await store.run(async () => {
      const page = await api.albums(requested, PAGE, offset, genre);
      if (requested !== listType) return; // the user switched tabs meanwhile
      albums = reset ? page : [...albums, ...page];
      done = page.length < PAGE || requested === 'random';
    });
    loading = false;
  }

  $effect(() => {
    if (TYPES.includes(type as ListType)) selected = type as ListType;
  });

  $effect(() => {
    void listType;
    void genre;
    albums = [];
    done = false;
    load(true);
  });
</script>

<section>
  {#if !genre}
    <h2>{t('albums.title')}</h2>
    <div class="tabs" role="tablist">
      {#each TYPES as kind (kind)}
        <button role="tab" aria-selected={selected === kind} class:active={selected === kind} onclick={() => (selected = kind)}>
          {t(`albums.${kind}`)}
        </button>
      {/each}
      {#if selected === 'random'}
        <button onclick={() => load(true)}>⟳ {t('albums.reshuffle')}</button>
      {/if}
    </div>
  {/if}
  {#if !loading && albums.length === 0}
    <p class="muted">{t('albums.empty')}</p>
  {/if}
  <AlbumGrid {albums} />
  {#if !done && albums.length > 0}
    <button onclick={() => load(false)} disabled={loading}>{t('albums.loadMore')}</button>
  {/if}
</section>

<style>
  .tabs {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 12px;
    margin-bottom: 4px;
  }
  .tabs button {
    flex: none;
    border-radius: 999px;
  }
  .tabs .active {
    background: var(--accent);
    color: var(--on-accent);
    border-color: transparent;
  }
</style>
