<script lang="ts">
  // The app's icon, drawn live: the Cast mark with its screen, in dark pixels on
  // the grey-green LCD of the installed icon, the unlit pixels faintly visible.
  // Same pixels and colours as the installed icon (scripts/make_icons.py), without
  // its white case, too fine at these sizes.
  //
  // boot: the mark's pixels darken column by column when it appears, like an
  // LCD switching on (not with reduced motion).

  let { size = 32, boot = false }: { size?: number; boot?: boolean } = $props();

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
  const lit = ROWS.flatMap((row, j) => [...row].flatMap((c, i) => (c === '#' ? [{ x: i + 3, y: j + 3 }] : [])));

  // Each pattern needs its own id on the page.
  const id = `mark-dots-${Math.random().toString(36).slice(2, 8)}`;
</script>

<svg class="mark" class:boot width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
  <defs>
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
  <rect width="24" height="24" rx="4" fill={`url(#${id})`} />
  {#each lit as dot (dot.x * 24 + dot.y)}
    <rect x={dot.x + 0.11} y={dot.y + 0.11} width="0.78" height="0.78" rx="0.2" class="dot" style:--col={dot.x - 3} />
  {/each}
  <rect width="24" height="24" rx="4" fill={`url(#${id}-shade)`} />
  <rect x="0.25" y="0.25" width="23.5" height="23.5" rx="3.75" class="bezel" />
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
  /* Switching on: one column after another, each pixel snapping on, no fade. */
  .boot .dot {
    animation: dot-on 1ms step-end both;
    animation-delay: calc(120ms + var(--col) * 28ms);
  }
  @keyframes dot-on {
    from {
      opacity: 0.07;
    }
  }
</style>
