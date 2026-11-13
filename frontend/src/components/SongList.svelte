<script lang="ts">
  import { api } from '../lib/api';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { AddMode, Song } from '../lib/types';

  let {
    songs,
    onplay,
    numbered = false,
    showAlbum = true,
  }: {
    songs: Song[];
    /** Clicking a row: usually "play this list from here". */
    onplay: (index: number) => void;
    numbered?: boolean;
    showAlbum?: boolean;
  } = $props();

  let menuFor = $state<number | null>(null);
  const currentId = $derived(store.player?.current?.id);

  async function add(song: Song, mode: AddMode) {
    menuFor = null;
    await store.run(async () => {
      await api.queueSongs([song.id], mode);
      if (mode !== 'now') store.notify('added_to_queue', {}, 'info');
    });
  }
</script>

<svelte:window onclick={() => (menuFor = null)} />

<ol class="songs">
  {#each songs as song, i (`${song.id}-${i}`)}
    <li class:current={song.id === currentId}>
      <button class="row" onclick={() => onplay(i)}>
        {#if numbered}<span class="num muted">{song.track ?? i + 1}</span>{/if}
        <span class="text">
          <span class="title">{song.title}</span>
          {#if showAlbum}<span class="muted">{song.artist} · {song.album}</span>{/if}
        </span>
        <span class="muted">{formatTime(song.duration)}</span>
      </button>
      <div class="menu-wrap">
        <button
          class="more"
          aria-label={t('song.more')}
          aria-expanded={menuFor === i}
          onclick={(e) => {
            e.stopPropagation();
            menuFor = menuFor === i ? null : i;
          }}>⋯</button
        >
        {#if menuFor === i}
          <div class="menu" role="menu">
            <button role="menuitem" onclick={() => add(song, 'now')}>{t('song.playNow')}</button>
            <button role="menuitem" onclick={() => add(song, 'next')}>{t('song.playNext')}</button>
            <button role="menuitem" onclick={() => add(song, 'end')}>{t('song.addToQueue')}</button>
          </div>
        {/if}
      </div>
    </li>
  {/each}
</ol>

<style>
  .songs {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  li {
    display: flex;
    align-items: center;
    border-radius: 6px;
  }
  li:hover {
    background: var(--surface-2);
  }
  .row {
    flex: 1;
    min-width: 0;
    display: flex;
    gap: 10px;
    align-items: center;
    text-align: left;
    background: none;
    border: 0;
    padding: 10px 8px;
  }
  .num {
    width: 2em;
    flex: none;
  }
  .text {
    flex: 1;
    min-width: 0;
    display: grid;
  }
  .text > span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .current .title {
    color: var(--accent);
    font-weight: 600;
  }
  .menu-wrap {
    position: relative;
  }
  .more {
    background: none;
    border: 0;
    width: 40px;
    height: 40px;
    font-size: 18px;
  }
  .menu {
    position: absolute;
    right: 0;
    top: 100%;
    z-index: 15;
    display: grid;
    min-width: 170px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    box-shadow: 0 8px 24px rgb(0 0 0 / 0.25);
    padding: 4px;
  }
  .menu button {
    background: none;
    border: 0;
    text-align: left;
    padding: 8px 10px;
  }
  .menu button:hover {
    background: var(--surface-2);
  }
</style>
