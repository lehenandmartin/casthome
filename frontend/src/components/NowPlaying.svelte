<script lang="ts">
  import { modal } from '../lib/modal';
  import { fadeIn } from '../lib/motion';
  import { coverUrl } from '../lib/api';
  import { albumColor, type AlbumColor } from '../lib/albumColor';
  import { contextMenu, menu } from '../lib/contextMenu.svelte';
  import { currentSongMenu } from '../lib/menus';
  import { startRadio } from '../lib/radio';
  import { router } from '../lib/router.svelte';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import { marquee } from '../lib/marquee';
  import DeviceButton from './DeviceButton.svelte';
  import Icon from './Icon.svelte';
  import PlayerControls from './PlayerControls.svelte';
  import SeekBar from './SeekBar.svelte';
  import StarButton from './StarButton.svelte';
  import VolumeSlider from './VolumeSlider.svelte';

  const p = $derived(store.player);
  const song = $derived(p?.current ?? null);
  const cover = $derived(song?.cover_art ? coverUrl(song.cover_art, 800) : null);
  // The album's own colour for the seek bar and play button (amber if the cover is grey).
  let tint = $state<AlbumColor | null>(null);
  $effect(() => {
    const url = song?.cover_art ? coverUrl(song.cover_art, 96) : null;
    let current = true;
    if (!url) tint = null;
    else albumColor(url).then((color) => current && (tint = color));
    return () => (current = false);
  });
  const index = $derived(store.queue.index);
  const next = $derived(index !== null ? (store.queue.items[index + 1] ?? null) : null);
  const pad = (n: number) => String(n).padStart(2, '0');
  const position = $derived(index !== null ? `${pad(index + 1)}/${pad(store.queue.items.length)}` : '');

  // The hi-fi display: what the amplifier would show, in Doto.
  let shown = $state(0);
  const duration = $derived(p?.duration ?? song?.duration ?? 0);
  const casting = $derived(Boolean(p?.device_uuid) && !store.isThisBrowser);
  // Doto draws Latin scripts only: a title in another script keeps the system font, whole line.
  const latin = (text: string) => /^[\u0000-\u024F\u1E00-\u1EFF\u2000-\u206F\u20A0-\u20CF\u2212]*$/.test(text);
  const title = $derived(song?.title ?? t('player.nothing'));
  const byline = $derived(song ? [song.artist, song.album].filter(Boolean).join(' · ') : '');

  const albumHref = $derived(song?.album_id ? `#/album/${encodeURIComponent(song.album_id)}` : null);

  // The second time on the display: remaining (default) or the track's length, remembered.
  let showTotal = $state((() => {
    try {
      return localStorage.getItem('casthome.lcdTotal') === '1';
    } catch {
      return false;
    }
  })());
  function toggleTotal() {
    showTotal = !showTotal;
    try {
      localStorage.setItem('casthome.lcdTotal', showTotal ? '1' : '0');
    } catch {
      /* private mode: lasts until the page closes */
    }
  }

  const source = $derived(
    !p?.device_uuid ? '' : store.isThisBrowser ? t('devices.thisBrowser') : (p.device_name ?? ''),
  );
  const statusLabel = $derived(
    p?.status === 'loading' || p?.status === 'buffering' ? t('player.loading') : '',
  );

  function go(hash: string) {
    // Navigate once the "back" that closes Now Playing is done, or it would undo the navigation.
    store.closeNowPlaying().then(() => router.navigate(hash));
  }

  // Swipe down to close (mobile).
  let startY: number | null = null;
  let dragY = $state(0);
  function touchStart(e: TouchEvent) {
    startY = (e.target as HTMLElement).closest('input, .controls') ? null : e.touches[0].clientY;
  }
  function touchMove(e: TouchEvent) {
    if (startY !== null) dragY = Math.max(0, e.touches[0].clientY - startY);
  }
  function touchEnd() {
    if (dragY > 110) store.closeNowPlaying();
    startY = null;
    dragY = 0;
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && !e.defaultPrevented && !contextMenu.current && store.closeNowPlaying()} />

