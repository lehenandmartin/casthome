<script lang="ts">
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { RepeatMode } from '../lib/types';
  import Icon from './Icon.svelte';

  let { size = 'normal', modes = true }: { size?: 'normal' | 'large'; modes?: boolean } = $props();

  const p = $derived(store.player);
  const actuallyPlaying = $derived(p?.status === 'playing' || p?.status === 'buffering' || p?.status === 'loading');
  // Play/pause answers the tap at once; the server's state takes over when it arrives.
  const playing = $derived(optimistic.value ?? actuallyPlaying);
  // Only a real change of status ends the optimistic state (not every player update).
  const status = $derived(p?.status);
  $effect(() => {
    void status;
    optimistic.value = null;
  });

  function toggle() {
    optimistic.value = !actuallyPlaying;
    clearTimeout(optimistic.timer);
    optimistic.timer = setTimeout(() => (optimistic.value = null), 3000);
    store.run(async () => {
      try {
        await api.action('toggle');
      } catch (error) {
        optimistic.value = null;
        throw error;
      }
    });
  }
  const busy = $derived(p?.status === 'loading' || p?.status === 'buffering');
  const hasQueue = $derived(store.queue.items.length > 0);
  const nextRepeat: Record<RepeatMode, RepeatMode> = { off: 'all', all: 'one', one: 'off' };
  const repeat = $derived(p?.repeat ?? 'off');
  const big = $derived(size === 'large');
</script>

<script lang="ts" module>
  // Shared by every player bar (mini, full, Now Playing), so they all agree.
  const optimistic = $state<{ value: boolean | null; timer?: ReturnType<typeof setTimeout> }>({ value: null });
</script>

<div class="controls" class:big>
  {#if modes}
    <button
      class="icon-btn"
      class:on={p?.shuffle}
      aria-pressed={p?.shuffle ?? false}
      aria-label={t('player.shuffle')}
      title={t('player.shuffle')}
      onclick={() => store.run(() => api.setMode({ shuffle: !p?.shuffle }))}
    >
      <Icon name="shuffle" size={big ? 22 : 18} />
    </button>
  {/if}
  <button
    class="icon-btn"
    disabled={!hasQueue}
    aria-label={t('player.previous')}
    title={t('player.previous')}
    onclick={() => store.run(() => api.action('previous'))}
  >
    <Icon name="previous" size={big ? 32 : 22} />
  </button>
  <button
    class="play"
    class:busy
    disabled={!hasQueue}
    aria-label={playing ? t('player.pause') : t('player.play')}
    title={playing ? t('player.pause') : t('player.play')}
    onclick={toggle}
  >
    <Icon name={playing ? 'pause' : 'play'} size={big ? 34 : 22} />
  </button>
  <button
    class="icon-btn"
    disabled={!hasQueue}
    aria-label={t('player.next')}
    title={t('player.next')}
    onclick={() => store.run(() => api.action('next'))}
  >
    <Icon name="next" size={big ? 32 : 22} />
  </button>
  {#if modes}
    <button
      class="icon-btn"
      class:on={repeat !== 'off'}
      aria-label={t(`player.repeat.${repeat}`)}
      title={t(`player.repeat.${repeat}`)}
      onclick={() => store.run(() => api.setMode({ repeat: nextRepeat[repeat] }))}
    >
      <Icon name={repeat === 'one' ? 'repeatOne' : 'repeat'} size={big ? 22 : 18} />
    </button>
  {/if}
</div>

<style>
  .controls {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }
  .controls.big {
    justify-content: space-between;
    gap: 0;
  }
  .big .icon-btn {
    width: 52px;
    height: 52px;
  }
  .play {
    display: grid;
    place-items: center;
    width: 42px;
    height: 42px;
    min-height: 0;
    padding: 0;
    border-radius: 50%;
    background: var(--text);
    color: var(--bg);
  }
  .big .play {
    width: 72px;
    height: 72px;
  }
  .play.busy {
    animation: pulse 1.2s ease-in-out infinite;
  }
  @keyframes pulse {
    50% {
      opacity: 0.6;
    }
  }
</style>
