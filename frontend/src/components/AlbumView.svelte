<script lang="ts">
  import { api, coverUrl } from '../lib/api';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Album } from '../lib/types';
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
</script>

{#if album}
  <section>
    <header>
      {#if album.cover_art}<img src={coverUrl(album.cover_art, 600)} alt="" />{/if}
      <div>
        <h2>{album.name} <StarButton kind="album" id={album.id} bind:starred={album.starred} /></h2>
        <p class="muted"><a href={`#/artist/${encodeURIComponent(album.artist_id ?? '')}`}>{album.artist}</a>{album.year ? ` · ${album.year}` : ''}</p>
        <p class="muted">{t('album.tracks', { count: album.song_count })} · {formatTime(album.duration)}</p>
        <RatingStars id={album.id} bind:rating={album.user_rating} />
        <div class="actions">
          <button class="primary" onclick={() => store.run(() => api.playAlbum(album!.id))}>{t('album.play')}</button>
          <button onclick={() => store.run(() => api.queueAlbum(album!.id, 'next'))}>{t('album.playNext')}</button>
          <button onclick={() => store.run(() => api.queueAlbum(album!.id, 'end'))}>{t('album.addToQueue')}</button>
          <button onclick={() => (picking = true)}>{t('song.addToPlaylist')}</button>
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
  }
  @media (min-width: 640px) {
    header {
      grid-template-columns: 220px 1fr;
      align-items: end;
    }
  }
  img {
    width: 100%;
    max-width: 320px;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: 8px;
  }
  h2 {
    margin: 0 0 4px;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  p {
    margin: 0 0 4px;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
  }
  a {
    color: inherit;
  }
</style>
