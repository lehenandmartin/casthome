<script lang="ts">
  import { fadeIn } from '../lib/motion';
  import { coverUrl } from '../lib/api';
  import { menu } from '../lib/contextMenu.svelte';
  import { currentSongMenu } from '../lib/menus';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import DeviceButton from './DeviceButton.svelte';
  import Icon from './Icon.svelte';
  import PlayerControls from './PlayerControls.svelte';
  import SeekBar from './SeekBar.svelte';
  import StarButton from './StarButton.svelte';
  import VolumeSlider from './VolumeSlider.svelte';
  import { formatTime } from '../lib/format';
  import { marquee } from '../lib/marquee';


  const song = $derived(store.player?.current ?? null);
  const duration = $derived(store.player?.duration ?? song?.duration ?? 0);
  const progress = $derived(duration ? Math.min(100, (store.position / duration) * 100) : 0);
  const songMenu = () => (song ? currentSongMenu(song) : null);
  const casting = $derived(Boolean(store.player?.device_uuid) && !store.isThisBrowser);
  const source = $derived(
    !store.player?.device_uuid ? '' : store.isThisBrowser ? t('devices.thisBrowser') : (store.player.device_name ?? ''),
  );
  const title = $derived(song?.title ?? t('player.nothing'));
</script>

<footer class="player">
  <!-- Mobile: compact bar, tap to open Now Playing -->
  <div class="mini">
    <div class="mini-progress" style:width={`${progress}%`}></div>
    <button class="mini-main" use:menu={songMenu} disabled={!song} onclick={() => store.openNowPlaying()}>
      <!-- The visible title and source are part of the button's name (WCAG 2.5.3). -->
      <span class="sr-only">{t('nowPlaying.open')}:</span>
      <!-- A new track: its cover and title fade in. -->
      {#key song?.id}
        <!-- The cover set into the bar, like the display next to it. -->
        <span class="well recessed">
          {#if song?.cover_art}
            <img src={coverUrl(song.cover_art, 96)} alt="" in:fadeIn />
          {:else}
            <span class="thumb"><Icon name="disc" size={20} /></span>
          {/if}
        </span>
        <!-- A small version of Now Playing's display: the title scrolling dot by
             dot, then where it plays and the time. -->
        <span class="mini-display lcd lcd-screen recessed" in:fadeIn>
          <span class="scroll" use:marquee={title}><span>{title}</span></span>
          <span class="row">
            <span class="source ellipsis" class:lit={casting && store.player?.connected} class:lost={casting && !store.player?.connected}>{source}</span>
            <span aria-hidden="true">{formatTime(store.position)}</span>
          </span>
        </span>
      {/key}
    </button>
    <DeviceButton compact />
    <PlayerControls modes={false} />
  </div>

  <!-- Desktop: full bar -->
  <div class="full">
    <div class="now" use:menu={songMenu}>
      <button class="cover" disabled={!song} onclick={() => store.openNowPlaying()} aria-label={t('nowPlaying.open')}>
        {#key song?.id}
          <span class="well recessed">
            {#if song?.cover_art}
              <img src={coverUrl(song.cover_art, 128)} alt="" in:fadeIn />
            {:else}
              <span class="thumb"><Icon name="disc" size={22} /></span>
            {/if}
          </span>
        {/key}
      </button>
      <!-- The same small display as on phones; it opens Now Playing too. -->
      <button class="mini-display lcd lcd-screen recessed" disabled={!song} onclick={() => store.openNowPlaying()}>
        <span class="sr-only">{t('nowPlaying.open')}:</span>
        <span class="scroll" use:marquee={title}><span>{title}</span></span>
        <span class="row">
          <span class="source ellipsis" class:lit={casting && store.player?.connected} class:lost={casting && !store.player?.connected}>{source}</span>
        </span>
      </button>
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
      <!-- Its name is on the display: the icon is enough, as on phones. -->
      <DeviceButton compact />
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
    /* The cover and the display share one height. */
    --well-h: 44px;
    position: fixed;
    z-index: 30;
    left: 0;
    right: 0;
    background: var(--surface);
    border-top: 1px solid var(--border);
  }
  /* The cover set into the bar: the same lip and inner shadow as the display. */
  .well {
    --radius-w: 6px;
    --lip-w: 3px;
    display: block;
    flex: none;
    width: var(--well-h);
    height: var(--well-h);
    border-radius: var(--radius-w);
  }
  img,
  .thumb {
    width: 100%;
    height: 100%;
    border-radius: var(--radius-w);
    object-fit: cover;
    background: var(--surface-2);
    color: var(--muted);
    display: grid;
    place-items: center;
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
    padding: 0 8px 0 12px;
  }



  .mini-progress {
    position: absolute;
    top: -1px;
    left: 0;
    height: 2px;
    background: var(--accent);
    transition: width 0.5s linear;
  }

  /* A small LCD, the same as Now Playing's, as tall as the cover. */
  .mini-display {
    flex: 1;
    min-width: 0;
    height: var(--well-h);
    display: grid;
    align-content: center;
    gap: 2px;
    padding: 4px 8px;
    --radius-w: 8px;
    --lip-w: 3px;
    border-radius: var(--radius-w);
    font-size: 16px;
    line-height: 16px;
    text-align: left;
  }
  .mini-display .scroll {
    overflow: hidden;
    white-space: nowrap;
  }
  .mini-display .scroll > span {
    display: inline-block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    vertical-align: top;
  }
  .mini-display .scroll:global(.scrolling) > span {
    max-width: none;
    overflow: visible;
  }
  .mini-display .row {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    min-width: 0;
    /* Always two lines, the second empty when there is nothing to show. */
    min-height: 16px;
    color: var(--lcd-dim);
  }
  /* A long device name is cut, the time stays whole. */
  .mini-display .source {
    flex: 1;
    min-width: 0;
  }
  .mini-display .row > :not(.source) {
    flex: none;
  }
  .mini-display .source.lit {
    color: var(--lcd-ink);
  }
  .mini-display .source.lost {
    color: #9b2a20;
  }


  .mini-main {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 8px;
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
      --well-h: 56px;
    }
    .mini {
      display: none;
    }
    .full {
      display: grid;
      /* The left side holds the display: a little more room than the right. */
      grid-template-columns: minmax(0, 1.6fr) minmax(300px, 440px) minmax(200px, 1fr);
      align-items: center;
      gap: 24px;
      height: var(--player-desktop-h);
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
      width: 104px;
    }
    .vol:empty {
      display: none;
    }
    .full .mini-display {
      max-width: 340px;
      min-height: 0;
      cursor: pointer;
    }
    .full .mini-display:disabled {
      opacity: 1;
      cursor: default;
    }
  }

  /* A narrow desktop window: the display keeps its room, the controls give some up. */
  @media (min-width: 900px) and (max-width: 1279px) {
    .full {
      grid-template-columns: minmax(200px, 1.2fr) minmax(220px, 320px) minmax(192px, 1fr);
      gap: 16px;
    }
    .vol {
      width: 96px;
    }
  }
</style>
