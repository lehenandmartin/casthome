<script lang="ts">
  import { api, coverUrl } from '../lib/api';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Album } from '../lib/types';
  import Icon from './Icon.svelte';
  import PlaylistPicker from './PlaylistPicker.svelte';
  import RatingStars from './RatingStars.svelte';
  import SongList from './SongList.svelte';
  import StarButton from './StarButton.svelte';

  let { id }: { id: string } = $props();
  let album = $state<Album | null>(null);
  let picking = $state(false);

  $effect(() => {
    album = null;
    const albumId = id;
    store.run(async () => {
      album = await api.album(albumId);
    });
  });

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
  <section>
    <header>
      <div class="cover">
        {#if album.cover_art}
          <img src={coverUrl(album.cover_art, 600)} alt="" />
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
    <SongList songs={album.songs ?? []} numbered showAlbum={false} onplay={(i) => store.run(() => api.playAlbum(album!.id, i))} />
  </section>
  {#if picking}
    <PlaylistPicker songIds={(album.songs ?? []).map((s) => s.id)} onclose={() => (picking = false)} />
  {/if}
{/if}

<style>
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
