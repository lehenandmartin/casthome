<script lang="ts">
  import { api } from '../lib/api';
  import { isIOS } from '../lib/browserPlayer';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import Icon from './Icon.svelte';

  let local = $state<number | null>(null);
  let timer: ReturnType<typeof setTimeout> | undefined;

  const p = $derived(store.player);
  // iOS ignores volume changes on <audio>: use the hardware buttons there.
  const available = $derived(Boolean(p?.connected) && !(store.isThisBrowser && isIOS));
  const volume = $derived(local ?? p?.volume ?? 0);

  function change(event: Event) {
    const level = Number((event.target as HTMLInputElement).value);
    local = level;
    clearTimeout(timer);
    timer = setTimeout(async () => {
      await store.run(() => api.setVolume(level));
      local = null;
    }, 120);
  }
</script>

{#if available}
  <div class="volume">
    <Icon name={volume === 0 || p?.muted ? 'volumeMute' : 'volume'} size={18} />
    <input
      type="range"
      min="0"
      max="1"
      step="0.02"
      value={volume}
      style:--fill={`${volume * 100}%`}
      aria-label={t('player.volume')}
      oninput={change}
    />
  </div>
{/if}

<style>
  .volume {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--muted);
    width: 100%;
  }
</style>
