<script lang="ts">
  import { coverUrl } from '../lib/api';
  import { router } from '../lib/router.svelte';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
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
  const position = $derived(index !== null ? `${index + 1} / ${store.queue.items.length}` : '');
  const statusLabel = $derived(
    p?.status === 'loading' || p?.status === 'buffering' ? t('player.loading') : '',
  );

  function go(hash: string) {
    store.closeNowPlaying();
    // Let history.back() settle before navigating.
    setTimeout(() => router.navigate(hash), 30);
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

<svelte:window onkeydown={(e) => e.key === 'Escape' && store.closeNowPlaying()} />

<div
  class="np"
  role="dialog"
  aria-modal="true"
  aria-label={t('nowPlaying.title')}
  tabindex="-1"
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
      {#if position}<span class="muted">{position}</span>{/if}
    </div>
    <button class="icon-btn" aria-label={t('nav.queue')} title={t('nav.queue')} onclick={() => go('#/queue')}>
      <Icon name="queue" size={22} />
    </button>
  </header>

  <div class="body">
    <div class="art">
      {#if cover}
        <img src={cover} alt="" />
      {:else}
        <div class="art-placeholder"><Icon name="disc" size={72} /></div>
      {/if}
    </div>

    <div class="info">
      <div class="titles">
        <h2 class="ellipsis">{song?.title ?? t('player.nothing')}</h2>
        {#if song}
          <p class="ellipsis">
            {#if song.artist_id}
              <button class="link" onclick={() => go(`#/artist/${encodeURIComponent(song.artist_id ?? '')}`)}>{song.artist}</button>
            {:else}{song.artist}{/if}
            {#if song.album}
              <span class="dot">·</span>
              {#if song.album_id}
                <button class="link" onclick={() => go(`#/album/${encodeURIComponent(song.album_id ?? '')}`)}>{song.album}</button>
              {:else}{song.album}{/if}
            {/if}
          </p>
        {/if}
      </div>
      {#if song}
        {#key song.id}<StarButton kind="song" id={song.id} starred={song.starred} />{/key}
      {/if}
    </div>

    <SeekBar />
    {#if statusLabel}<p class="status muted">{statusLabel}</p>{/if}

    <PlayerControls size="large" />

    <div class="bottom">
      <DeviceButton />
      <div class="vol"><VolumeSlider /></div>
    </div>

    {#if next}
      <button class="up-next" onclick={() => go('#/queue')}>
        <span class="eyebrow">{t('queue.upNext')}</span>
        <span class="ellipsis"><strong>{next.title}</strong> <span class="muted">· {next.artist}</span></span>
        <span class="muted">{formatTime(next.duration)}</span>
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
    overflow: hidden auto;
    padding: env(safe-area-inset-top) 0 env(safe-area-inset-bottom);
    animation: rise 0.22s ease-out;
    transition: transform 0.05s;
  }
  @keyframes rise {
    from {
      transform: translateY(8%);
      opacity: 0;
    }
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
    grid-template-columns: 48px 1fr 48px;
    align-items: center;
    padding: 8px 8px 0;
  }
  .head-title {
    display: grid;
    justify-items: center;
    line-height: 1.2;
  }
  .eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
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
  }
  .art {
    width: 100%;
    max-width: min(420px, 46dvh);
    aspect-ratio: 1;
    margin: 0 auto 8px;
  }
  .art img,
  .art-placeholder {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 14px;
    box-shadow: var(--shadow);
    background: var(--surface-2);
    color: var(--muted);
    display: grid;
    place-items: center;
  }
  .info {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .titles {
    flex: 1;
    min-width: 0;
  }
  h2 {
    margin: 0 0 2px;
    font-size: 1.4rem;
  }
  .info p {
    margin: 0;
    color: var(--muted);
  }
  .dot {
    margin: 0 2px;
  }
  .link {
    background: none;
    padding: 0;
    min-height: 0;
    border-radius: 0;
    color: inherit;
  }
  .link:hover {
    text-decoration: underline;
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
