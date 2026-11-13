<script lang="ts">
  import { coverUrl } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import DeviceButton from './DeviceButton.svelte';
  import Icon from './Icon.svelte';
  import PlayerControls from './PlayerControls.svelte';
  import SeekBar from './SeekBar.svelte';
  import StarButton from './StarButton.svelte';
  import VolumeSlider from './VolumeSlider.svelte';

  const song = $derived(store.player?.current ?? null);
  const duration = $derived(store.player?.duration ?? song?.duration ?? 0);
  const progress = $derived(duration ? Math.min(100, (store.position / duration) * 100) : 0);
  const casting = $derived(Boolean(store.player?.device_uuid) && !store.isThisBrowser);
</script>

<footer class="player">
  <!-- Mobile: compact bar, tap to open Now Playing -->
  <div class="mini">
    <div class="mini-progress" style:width={`${progress}%`}></div>
    <button class="mini-main" disabled={!song} onclick={() => store.openNowPlaying()} aria-label={t('nowPlaying.open')}>
      {#if song?.cover_art}
        <img src={coverUrl(song.cover_art, 96)} alt="" />
      {:else}
        <span class="thumb"><Icon name="disc" size={20} /></span>
      {/if}
      <span class="text">
        <span class="title ellipsis">{song?.title ?? t('player.nothing')}</span>
        <span class="sub ellipsis" class:casting>
          {#if casting}{t('player.onDevice', { device: store.player?.device_name ?? '' })}{:else if song}{song.artist}{/if}
        </span>
      </span>
    </button>
    <DeviceButton compact />
    <PlayerControls modes={false} />
  </div>

  <!-- Desktop: full bar -->
  <div class="full">
    <div class="now">
      <button class="cover" disabled={!song} onclick={() => store.openNowPlaying()} aria-label={t('nowPlaying.open')}>
        {#if song?.cover_art}
          <img src={coverUrl(song.cover_art, 128)} alt="" />
        {:else}
          <span class="thumb"><Icon name="disc" size={22} /></span>
        {/if}
      </button>
      <div class="text">
        <span class="title ellipsis">{song?.title ?? t('player.nothing')}</span>
        {#if song}
          <span class="sub ellipsis">
            {#if song.artist_id}<a href={`#/artist/${encodeURIComponent(song.artist_id)}`}>{song.artist}</a>{:else}{song.artist}{/if}
          </span>
        {/if}
      </div>
      {#if song}
        {#key song.id}<StarButton kind="song" id={song.id} starred={song.starred} />{/key}
      {/if}
    </div>
    <div class="center">
      <PlayerControls />
      <SeekBar />
    </div>
    <div class="right">
      <div class="vol"><VolumeSlider /></div>
      <DeviceButton />
      <button
        class="icon-btn"
        class:on={store.queuePanel}
        aria-pressed={store.queuePanel}
        aria-label={t('nav.queue')}
        title={t('nav.queue')}
        onclick={() => store.toggleQueue()}><Icon name="queue" size={20} /></button
      >
    </div>
  </div>
</footer>

<style>
  .player {
    position: fixed;
    z-index: 30;
    left: 0;
    right: 0;
    background: color-mix(in srgb, var(--surface) 92%, transparent);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-top: 1px solid var(--border);
  }
  img,
  .thumb {
    width: 44px;
    height: 44px;
    border-radius: 6px;
    object-fit: cover;
    background: var(--surface-2);
    color: var(--muted);
    display: grid;
    place-items: center;
    flex: none;
  }
  .text {
    display: grid;
    min-width: 0;
    text-align: left;
  }
  .title {
    font-weight: 600;
  }
  .sub {
    color: var(--muted);
    font-size: 0.85rem;
  }
  .sub a {
    text-decoration: none;
  }
  .sub a:hover {
    text-decoration: underline;
  }
  .sub.casting {
    color: var(--accent);
  }

  /* --- mobile --- */
  .player {
    bottom: var(--tabbar-h);
  }
  .full {
    display: none;
  }
  .mini {
    position: relative;
    display: flex;
    align-items: center;
    gap: 2px;
    height: var(--player-h);
    padding: 0 8px 0 10px;
  }
  .mini-progress {
    position: absolute;
    top: -1px;
    left: 0;
    height: 2px;
    background: var(--accent);
    transition: width 0.5s linear;
  }
  .mini-main {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 10px;
    background: none;
    padding: 0;
    border-radius: 8px;
  }
  .mini-main:disabled {
    opacity: 1;
  }
  /* Mini player keeps play/pause and next only. */
  .mini :global(.controls > button:first-child) {
    display: none;
  }

  /* --- desktop --- */
  @media (min-width: 900px) {
    .player {
      bottom: 0;
      left: var(--sidebar-w);
    }
    .mini {
      display: none;
    }
    .full {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(300px, 480px) minmax(0, 1fr);
      align-items: center;
      gap: 24px;
      height: 84px;
      padding: 0 20px;
    }
    .now {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }
    .cover {
      padding: 0;
      background: none;
      border-radius: 6px;
      min-height: 0;
    }
    .cover img,
    .cover .thumb {
      width: 56px;
      height: 56px;
    }
    .center {
      display: grid;
      gap: 0;
    }
    .right {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      min-width: 0;
    }
    .vol {
      width: 120px;
    }
    .vol:empty {
      display: none;
    }
    .right :global(.device) {
      max-width: 200px;
    }
  }
</style>
