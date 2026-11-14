<script lang="ts">
  import { api, coverUrl } from '../lib/api';
  import { menu } from '../lib/contextMenu.svelte';
  import { dialogs } from '../lib/dialog.svelte';
  import { playlistMenu } from '../lib/menus';
  import { router } from '../lib/router.svelte';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Playlist } from '../lib/types';
  import Icon from './Icon.svelte';
  import SkeletonList from './SkeletonList.svelte';

  let playlists = $state<Playlist[]>([]);
  let loaded = $state(false);

  // Most recently changed first (sorted by the server).
  async function load() {
    await store.run(async () => {
      playlists = await api.playlists();
      loaded = true;
    });
  }

  async function create() {
    const name = (
      await dialogs.prompt({
        title: t('playlists.new'),
        placeholder: t('playlists.namePlaceholder'),
        confirmLabel: t('playlists.create'),
      })
    )?.trim();
    if (!name) return;
    await store.run(async () => {
      const playlist = await api.createPlaylist(name);
      router.navigate(`#/playlist/${encodeURIComponent(playlist.id)}`);
    });
  }

  load();
</script>

<section>
  <div class="head">
    <h2>{t('playlists.title')}</h2>
    <button class="primary new" onclick={create}><Icon name="plus" size={18} />{t('playlists.new')}</button>
  </div>
  {#if !loaded}
    <SkeletonList count={8} thumb />
  {/if}
  {#if loaded && playlists.length === 0}
    <p class="muted">{t('playlists.empty')}</p>
  {/if}
  <ul>
    {#each playlists as playlist (playlist.id)}
      <li>
        <a href={`#/playlist/${encodeURIComponent(playlist.id)}`} use:menu={() => playlistMenu(playlist, load)}>
          {#if playlist.cover_art}
            <img src={coverUrl(playlist.cover_art, 96)} alt="" loading="lazy" />
          {:else}
            <span class="thumb"></span>
          {/if}
          <span class="text">
            <span>{playlist.name}</span>
            <span class="muted">
              {t('playlists.tracks', { count: playlist.song_count })} · {formatTime(playlist.duration)}
            </span>
          </span>
        </a>
      </li>
    {/each}
  </ul>
</section>

<style>
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }
  .head h2 {
    margin: 0;
  }
  .new {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex: none;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  a {
    display: flex;
    gap: 12px;
    align-items: center;
    padding: 8px;
    border-radius: 6px;
    color: inherit;
    text-decoration: none;
  }
  a:hover {
    background: var(--surface-2);
  }
  img,
  .thumb {
    width: 48px;
    height: 48px;
    border-radius: 4px;
    object-fit: cover;
    background: var(--surface-2);
    flex: none;
  }
  .text {
    display: grid;
    min-width: 0;
  }
  .text > span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
