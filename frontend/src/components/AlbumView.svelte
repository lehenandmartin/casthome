<script lang="ts">
  import { api, cached, coverUrl } from '../lib/api';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { preloadImages } from '../lib/preload';
  import { store } from '../lib/store.svelte';
  import type { Album } from '../lib/types';
  import AlbumGrid from './AlbumGrid.svelte';
  import Icon from './Icon.svelte';
  import PlaylistPicker from './PlaylistPicker.svelte';
  import RatingStars from './RatingStars.svelte';
  import SkeletonGrid from './SkeletonGrid.svelte';
  import SkeletonList from './SkeletonList.svelte';
  import SongList from './SongList.svelte';
  import StarButton from './StarButton.svelte';

  let { id }: { id: string } = $props();
  let album = $state<Album | null>(null);
  let picking = $state(false);
  // The artist's other albums, shown under the tracks (null while loading).
  let more = $state<Album[] | null>(null);
  // Content coming from the network (not from memory) arrives in a light cascade.
  let arrive = $state(false);

  // Shown at once: the album as last loaded, else what the tapped card knew
  // (name, artist, cover; the tracks then show placeholders).
  $effect(() => {
    const albumId = id;
    // A local first: reading `album` back here would make this effect depend on it.
    const known = cached.album(albumId) ?? cached.albumSummary(albumId) ?? null;
    album = known;
    arrive = !known?.songs;
    const knownOthers = othersFrom(known?.artist_id ? cached.artist(known.artist_id) : undefined, albumId);
    const shownAtOnce = knownOthers !== null;
    more = knownOthers;
    store.run(async () => {
      const loaded = await api.album(albumId);
      if (albumId !== id) return;
      album = loaded;
      if (!loaded.artist_id) {
        more = [];
        return;
      }
      api
        .artist(loaded.artist_id)
        .then(async (artist) => {
          const others = othersFrom(artist, albumId) ?? [];
          // Shown all at once, when their pictures are loaded (unless already shown).
          if (!shownAtOnce) await preloadImages(others.slice(0, 12).map((a) => coverUrl(a.cover_art)));
          if (albumId === id) more = others;
        })
        .catch(() => {
          if (albumId === id && !shownAtOnce) more = [];
        });
    });
  });

  function othersFrom(artist: { albums: Album[] } | undefined, albumId: string): Album[] | null {
    return artist ? artist.albums.filter((a) => a.id !== albumId) : null;
  }

  async function queue() {
    if (!album) return;
    const albumId = album.id;
    await store.run(async () => {
      await api.queueAlbum(albumId);
      store.notify('added_to_queue', {}, 'info');
    });
  }
</script>

{#if album}
  <section class:arrive>
    <header>
      <div class="cover">
        {#if album.cover_art}
          <!-- The smaller cover the lists use is usually cached: it shows while the large one loads. -->
          <img
            src={coverUrl(album.cover_art, 600)}
            alt=""
            style:background={`center / cover url("${coverUrl(album.cover_art, 300)}")`}
          />
        {:else}
          <span class="placeholder"><Icon name="disc" size={64} /></span>
        {/if}
      </div>
      <div class="meta">
        <span class="eyebrow">{t('album.label')}</span>
        <h2>{album.name}</h2>
        <p class="artist">
          {#if album.artist_id}
            <a href={`#/artist/${encodeURIComponent(album.artist_id)}`}>{album.artist}</a>
          {:else}{album.artist}{/if}
        </p>
        <p class="muted">
          {[album.year, album.song_count === 1 ? t('album.oneTrack') : t('album.tracks', { count: album.song_count }), formatTime(album.duration)]
            .filter(Boolean)
            .join(' · ')}
        </p>
        <RatingStars id={album.id} bind:rating={album.user_rating} />
        <div class="actions">
          <button class="primary play" onclick={() => store.run(() => api.playAlbum(album!.id))}>
            <Icon name="play" size={18} />{t('album.play')}
          </button>
          <button class="icon-btn ring" title={t('album.addToQueue')} aria-label={t('album.addToQueue')} onclick={queue}>
            <Icon name="queue" size={20} />
          </button>
          <button class="icon-btn ring" title={t('song.addToPlaylist')} aria-label={t('song.addToPlaylist')} onclick={() => (picking = true)}>
            <Icon name="playlist" size={20} />
          </button>
          <span class="ring-star"><StarButton kind="album" id={album.id} bind:starred={album.starred} /></span>
        </div>
      </div>
    </header>
    {#if album.songs}
      <SongList songs={album.songs} numbered showAlbum={false} onplay={(i) => store.run(() => api.playAlbum(album!.id, i))} />
    {:else}
      <SkeletonList count={Math.min(album.song_count || 8, 12)} />
    {/if}

    {#if more === null}
      <h3 class="more-title">{t('album.moreBy', { artist: album.artist })}</h3>
      <SkeletonGrid rows={1} />
    {:else if more.length > 0}
      <h3 class="more-title">{t('album.moreBy', { artist: album.artist })}</h3>
      <AlbumGrid albums={more} showArtist={false} rowsOnly />
    {/if}
  </section>
  {#if picking}
    <PlaylistPicker songIds={(album.songs ?? []).map((s) => s.id)} onclose={() => (picking = false)} />
  {/if}
{:else}
  <section aria-busy="true">
    <header aria-hidden="true">
      <div class="cover"><span class="skeleton sk-cover"></span></div>
      <div class="meta sk-meta">
        <span class="skeleton text" style:width="60px"></span>
        <span class="skeleton text sk-title"></span>
        <span class="skeleton text" style:width="120px"></span>
        <span class="skeleton text" style:width="160px"></span>
        <div class="actions"><span class="skeleton sk-pill"></span></div>
      </div>
    </header>
    <SkeletonList count={8} />
  </section>
{/if}

<style>
  /* Placeholders while the album loads. */
  .sk-cover {
    width: 100%;
    height: 100%;
    border-radius: 12px;
  }
  .sk-meta {
    width: 100%;
    gap: 10px;
  }
  .sk-title {
    width: min(320px, 70%);
    height: 1.8rem;
  }
  .sk-pill {
    width: 120px;
    height: 42px;
    border-radius: 999px;
  }
  .more-title {
    margin: 28px 0 10px;
    font-size: 1.15rem;
  }
  header {
    display: grid;
    gap: 16px;
    margin-bottom: 16px;
    justify-items: center;
    text-align: center;
  }
  .cover {
    width: min(260px, 70vw);
    aspect-ratio: 1;
  }
  .cover img,
  .placeholder {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 12px;
    box-shadow: var(--shadow);
    background: var(--surface-2);
    color: var(--muted);
    display: grid;
    place-items: center;
  }
  .meta {
    display: grid;
    justify-items: center;
    gap: 4px;
    min-width: 0;
  }
  .eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
  }
  h2 {
    margin: 0;
  }
  p {
    margin: 0;
  }
  .artist {
    font-weight: 600;
  }
  .artist a {
    text-decoration: none;
  }
  .artist a:hover {
    text-decoration: underline;
  }
  .actions {
    margin-top: 10px;
    align-items: center;
    justify-content: center;
  }
  .play {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 10px 22px;
  }
  .ring {
    background: var(--surface-2);
  }
  @media (min-width: 720px) {
    header {
      grid-template-columns: 240px 1fr;
      align-items: end;
      justify-items: start;
      text-align: left;
      gap: 28px;
    }
    .cover {
      width: 240px;
    }
    .meta {
      justify-items: start;
    }
    .actions {
      justify-content: flex-start;
    }
  }
</style>
