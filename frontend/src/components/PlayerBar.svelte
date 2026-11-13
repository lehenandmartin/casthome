<script lang="ts">
  import { api, coverUrl } from '../lib/api';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { RepeatMode } from '../lib/types';
  import DevicePicker from './DevicePicker.svelte';

  let pickerOpen = $state(false);
  let seeking = $state<number | null>(null);

  const p = $derived(store.player);
  const song = $derived(p?.current ?? null);
  const playing = $derived(p?.status === 'playing' || p?.status === 'buffering' || p?.status === 'loading');
  const duration = $derived(p?.duration ?? song?.duration ?? 0);
  const position = $derived(seeking ?? store.position);
  const nextRepeat: Record<RepeatMode, RepeatMode> = { off: 'all', all: 'one', one: 'off' };

  function commitSeek() {
    if (seeking === null) return;
    const target = seeking;
    seeking = null;
    store.run(() => api.seek(target));
  }

  let volumeTimer: ReturnType<typeof setTimeout> | undefined;
  function changeVolume(event: Event) {
    const level = Number((event.target as HTMLInputElement).value);
    clearTimeout(volumeTimer);
    volumeTimer = setTimeout(() => store.run(() => api.setVolume(level)), 150);
  }
</script>

<footer class="player">
  <input
    class="seek"
    type="range"
    min="0"
    max={duration || 1}
    step="1"
    value={position}
    disabled={!song || !duration}
    aria-label={formatTime(position)}
    oninput={(e) => (seeking = Number((e.target as HTMLInputElement).value))}
    onchange={commitSeek}
  />
  <div class="bar">
    <div class="now">
      {#if song?.cover_art}
        <img src={coverUrl(song.cover_art, 96)} alt="" />
      {:else}
        <span class="thumb"></span>
      {/if}
      <div class="text">
        <span class="title">{song?.title ?? t('player.nothing')}</span>
        <span class="muted">
          {#if song}{song.artist} · {formatTime(position)} / {formatTime(duration)}{/if}
        </span>
      </div>
    </div>

    <div class="controls">
      <button
        class="icon"
        class:on={p?.shuffle}
        title={t('player.shuffle')}
        aria-label={t('player.shuffle')}
        aria-pressed={p?.shuffle ?? false}
        onclick={() => store.run(() => api.setMode({ shuffle: !p?.shuffle }))}>⤮</button
      >
      <button class="icon" title={t('player.previous')} aria-label={t('player.previous')} onclick={() => store.run(() => api.action('previous'))}>⏮</button>
      <button
        class="icon big"
        title={playing ? t('player.pause') : t('player.play')}
        aria-label={playing ? t('player.pause') : t('player.play')}
        onclick={() => store.run(() => api.action('toggle'))}>{playing ? '⏸' : '▶'}</button
      >
      <button class="icon" title={t('player.next')} aria-label={t('player.next')} onclick={() => store.run(() => api.action('next'))}>⏭</button>
      <button
        class="icon"
        class:on={p && p.repeat !== 'off'}
        title={t(`player.repeat.${p?.repeat ?? 'off'}`)}
        aria-label={t(`player.repeat.${p?.repeat ?? 'off'}`)}
        onclick={() => store.run(() => api.setMode({ repeat: nextRepeat[p?.repeat ?? 'off'] }))}
        >{p?.repeat === 'one' ? '🔂' : '🔁'}</button
      >
    </div>

    <div class="device">
      {#if p?.connected}
        <input
          class="volume"
          type="range"
          min="0"
          max="1"
          step="0.02"
          value={p.volume}
          aria-label={t('player.volume')}
          oninput={changeVolume}
        />
      {/if}
      <button class="device-btn" class:warn={p?.device_uuid && !p.connected} onclick={() => (pickerOpen = true)}>
        📡 {p?.device_name ?? t('devices.choose')}
      </button>
    </div>
  </div>
</footer>

{#if pickerOpen}
  <DevicePicker onclose={() => (pickerOpen = false)} />
{/if}

<style>
  .player {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 10;
    background: var(--surface);
    border-top: 1px solid var(--border);
    padding-bottom: env(safe-area-inset-bottom);
  }
  .seek {
    display: block;
    width: 100%;
    margin: 0;
    height: 4px;
    accent-color: var(--accent);
  }
  .bar {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 8px 16px;
  }
  @media (min-width: 720px) {
    .bar {
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
    }
  }
  .now {
    display: flex;
    gap: 12px;
    align-items: center;
    min-width: 0;
  }
  img,
  .thumb {
    width: 44px;
    height: 44px;
    border-radius: 4px;
    object-fit: cover;
    background: var(--surface-2);
    flex: none;
  }
  .text {
    display: grid;
    min-width: 0;
  }
  .text span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .title {
    font-weight: 600;
  }
  .controls {
    display: flex;
    justify-content: center;
    gap: 4px;
  }
  .icon {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 0;
    background: none;
    font-size: 18px;
    opacity: 0.85;
  }
  .icon.on {
    color: var(--accent);
    opacity: 1;
  }
  .icon.big {
    background: var(--accent);
    color: var(--on-accent);
    opacity: 1;
  }
  .device {
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: flex-end;
    min-width: 0;
  }
  .volume {
    width: 96px;
    accent-color: var(--accent);
  }
  .device-btn {
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .device-btn.warn {
    border-color: var(--danger);
  }
</style>
