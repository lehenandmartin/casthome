<script lang="ts">
  import { api } from '../lib/api';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';

  let { showTimes = true }: { showTimes?: boolean } = $props();
  let dragging = $state<number | null>(null);

  const duration = $derived(store.player?.duration ?? store.player?.current?.duration ?? 0);
  const position = $derived(dragging ?? store.position);
  const fill = $derived(duration ? `${Math.min(100, (position / duration) * 100)}%` : '0%');

  function commit() {
    if (dragging === null) return;
    const target = dragging;
    dragging = null;
    store.run(() => api.seek(target));
  }
</script>

<div class="seek">
  <input
    type="range"
    min="0"
    max={duration || 1}
    step="1"
    value={position}
    style:--fill={fill}
    disabled={!store.player?.current || !duration}
    aria-label={t('player.seek')}
    aria-valuetext={`${formatTime(position)} / ${formatTime(duration)}`}
    oninput={(e) => (dragging = Number((e.target as HTMLInputElement).value))}
    onchange={commit}
  />
  {#if showTimes}
    <div class="times muted">
      <span>{formatTime(position)}</span>
      <span>-{formatTime(Math.max(0, duration - position))}</span>
    </div>
  {/if}
</div>

<style>
  .seek {
    width: 100%;
  }
  .times {
    display: flex;
    justify-content: space-between;
    font-size: 0.78rem;
    font-variant-numeric: tabular-nums;
    margin-top: -2px;
  }
</style>
