<script lang="ts">
  // A list row that reacts to horizontal swipes on touch screens, like Spotify:
  // swipe right -> `onright` (e.g. add to queue), swipe left -> `onleft`
  // (e.g. remove). A coloured background with an icon shows what will happen;
  // releasing before the threshold springs back and does nothing. Vertical
  // scrolling is untouched, and the tap that ends a swipe never "clicks".
  import type { Snippet } from 'svelte';
  import type { IconName } from '../lib/icons';
  import Icon from './Icon.svelte';

  interface Side {
    label: string;
    icon: IconName;
    action: () => void;
    /** Slide the row away before running the action (for removals). */
    dismiss?: boolean;
  }

  let { right, left, children }: { right?: Side; left?: Side; children: Snippet } = $props();

  const THRESHOLD = 0.3; // fraction of the row width
  const MIN_PX = 72;

  let row = $state<HTMLDivElement | null>(null);
  let dx = $state(0);
  let animating = $state(false);
  let start: { x: number; y: number; id: number } | null = null;
  let horizontal = false;
  let suppressClick = false;

  const width = () => row?.offsetWidth ?? 320;
  const limit = () => Math.max(MIN_PX, width() * THRESHOLD);
  const side = $derived(dx > 0 ? right : dx < 0 ? left : undefined);
  const armed = $derived(Math.abs(dx) >= limit());

  function down(e: PointerEvent) {
    if (e.pointerType !== 'touch' || animating) return;
    if ((e.target as HTMLElement).closest('[data-no-swipe]')) return; // e.g. the drag handle
    start = { x: e.clientX, y: e.clientY, id: e.pointerId };
    horizontal = false;
  }

  function move(e: PointerEvent) {
    if (!start || e.pointerId !== start.id) return;
    const mx = e.clientX - start.x;
    const my = e.clientY - start.y;
    if (!horizontal) {
      if (Math.abs(my) > 10 && Math.abs(my) > Math.abs(mx)) {
        start = null; // a vertical scroll: let the page have it
        return;
      }
      if (Math.abs(mx) < 10) return;
      horizontal = true;
      row?.setPointerCapture(e.pointerId);
    }
    let next = mx;
    if ((next > 0 && !right) || (next < 0 && !left)) next = next / 6; // resist on a side without action
    const wasArmed = Math.abs(dx) >= limit();
    dx = next;
    if (!wasArmed && Math.abs(dx) >= limit()) navigator.vibrate?.(8);
  }

  async function up(e: PointerEvent) {
    if (!start || e.pointerId !== start.id) return;
    start = null;
    if (!horizontal) return;
    suppressClick = true;
    setTimeout(() => (suppressClick = false), 350);
    const chosen = armed ? side : undefined;
    animating = true;
    if (chosen?.dismiss) {
      dx = dx > 0 ? width() : -width();
      await new Promise((r) => setTimeout(r, 180));
      chosen.action();
      // The row is normally removed by the next queue update; reset in case it is not.
      setTimeout(() => {
        dx = 0;
        animating = false;
      }, 400);
      return;
    }
    dx = 0;
    setTimeout(() => (animating = false), 200);
    chosen?.action();
  }

  function cancel() {
    start = null;
    animating = true;
    dx = 0;
    setTimeout(() => (animating = false), 200);
  }
</script>

<div class="swipe" class:active={dx !== 0}>
  {#if side}
    <div class="bg" class:to-right={dx > 0} class:to-left={dx < 0} class:armed class:danger={dx < 0}>
      <span class="hint" style:opacity={Math.min(1, Math.abs(dx) / limit())}>
        <Icon name={side.icon} size={20} />{side.label}
      </span>
    </div>
  {/if}
  <div
    bind:this={row}
    class="fg"
    class:animating
    style:transform={dx ? `translateX(${dx}px)` : undefined}
    onpointerdown={down}
    onpointermove={move}
    onpointerup={up}
    onpointercancel={cancel}
    onclickcapture={(e) => {
      if (suppressClick) {
        e.preventDefault();
        e.stopPropagation();
      }
    }}
    role="presentation"
  >
    {@render children()}
  </div>
</div>

<style>
  .swipe {
    position: relative;
    overflow: hidden;
    border-radius: 10px;
    flex: 1;
    min-width: 0;
  }
  .fg {
    position: relative;
    display: flex;
    align-items: center;
    min-width: 0;
    background: transparent; /* keeps the list's own hover styles */
    touch-action: pan-y; /* the browser keeps vertical scrolling, we get horizontal moves */
  }
  .active .fg {
    background: var(--bg); /* opaque while sliding, so the action colour shows only beside it */
  }
  .fg.animating {
    transition: transform 0.18s ease-out;
  }
  .bg {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    padding: 0 18px;
    background: var(--surface-3);
    color: var(--text);
    font-weight: 600;
    font-size: 0.9rem;
    transition: background 0.12s;
  }
  .bg.to-left {
    justify-content: flex-end;
  }
  .bg.armed {
    background: var(--accent);
    color: var(--on-accent);
  }
  .bg.armed.danger {
    background: var(--danger);
    color: var(--on-danger);
  }
  .hint {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
</style>
