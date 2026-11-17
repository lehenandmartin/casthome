<script lang="ts">
  import { api } from '../lib/api';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';

  // shown: the time on display, the dragged one while seeking (Now Playing's display reads it).
  // dots: drawn as a row of a dot-matrix display (Now Playing), lit one column at a time.
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
    <!-- The dots under the slider, which stays on top (invisible) for touch, mouse and keyboard. -->
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
  /* Dot-matrix row: unlit dots everywhere, lit ones up to the position, whole
     columns only. Dots and gaps are whole pixels, so the matrix stays visible
     on any screen (--lcd-pitch / --lcd-dot from the display). */
  .dots {
    --pitch: var(--lcd-pitch, 3px);
    --dot: var(--lcd-dot, 2px);
    --dot-on: var(--lcd-lit, var(--text));
    --dot-off: var(--lcd-ghost, color-mix(in srgb, var(--text) 18%, transparent));
    position: relative;
    display: grid;
    align-items: center;
    height: 24px;
  }
  .matrix,
  .lit {
    /* Two rows of dots. */
    height: calc(var(--pitch) + var(--dot));
    background-size: var(--pitch) var(--pitch);
    background-position: 0 0;
  }
  .matrix {
    width: 100%;
    width: round(down, 100%, var(--pitch));
    /* Square dots, like Doto's. */
    background-image: conic-gradient(at var(--dot) var(--dot), transparent 75%, var(--dot-off) 0);
  }
  .lit {
    width: calc(var(--progress) * 100%);
    width: round(down, calc(var(--progress) * 100%), var(--pitch));
    background-image: conic-gradient(at var(--dot) var(--dot), transparent 75%, var(--dot-on) 0);
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
