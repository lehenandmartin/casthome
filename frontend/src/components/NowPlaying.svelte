<script lang="ts">
  import { modal } from '../lib/modal';
  import { fadeIn } from '../lib/motion';
  import { coverUrl } from '../lib/api';
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
  const index = $derived(store.queue.index);
  const next = $derived(index !== null ? (store.queue.items[index + 1] ?? null) : null);
  const position = $derived(index !== null ? t('lcd.position', { n: index + 1, total: store.queue.items.length }) : '');

  // The LCD: what the iPod's screen would show, in Chicago.
  let shown = $state(0);
  const duration = $derived(p?.duration ?? song?.duration ?? 0);
  const casting = $derived(Boolean(p?.device_uuid) && !store.isThisBrowser);
  // Chicago draws Latin scripts only: a title in another script keeps the system font, whole line.
  const latin = (text: string) => /^[\u0000-\u024F\u1E00-\u1EFF\u2000-\u206F\u20A0-\u20CF\u2212]*$/.test(text);
  const title = $derived(song?.title ?? t('player.nothing'));
  const byline = $derived(song ? [song.artist, song.album].filter(Boolean).join(' / ') : '');

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
  style:transform={dragY ? `translateY(${dragY}px)` : undefined}
  ontouchstart={touchStart}
  ontouchmove={touchMove}
  ontouchend={touchEnd}
>
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
    <!-- The LCD, laid out like the iPod's Now Playing screen: the track's
         place in the queue and where it plays, then title, artist and album
         centred, the progress bar and the times. Long lines scroll pixel
         column by pixel column. -->
    <div class="display lcd lcd-screen recessed">
      <div class="top">
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
      <h2 class="scroll" class:sys={!latin(title)} use:menu={() => (song ? currentSongMenu(song) : null)} use:marquee={title}>
        {#if albumHref}
          <button class="lcd-btn" onclick={() => go(albumHref)}>{title}</button>
        {:else}
          <span>{title}</span>
        {/if}
      </h2>
      {#if song && byline}
        <!-- Artist / album on one line, each a link. -->
        <p class="scroll" class:sys={!latin(byline)} use:marquee={byline}>
          <span>
            {#if song.artist}{#if song.artist_id}
                <button class="lcd-btn" onclick={() => go(`#/artist/${encodeURIComponent(song.artist_id ?? '')}`)}>{song.artist}</button>
              {:else}{song.artist}{/if}{/if}{#if song.artist && song.album}{' / '}{/if}{#if song.album}{#if song.album_id}
                <button class="lcd-btn" onclick={() => go(`#/album/${encodeURIComponent(song.album_id ?? '')}`)}>{song.album}</button>
              {:else}{song.album}{/if}{/if}
          </span>
        </p>
      {/if}
      <SeekBar dots showTimes={false} bind:shown />
      <div class="times">
        <span aria-hidden="true">{formatTime(shown)}</span>
        <!-- Its name starts with the time shown (WCAG 2.5.3), then what a press does. -->
        <button class="lcd-btn" title={showTotal ? t('lcd.showRemaining') : t('lcd.showTotal')} onclick={toggleTotal}>
          {showTotal ? formatTime(duration) : `-${formatTime(Math.max(0, duration - shown))}`}<span class="sr-only"
            >, {showTotal ? t('lcd.showRemaining') : t('lcd.showTotal')}</span
          >
        </button>
      </div>
    </div>

    <div class="art" use:menu={() => (song ? currentSongMenu(song) : null)}>
      <!-- The cover set into the case, like the screen. -->
      <div class="well recessed">
        {#if cover}
          {#key cover}<img src={cover} alt="" in:fadeIn={{ duration: 220 }} />{/key}
        {:else}
          <div class="art-placeholder"><Icon name="disc" size={72} /></div>
        {/if}
      </div>
    </div>
    {#if statusLabel}<p class="status muted">{statusLabel}</p>{/if}

    <PlayerControls size="large" />

    <div class="bottom">
      <!-- The device's name is on the display (which opens the picker too): the icon is enough. -->
      <DeviceButton compact />
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
    overflow: hidden;
    padding: calc(env(safe-area-inset-top) + 12px) 0 env(safe-area-inset-bottom);
    transition: transform 0.05s;
    animation: rise 0.3s var(--ease-out);
  }
  @keyframes rise {
    from {
      opacity: 0;
    }
  }
  .np :global(.play) {
    background: var(--accent);
    color: var(--on-accent);
  }
  /* The LCD. Dark pixels on the grey-green reflector, all one size as on the
     iPod: 20px, a quarter more than Chicago's own 16px. The source in full
     ink when the music plays there, dimmed on this browser, red when lost. */
  .display {
    /* The hover underline: a dotted row of pixels. */
    --lcd-pitch: 2.5px;
    --lcd-dot: 1.25px;
    --lcd-lit: var(--lcd-ink);
    --lost: #9b2a20;
    display: grid;
    min-width: 0;
    padding: 8px 12px;
    --radius-w: 10px;
    border-radius: var(--radius-w);
    font-size: 20px;
    line-height: 22px;
  }
  .display > * {
    margin: 0;
  }
  .display h2 {
    font-size: inherit;
    font-weight: 400;
    letter-spacing: 0;
  }
  /* The first line: the place in the queue, and where it plays. */
  .top {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 16px;
    min-width: 0;
    color: var(--lcd-dim);
  }
  .top .source {
    min-width: 0;
  }
  .top .source.lit {
    color: var(--lcd-ink);
  }
  .top .source.lost {
    color: var(--lost);
  }
  .display .scroll {
    text-align: center;
  }
  .display .scroll:global(.scrolling) {
    text-align: left;
  }
  /* The seek bar: a little room above and below, for fingers. */
  .display :global(.dots) {
    height: 28px;
  }
  .times {
    display: flex;
    justify-content: space-between;
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
  /* A title in a script Chicago does not draw: the system font, the whole line. */
  .display .sys {
    font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
    font-size: var(--text-md);
    -webkit-font-smoothing: antialiased;
    letter-spacing: 0;
  }
  /* Words on the display that are buttons: still just pixels, with a touch
     area a little larger than the letters. */
  .lcd-btn {
    --pad-x: 4px;
    --pad-y: 6px;
    position: relative;
    font: inherit;
    letter-spacing: inherit;
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
     album, time): a dotted row of pixels lit under the word. */
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
    font-size: var(--text-xs);
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
    gap: 12px;
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
  /* Room for the lip all around. */
  .well {
    --radius-w: 12px;
    width: min(100cqw - 16px, 100cqh - 16px, 420px);
    aspect-ratio: 1;
    border-radius: var(--radius-w);
  }
  .art img,
  .art-placeholder {
    display: grid;
    place-items: center;
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: calc(var(--radius-w) - 1px);
    background: var(--surface-2);
    color: var(--muted);
  }

  .status {
    margin: -12px 0 0;
    text-align: center;
  }
  /* Even space around the controls: the play button is a full 72px disc,
     the icons around it and in the row below sit in larger boxes than they
     look, so the controls get more room above and the row below comes closer. */
  .body > :global(.controls) {
    margin-top: 12px;
  }
  .bottom {
    display: flex;
    align-items: center;
    gap: 16px;
    min-width: 0;
    margin-top: -8px;
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
    gap: 8px;
    text-align: left;
    border-radius: 12px;
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 12px 16px;
    min-width: 0;
  }
</style>
