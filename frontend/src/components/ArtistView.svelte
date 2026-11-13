<script lang="ts">
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { ArtistDetail } from '../lib/types';
  import AlbumGrid from './AlbumGrid.svelte';
  import StarButton from './StarButton.svelte';

  let { id }: { id: string } = $props();
  let artist = $state<ArtistDetail | null>(null);

  $effect(() => {
    artist = null;
    const artistId = id;
    store.run(async () => {
      artist = await api.artist(artistId);
    });
  });

  async function queue(mode: 'now' | 'next' | 'end') {
    if (!artist) return;
    const artistId = artist.id;
    await store.run(async () => {
      await api.queueArtist(artistId, mode);
      if (mode !== 'now') store.notify('added_to_queue', {}, 'info');
    });
  }
</script>

{#if artist}
  <section>
    <h2>{artist.name} <StarButton kind="artist" id={artist.id} bind:starred={artist.starred} /></h2>
    <p class="muted">{t('album.count', { count: artist.albums.length })}</p>
    <div class="actions">
      <button class="primary" onclick={() => queue('now')}>{t('artist.playAll')}</button>
      <button onclick={() => queue('next')}>{t('album.playNext')}</button>
      <button onclick={() => queue('end')}>{t('album.addToQueue')}</button>
    </div>
    <AlbumGrid albums={artist.albums} showArtist={false} />
  </section>
{/if}

<style>
  h2 {
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 12px 0 20px;
  }
</style>
