<script lang="ts">
  // The app's icon, drawn live: the Cast mark with its screen, in amber dots on
  // the dark glass of the hi-fi display, the other dots faintly visible. Same
  // dots as the installed icon (scripts/make_icons.py, mark()).
  //
  // boot: the mark's dots light up column by column when it appears, like a
  // display switching on (not with reduced motion).

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
      <rect x="0.11" y="0.11" width="0.78" height="0.78" class="ghost" />
    </pattern>
  </defs>
  <rect width="24" height="24" rx="5.25" class="glass" />
  <rect width="24" height="24" rx="5.25" fill={`url(#${id})`} />
  {#each lit as dot (dot.x * 24 + dot.y)}
    <rect x={dot.x + 0.11} y={dot.y + 0.11} width="0.78" height="0.78" class="dot" style:--col={dot.x - 3} />
  {/each}
</svg>

<style>
  .mark {
    display: block;
    flex: none;
  }
  .glass {
    fill: #141312;
  }
  .ghost {
    fill: #f2a43a;
    opacity: 0.07;
  }
  .dot {
    fill: #f2a43a;
  }
  /* Switching on: one column after another, each dot snapping on, no fade. */
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
