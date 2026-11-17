<script lang="ts">
  import { api } from '../lib/api';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';

  // shown: the time on display, the dragged one while seeking (Now Playing's display reads it).
  // dots: drawn as the iPod's progress bar on the LCD (Now Playing): a hollow bar filling with ink.
  let {
    showTimes = true,
    shown = $bindable(0),
    dots = false,
  }: { showTimes?: boolean; shown?: number; dots?: boolean } = $props();
  let dragging = $state<number | null>(null);

  const duration = $derived(store.player?.duration ?? store.player?.current?.duration ?? 0);
  const position = $derived(dragging ?? store.position);
  $effect(() => {
    shown = position;
  });
  const ratio = $derived(duration ? Math.min(1, position / duration) : 0);
  const fill = $derived(duration ? `${Math.min(100, (position / duration) * 100)}%` : '0%');

  function commit() {
    if (dragging === null) return;
    const target = dragging;
    dragging = null;
    store.run(() => api.seek(target));
  }
</script>

<div class="seek" class:dots style:--progress={ratio}>
  {#if dots}
    <!-- The bar under the slider, which stays on top (invisible) for touch, mouse and keyboard. -->
    <div class="matrix" aria-hidden="true"><div class="lit"></div></div>
  {/if}
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
    <div class="times muted figures">
      <span>{formatTime(position)}</span>
      <span>-{formatTime(Math.max(0, duration - position))}</span>
    </div>
  {/if}
</div>

<style>
  .seek {
    width: 100%;
  }
  /* The iPod's progress bar: a hollow bar with round ends in the LCD's ink,
     filling up to the position in whole pixels. */
  .dots {
    --ink: var(--lcd-lit, var(--text));
    position: relative;
    display: grid;
    align-items: center;
    height: 24px;
  }
  .matrix {
    height: 12px;
    border: 2px solid var(--ink);
    border-radius: 6px;
    overflow: hidden;
  }
  /* Filled to the full height; the bar's round end clips its start, its own
     end stays straight, as on the iPod. */
  .lit {
    height: 100%;
    width: calc(var(--progress) * 100%);
    width: round(down, calc(var(--progress) * 100%), 1px);
    background: var(--ink);
  }
  .dots input {
    position: absolute;
    inset: 0;
    height: 100%;
    opacity: 0;
  }
  .dots:has(input:focus-visible) {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
    border-radius: 4px;
  }
  .times {
    display: flex;
    justify-content: space-between;
    font-size: var(--text-xs);
    font-variant-numeric: tabular-nums;
    margin-top: -2px;
  }
</style>
