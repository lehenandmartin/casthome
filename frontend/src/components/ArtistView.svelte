<script lang="ts">
  import { api, coverUrl } from '../lib/api';
  import { t } from '../lib/i18n';
  import { preloadImages } from '../lib/preload';
  import { startArtistRadio } from '../lib/radio';
  import { store } from '../lib/store.svelte';
  import type { Artist, ArtistDetail, ArtistHighlights } from '../lib/types';
  import AlbumGrid from './AlbumGrid.svelte';
  import ArtistGrid from './ArtistGrid.svelte';
  import Icon from './Icon.svelte';
  import SkeletonGrid from './SkeletonGrid.svelte';
  import SkeletonList from './SkeletonList.svelte';
  import SongList from './SongList.svelte';
  import StarButton from './StarButton.svelte';

  let { id }: { id: string } = $props();
  let artist = $state<ArtistDetail | null>(null);
  let highlights = $state<ArtistHighlights | null>(null);
  // null while loading (a placeholder is shown).
  let similar = $state<Artist[] | null>(null);
  let expanded = $state(false);

  const FOLDED = 5;

  $effect(() => {
    artist = null;
    highlights = null;
    similar = null;
    expanded = false;
    const artistId = id;
    store.run(async () => {
      artist = await api.artist(artistId);
    });
    // Separate request: popular tracks come from Last.fm and may be slower.
    api
      .artistHighlights(artistId)
      .then((h) => {
        if (artistId === id) highlights = h;
      })
      .catch(() => {});
    // Similar artists: shown all at once, when their pictures are loaded.
    api
      .similarArtists(artistId)
      .then(async (list) => {
        await preloadImages(list.map((a) => coverUrl(a.cover_art)));
        if (artistId === id) similar = list;
      })
      .catch(() => {
        if (artistId === id) similar = [];
      });
  });

  const top = $derived(highlights?.top ?? []);
  const shownTop = $derived(expanded ? top : top.slice(0, FOLDED));
  const likedHref = $derived(
    artist ? `#/tracks?fav=1&artist=${encodeURIComponent(artist.id)}&name=${encodeURIComponent(artist.name)}` : '#/',
  );

  async function playAll() {
    if (!artist) return;
    const artistId = artist.id;
    await store.run(() => api.playArtist(artistId));
  }

  async function queue() {
    if (!artist) return;
    const artistId = artist.id;
    await store.run(async () => {
      await api.queueArtist(artistId);
      store.notify('added_to_queue', {}, 'info');
    });
  }

  // Tapping a popular track plays the whole top list from there.
  function playTop(index: number) {
    if (!artist) return;
    const ids = top.map((s) => s.id);
    const name = t('artist.popularContext', { name: artist.name });
    store.run(() => api.playSongs(ids, index, name));
  }
</script>

{#if artist}
  <section>
    <h2>{artist.name} <StarButton kind="artist" id={artist.id} bind:starred={artist.starred} /></h2>
    <p class="muted">{t('album.count', { count: artist.albums.length })}</p>
    <div class="actions">
      <button class="primary" onclick={playAll}>{t('artist.playAll')}</button>
      <button onclick={queue}>{t('album.addToQueue')}</button>
      <button class="radio" onclick={() => artist && startArtistRadio(artist)}>
        <Icon name="radio" size={18} />{t('song.startRadio')}
      </button>
    </div>

    {#if highlights && highlights.liked_count > 0}
      <a class="liked" href={likedHref}>
        <span class="liked-icon"><Icon name="starFilled" size={22} /></span>
        <span class="text">
          <strong>{t('artist.liked')}</strong>
          <span class="muted">
            {highlights.liked_count === 1
              ? t('artist.likedOne', { name: artist.name })
              : t('artist.likedCount', { count: highlights.liked_count, name: artist.name })}
          </span>
        </span>
        <span class="chevron muted" aria-hidden="true">›</span>
      </a>
    {/if}

    {#if !highlights}
      <span class="skeleton text heading" aria-hidden="true"></span>
      <SkeletonList count={5} />
    {:else if top.length > 0}
      <h3>{highlights.top_source === 'popular' ? t('artist.popular') : t('artist.mostPlayed')}</h3>
      {#if highlights.top_source === 'popular'}<p class="muted hint">{t('artist.popularHint')}</p>{/if}
      <SongList songs={shownTop} onplay={playTop} ranked />
      {#if top.length > FOLDED}
        <button class="link" onclick={() => (expanded = !expanded)}>
          {expanded ? t('artist.showLess') : t('artist.showMore')}
        </button>
      {/if}
    {/if}

    <h3>{t('artist.albums')}</h3>
    <AlbumGrid albums={artist.albums} showArtist={false} />

    {#if similar === null}
      <h3>{t('artist.similar')}</h3>
      <SkeletonGrid round rows={1} />
    {:else if similar.length > 0}
      <h3>{t('artist.similar')}</h3>
      <ArtistGrid artists={similar} rowsOnly />
    {/if}
  </section>
{:else}
  <section aria-busy="true">
    <span class="skeleton text page-title"></span>
    <span class="skeleton text page-sub"></span>
    <div class="actions" aria-hidden="true">
      <span class="skeleton pill"></span><span class="skeleton pill"></span><span class="skeleton pill"></span>
    </div>
    <span class="skeleton text heading" aria-hidden="true"></span>
    <SkeletonList count={5} />
    <span class="skeleton text heading" aria-hidden="true"></span>
    <SkeletonGrid count={6} />
  </section>
{/if}

<style>
  /* Placeholders while the page loads. */
  .page-title {
    width: 40%;
    height: 1.9rem;
    margin: 6px 0 12px;
  }
  .page-sub {
    width: 18%;
  }
  .pill {
    width: 110px;
    height: 38px;
    border-radius: 999px;
  }
  .skeleton.heading {
    width: 140px;
    height: 1.15rem;
    margin: 24px 0 12px;
  }
  h2 {
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  h3 {
    margin: 24px 0 8px;
    font-size: 1.15rem;
  }
  .hint {
    margin: -4px 0 8px;
    font-size: 0.8rem;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 12px 0 20px;
  }
  .radio {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .liked {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border-radius: 10px;
    background: var(--surface);
    border: 1px solid var(--border);
    color: inherit;
    text-decoration: none;
  }
  .liked:hover {
    background: var(--surface-2);
  }
  .liked-icon {
    display: grid;
    place-items: center;
    width: 48px;
    height: 48px;
    border-radius: 8px;
    background: var(--accent);
    color: var(--on-accent);
    flex: none;
  }
  .liked .text {
    flex: 1;
    display: grid;
    min-width: 0;
  }
  .chevron {
    font-size: 1.5rem;
    line-height: 1;
  }
  .link {
    background: none;
    padding: 6px 0;
    min-height: 0;
    color: var(--muted);
    font-weight: 600;
    font-size: 0.9rem;
  }
  .link:hover {
    color: var(--text);
  }
</style>
