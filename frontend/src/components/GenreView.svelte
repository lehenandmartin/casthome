<script lang="ts">
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import Albums from './Albums.svelte';

  let { name }: { name: string } = $props();

  async function playSongs() {
    const genre = name;
    await store.run(async () => {
      const songs = await api.genreSongs(genre);
      if (songs.length === 0) {
        store.notify('nothing_to_play');
        return;
      }
      await api.playSongs(songs.map((s) => s.id));
    });
  }
</script>

<section>
  <h2>{name}</h2>
  <div class="actions">
    <button class="primary" onclick={playSongs}>{t('genre.playSongs')}</button>
  </div>
  <Albums genre={name} />
</section>

<style>
  .actions {
    margin: 0 0 16px;
  }
</style>
