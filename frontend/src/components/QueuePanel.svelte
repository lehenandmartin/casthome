<script lang="ts">
  import { riseOut, slideOutRight } from '../lib/motion';
  // The queue as a layer, never a page:
  // - mobile: a sheet that slides up over the page or Now Playing; Back, the
  //   chevron or a swipe down on its header closes it and returns there;
  // - desktop: a panel on the right, next to the page, toggled from the
  //   player bar or the sidebar.
  import { contextMenu } from '../lib/contextMenu.svelte';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import Icon from './Icon.svelte';
  import QueueView from './QueueView.svelte';

  let dragY = $state(0);
  let startY: number | null = null;

  function down(e: PointerEvent) {
    if (store.isDesktop || e.pointerType !== 'touch') return;
    startY = e.clientY;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }
  function move(e: PointerEvent) {
    if (startY !== null) dragY = Math.max(0, e.clientY - startY);
  }
  function up() {
    if (startY === null) return;
    startY = null;
    if (dragY > 90) store.closeQueue();
    dragY = 0;
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && !e.defaultPrevented && !contextMenu.current && !store.isDesktop && store.closeQueue()} />

{#if store.isDesktop}
  <aside class="side" out:slideOutRight|global aria-label={t('queue.title')}>
    <div class="side-head">
      <h2>{t('queue.title')}</h2>
      <button class="icon-btn" aria-label={t('queue.close')} title={t('queue.close')} onclick={() => store.closeQueue()}>
        <Icon name="close" size={20} />
      </button>
    </div>
    <div class="scroll"><QueueView embedded /></div>
  </aside>
{:else}
  <div
    class="sheet-layer"
    out:riseOut|global
    role="dialog"
    aria-modal="true"
    aria-label={t('queue.title')}
    style:transform={dragY ? `translateY(${dragY}px)` : undefined}
  >
    <div
      class="grab"
      role="presentation"
      onpointerdown={down}
      onpointermove={move}
      onpointerup={up}
      onpointercancel={up}
    >
      <button class="icon-btn" aria-label={t('queue.close')} title={t('queue.close')} onclick={() => store.closeQueue()}>
        <Icon name="chevronDown" size={26} />
      </button>
      <span class="grab-title">{t('queue.title')}</span>
      <span class="spacer" aria-hidden="true"></span>
    </div>
    <div class="scroll"><QueueView embedded /></div>
  </div>
{/if}

<style>
  /* --- mobile sheet --- */
  .sheet-layer {
    position: fixed;
    inset: 0;
    z-index: 55; /* above Now Playing (50), below sheets and dialogs */
    display: flex;
    flex-direction: column;
    background: var(--bg);
    padding-top: calc(env(safe-area-inset-top) + 10px);
    animation: rise 0.22s ease-out;
    transition: transform 0.05s;
  }
  @keyframes rise {
    from {
      transform: translateY(12%);
      opacity: 0;
    }
  }
  .grab {
    display: grid;
    grid-template-columns: 48px 1fr 48px;
    align-items: center;
    padding: 0 8px 4px;
    touch-action: none;
  }
  .grab-title {
    text-align: center;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
  }
  .scroll {
    flex: 1;
    overflow: auto;
    overscroll-behavior: contain;
    padding: 0 16px calc(24px + env(safe-area-inset-bottom));
  }

  /* --- desktop side panel --- */
  .side {
    position: fixed;
    z-index: 25; /* below the player bar (30) and overlays */
    top: 0;
    right: 0;
    bottom: 84px; /* the player bar */
    width: var(--queue-w);
    display: flex;
    flex-direction: column;
    background: var(--surface);
    border-left: 1px solid var(--border);
    animation: slide-in 0.18s ease-out;
  }
  @keyframes slide-in {
    from {
      transform: translateX(24px);
      opacity: 0;
    }
  }
  .side-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 12px 0 20px;
  }
  .side-head h2 {
    margin: 0;
    font-size: 1.15rem;
  }
  .side .scroll {
    padding: 0 12px 16px 16px;
  }
</style>
