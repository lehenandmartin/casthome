<script lang="ts" module>
  // When the switching on (boot) is over, in ms: what follows it (the About
  // screen's text) waits for it.
  export const BOOT_END = 1660;
</script>

<script lang="ts">
  // The app's icon, drawn live: the Cast mark with its screen, in dark pixels on
  // the grey-green LCD of the installed icon, the unlit pixels faintly visible.
  // Same pixels and colours as the installed icon (scripts/make_icons.py), without
  // its white case, too fine at these sizes.
  //
  // boot: the mark switches on in the order it is read, each pixel snapping
  // on: the dot, the first wave, the second, then the screen's frame drawn
  // like a snake, from the stub on the left, along the top, down the right
  // and back along the bottom (not with reduced motion). Driven by the time
  // since it appeared, read on every frame, not by CSS delays: a scroll or a
  // touch that holds frames back only makes it catch up, it never stalls.
  // elapsed (bindable): that time, Infinity once it is over, for what
  // follows (the About screen's text).
  //
  // bare: the mark's pixels alone, cropped to the mark, for a place that is
  // already an LCD (About).

  let {
    size = 32,
    boot = false,
    bare = false,
    elapsed = $bindable(boot ? 0 : Infinity),
  }: { size?: number; boot?: boolean; bare?: boolean; elapsed?: number } = $props();

  $effect(() => {
    if (!boot || matchMedia('(prefers-reduced-motion: reduce)').matches) {
      elapsed = Infinity;
      return;
    }
    const start = performance.now();
    let frame = requestAnimationFrame(function tick(now) {
      elapsed = now - start;
      // A little past the end, for what waits on it.
      if (elapsed < BOOT_END + 1000) frame = requestAnimationFrame(tick);
      else elapsed = Infinity;
    });
    return () => cancelAnimationFrame(frame);
  });

  // The mark on its 24-dot grid: '#' is lit (rows 3 to 20, columns 3 to 20).
  const ROWS = [
    '..................',
    '##################',
    '##################',
    '##..............##',
    '##..............##',
    '................##',
    '................##',
    '.#####..........##',
    '.######.........##',
    '.....###........##',
    '.###..###.......##',
    '.####..###......##',
    '...###..##......##',
    '....###.##......##',
    '###..##.##......##',
    '###..##.##.#######',
    '###........#######',
    '..................',
  ];
  // When each pixel switches on (ms): the dot and the waves as a whole, the
  // frame one step of its path after another (two pixels thick).
  const DOT_AT = 150;
  const WAVE_AT = [400, 650];
  const FRAME_AT = 900;
  const FRAME_STEP = 20;
  function onAt(x: number, y: number): number {
    const dist = Math.hypot(x - 4, 18 - y); // from the dot's centre, as in make_icons.py
    if (dist <= 1.5) return DOT_AT;
    if (dist >= 3.5 && dist < 5.5) return WAVE_AT[0];
    if (dist >= 7 && dist < 9) return WAVE_AT[1];
    let step: number;
    if (x <= 4 && y >= 6) step = 7 - y; // the stub on the left, going up
    else if (y <= 5) step = 2 + (x - 3); // the top, going right
    else if (x >= 19) step = 20 + (y - 6); // the right side, going down
    else step = 34 + (18 - x); // the bottom, going left
    return FRAME_AT + step * FRAME_STEP;
  }
  const lit = ROWS.flatMap((row, j) =>
    [...row].flatMap((c, i) => (c === '#' ? [{ x: i + 3, y: j + 3, at: onAt(i + 3, j + 3) }] : [])),
  );

  // Each pattern needs its own id on the page.
  const id = `mark-dots-${Math.random().toString(36).slice(2, 8)}`;
</script>

<svg class="mark" width={size} height={size} viewBox={bare ? '3 3 18 18' : '0 0 24 24'} aria-hidden="true">
  {#if !bare}<defs>
    <pattern {id} width="1" height="1" patternUnits="userSpaceOnUse">
      <rect x="0.11" y="0.11" width="0.78" height="0.78" rx="0.2" class="ghost" />
    </pattern>
    <radialGradient id="{id}-lcd" cx="0.5" cy="0.55" r="0.75">
      <stop offset="0" stop-color="#c4cbb2" />
      <stop offset="1" stop-color="#a9b195" />
    </radialGradient>
    <!-- The window's soft inner shadow, deeper at the top. -->
    <linearGradient id="{id}-shade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#000" stop-opacity="0.22" />
      <stop offset="0.12" stop-color="#000" stop-opacity="0" />
    </linearGradient>
  </defs>
  <rect width="24" height="24" rx="4" fill={`url(#${id}-lcd)`} />
  <rect width="24" height="24" rx="4" fill={`url(#${id})`} />{/if}
  {#each lit as dot (dot.x * 24 + dot.y)}
    <rect x={dot.x + 0.11} y={dot.y + 0.11} width="0.78" height="0.78" rx="0.2" class="dot" class:off={elapsed < dot.at} />
  {/each}
  {#if !bare}
    <rect width="24" height="24" rx="4" fill={`url(#${id}-shade)`} />
    <rect x="0.25" y="0.25" width="23.5" height="23.5" rx="3.75" class="bezel" />
  {/if}
</svg>

<style>
  .mark {
    display: block;
    flex: none;
  }
  .ghost {
    fill: #1b2219;
    opacity: 0.07;
  }
  .dot {
    fill: #1b2219;
  }
  .bezel {
    fill: none;
    stroke: #8d9384;
    stroke-width: 0.5;
  }
  /* Not on yet: an unlit pixel, faintly visible. Each snaps on, no fade. */
  .dot.off {
    opacity: 0.07;
  }
</style>