<div
  class="np"
  use:modal
  role="dialog"
  aria-modal="true"
  aria-label={t('nowPlaying.title')}
  tabindex="-1"
  class:tinted={tint}
  style:--album-h={tint?.h}
  style:--album-s={tint ? `${tint.s}%` : undefined}
  style:transform={dragY ? `translateY(${dragY}px)` : undefined}
  ontouchstart={touchStart}
  ontouchmove={touchMove}
  ontouchend={touchEnd}
>
  {#if cover}<div class="backdrop" style:background-image={`url("${cover}")`}></div>{/if}

  <header>
    <button class="icon-btn" aria-label={t('nowPlaying.close')} title={t('nowPlaying.close')} onclick={() => store.closeNowPlaying()}>
      <Icon name="chevronDown" size={26} />
    </button>
    <div class="head-title">
      <span class="eyebrow">{t('nowPlaying.title')}</span>
    </div>
    {#if song}
      <div class="head-actions">
        <button class="icon-btn" aria-label={t('song.startRadio')} title={t('song.startRadio')} onclick={() => startRadio(song)}>
          <Icon name="radio" size={22} />
        </button>
        {#key song.id}<StarButton kind="song" id={song.id} starred={song.starred} />{/key}
      </div>
    {:else}
      <span aria-hidden="true"></span>
    {/if}
  </header>

  <div class="body">
    <div class="art" use:menu={() => (song ? currentSongMenu(song) : null)}>
      {#if cover}
        {#key cover}<img src={cover} alt="" in:fadeIn={{ duration: 220 }} />{/key}
      {:else}
        <div class="art-placeholder"><Icon name="disc" size={72} /></div>
      {/if}
    </div>

    <!-- The amplifier's display: the track, its progress, the source and the modes.
         Long lines scroll column by column, like a real dot matrix. -->
    <div class="display lcd glass">
      <div class="line small">
        <span aria-hidden="true">{position}</span>
        {#if source}
          <button
            class="lcd-btn source ellipsis"
            class:lit={casting && p?.connected}
            class:lost={casting && !p?.connected}
            aria-label={`${t('devices.title')}: ${source}`}
            onclick={() => (store.devicePickerOpen = true)}>{source}</button
          >
        {/if}
      </div>
      <h2 class="scroll title" class:sys={!latin(title)} use:menu={() => (song ? currentSongMenu(song) : null)} use:marquee={title}>
        {#if albumHref}
          <button class="lcd-btn" onclick={() => go(albumHref)}>{title}</button>
        {:else}
          <span>{title}</span>
        {/if}
      </h2>
      {#if song}
        <p class="scroll byline" class:sys={!latin(byline)} use:marquee={byline}>
          <span>
            {#if song.artist_id}
              <button class="lcd-btn" onclick={() => go(`#/artist/${encodeURIComponent(song.artist_id ?? '')}`)}>{song.artist}</button>
            {:else}{song.artist}{/if}{#if song.album}
              {' · '}{#if song.album_id}
                <button class="lcd-btn" onclick={() => go(`#/album/${encodeURIComponent(song.album_id ?? '')}`)}>{song.album}</button>
              {:else}{song.album}{/if}
            {/if}
          </span>
        </p>
      {/if}
      <SeekBar dots showTimes={false} bind:shown />
      <div class="line small">
        <span aria-hidden="true">{formatTime(shown)}</span>
        <button class="lcd-btn" aria-label={showTotal ? t('lcd.showRemaining') : t('lcd.showTotal')} onclick={toggleTotal}>
          {showTotal ? formatTime(duration) : `-${formatTime(Math.max(0, duration - shown))}`}
        </button>
      </div>
    </div>
    {#if statusLabel}<p class="status muted">{statusLabel}</p>{/if}

    <PlayerControls size="large" />

    <div class="bottom">
      <DeviceButton />
      <div class="vol"><VolumeSlider /></div>
      <!-- Under the repeat button, as in Spotify. -->
      <button class="icon-btn queue-btn" aria-label={t('nav.queue')} title={t('nav.queue')} onclick={() => store.openQueue()}>
        <Icon name="queue" size={22} />
      </button>
    </div>

    {#if next}
      <button class="up-next" onclick={() => store.openQueue()}>
        <span class="eyebrow">{t('queue.upNext')}</span>
        <span class="ellipsis"><strong>{next.title}</strong> <span class="muted">· {next.artist}</span></span>
        <span class="muted figures">{formatTime(next.duration)}</span>
      </button>
    {/if}
  </div>
</div>

<style>
  .np {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: flex;
    flex-direction: column;
    background: var(--bg);
    /* The blurred backdrop overflows on purpose: it never makes the page scroll. */
    overflow: hidden;
    padding: calc(env(safe-area-inset-top) + 10px) 0 env(safe-area-inset-bottom);
    transition: transform 0.05s;
    animation: rise 0.22s ease-out;
  }
  @keyframes rise {
    from {
      opacity: 0;
    }
  }
  /* The album's colour replaces the amber here only, at a lightness that keeps
     the play button's icon readable in each theme. */
  .np.tinted {
    --accent: hsl(var(--album-h) var(--album-s) 38%);
    --on-accent: #ffffff;
  }
  @media (prefers-color-scheme: dark) {
    .np.tinted {
      --accent: hsl(var(--album-h) var(--album-s) 70%);
      --on-accent: #1a1816;
    }
  }
  .np :global(.play) {
    background: var(--accent);
    color: var(--on-accent);
    transition: background-color 0.4s ease-out;
  }
  /* The display. Lit words in full, unlit ones faintly visible like the ghost
     segments of a real display; the source lamp is amber, red when lost. */
  .display {
    --lit: var(--text);
    --ghost: color-mix(in srgb, var(--text) 18%, transparent);
    --lost: var(--danger);
    display: grid;
    /* Tight rows, as on a real display: one line of dots after another.
       Sizes in whole pixels keep the dots below on the screen's pixel grid. */
    gap: 4px;
    line-height: 16px;
    min-width: 0;
    text-transform: uppercase;
  }
  /* The seek bar: a little room above and below, for fingers. */
  .display :global(.dots) {
    height: 27px;
    margin: 0;
  }
  /* Dark glass in both themes, like a real display. */
  .display.glass {
    /* Dots drawn by the page (seek bar, underline): 2px squares 1px apart,
       whole pixels so they stay apart on every screen. */
    --lcd-pitch: 3px;
    --lcd-dot: 2px;
    --lcd-lit: var(--lit);
    --lcd-ghost: var(--ghost);
    --lit: #ece6dc;
    --ghost: rgb(236 230 220 / 0.16);
    --lamp: #f2a43a;
    --lost: #ec7a76;
    padding: 12px 16px;
    border-radius: 12px;
    background: #141312;
    border: 1px solid rgb(255 255 255 / 0.06);
    color: var(--lit);
  }

  .display .line {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 16px;
    min-width: 0;
  }
  .display .small {
    font-size: 14px;
  }

  .display .source {
    color: var(--ghost);
    min-width: 0;
  }
  .display .source.lit {
    color: var(--lamp);
  }
  .display .source.lost {
    color: var(--lost);
  }



  /* Title and artist on the display: one line each, scrolling when too long
     (lib/marquee.ts), cut with "…" when motion is reduced. */
  .display .scroll {
    /* Room under the letters for the hover underline, which the clipping would cut. */
    margin: 0 0 -6px;
    padding-bottom: 6px;
    letter-spacing: 0;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  /* The text box can move (inline-block); still, it ends with "…" while still. */
  .display .scroll > :first-child {
    display: inline-block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    vertical-align: top;
  }
  .display .scroll:global(.scrolling) > :first-child {
    max-width: none;
    overflow: visible;
  }
  .display .title {
    font-size: 20px;
    font-weight: 400;
    line-height: 22px;
  }
  .display .byline {
    font-size: 14px;
    color: rgb(236 230 220 / 0.62);
  }
  /* A title in a script Doto does not draw: the system font, the whole line. */
  .display .sys {
    font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
    text-transform: none;
    letter-spacing: 0;
  }
  /* Words on the display that are buttons: still just lit dots, with a touch
     area a little larger than the letters. */
  .lcd-btn {
    --pad-x: 4px;
    --pad-y: 6px;
    position: relative;
    font: inherit;
    letter-spacing: inherit;
    text-transform: inherit;
    color: inherit;
    background: none;
    border: 0;
    border-radius: 4px;
    min-height: 0;
    padding: var(--pad-y) var(--pad-x);
    margin: calc(var(--pad-y) * -1) calc(var(--pad-x) * -1);
    text-align: left;
  }
  /* In a scrolling line the button is the text that moves: no extra box. */
  .scroll .lcd-btn {
    --pad-x: 0px;
    --pad-y: 0px;
    padding: 0;
    margin: 0;
    border-radius: 0;
  }
  .lcd-btn:disabled {
    opacity: 1;
  }
  /* One hover for every word that does something (device, title, artist,
     album, time): a dotted underline, a row of dots lit under the word. */
  @media (hover: hover) {
    /* Square dots of one size everywhere (the display's pitch, like the seek
       bar), whatever the size of the word: a row of the same matrix, one
       blank row under the letters. */
    .lcd-btn:hover:not(:disabled)::after {
      content: '';
      position: absolute;
      left: var(--pad-x);
      right: var(--pad-x);
      top: calc(100% - var(--pad-y) + var(--lcd-pitch));
      height: var(--lcd-dot);
      background-image: conic-gradient(at var(--lcd-dot) var(--lcd-dot), transparent 75%, currentColor 0);
      background-size: var(--lcd-pitch) var(--lcd-pitch);
      background-repeat: repeat-x;
      pointer-events: none;
    }
  }
  .head-actions {
    display: flex;
    justify-content: flex-end;
  }

  .backdrop {
    position: absolute;
    inset: -40px;
    background-size: cover;
    background-position: center;
    filter: blur(60px) saturate(1.4);
    opacity: 0.35;
    pointer-events: none;
  }
  header,
  .body {
    position: relative;
  }
  header {
    display: grid;
    grid-template-columns: 96px 1fr 96px;
    align-items: center;
    padding: 8px 8px 0;
  }
  .head-title {
    display: grid;
    justify-items: center;
    line-height: 1.2;
  }
  .eyebrow {
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--muted);
  }
  .body {
    flex: 1;
    width: 100%;
    max-width: 480px;
    margin: 0 auto;
    padding: 12px 24px 20px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 14px;
    min-height: 0;
    /* Only a very short screen (a phone on its side) scrolls the content. */
    overflow: hidden auto;
  }
  /* Everything fits the screen without scrolling: the cover takes the height
     left by the rest, as a square as large as that space allows. */
  .art {
    flex: 1 1 0;
    min-height: 120px;
    container-type: size;
    display: grid;
    place-items: center;
  }
  .art img,
  .art-placeholder {
    width: min(100cqw, 100cqh, 420px);
    height: auto;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: 14px;
    box-shadow: var(--shadow);
    background: var(--surface-2);
    color: var(--muted);
    display: grid;
    place-items: center;
  }





  .status {
    margin: -10px 0 0;
    text-align: center;
  }
  .bottom {
    display: flex;
    align-items: center;
    gap: 16px;
    min-width: 0;
  }
  .bottom :global(.device) {
    flex: none;
    max-width: 60%;
  }
  .vol {
    flex: 1;
    min-width: 0;
  }
  .queue-btn {
    /* Same width as the large repeat button above it, so their centres line up. */
    width: 52px;
    height: 52px;
    margin-left: auto;
    flex: none;
  }
  .up-next {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 10px;
    text-align: left;
    border-radius: 12px;
    background: color-mix(in srgb, var(--surface) 70%, transparent);
    padding: 10px 14px;
    min-width: 0;
  }
</style>
