<script lang="ts">
  // A titled, horizontally scrolling row for the home page. Touch: swipe it;
  // desktop: arrow buttons appear next to the title.
  import type { Snippet } from 'svelte';
  import { t } from '../lib/i18n';
  import Icon from './Icon.svelte';

  let { title, seeAll, children }: { title: string; seeAll?: string; children: Snippet } = $props();
  let track = $state<HTMLDivElement | null>(null);

  function scroll(direction: 1 | -1) {
    if (!track) return;
    track.scrollBy({ left: direction * track.clientWidth * 0.85, behavior: 'smooth' });
  }
</script>

<section class="row">
  <div class="head">
    <h3>{title}</h3>
    <div class="tools">
      {#if seeAll}<a class="see-all" href={seeAll}>{t('home.seeAll')}</a>{/if}
      <button class="icon-btn arrow" aria-label={t('home.scrollLeft')} onclick={() => scroll(-1)}>
        <Icon name="chevronLeft" size={20} />
      </button>
      <button class="icon-btn arrow" aria-label={t('home.scrollRight')} onclick={() => scroll(1)}>
        <Icon name="chevronRight" size={20} />
      </button>
    </div>
  </div>
  <div class="track" bind:this={track} role="group" aria-label={title}>
    {@render children()}
  </div>
</section>

<style>
  .row {
    margin: 24px 0 0;
  }
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }
  h3 {
    margin: 0;
    font-size: var(--text-lg);
  }
  .tools {
    display: flex;
    align-items: center;
    gap: 2px;
  }
  .see-all {
    color: var(--muted);
    font-size: var(--text-sm);
    font-weight: 600;
    text-decoration: none;
    margin-right: 4px;
  }
  .see-all:hover {
    color: var(--text);
  }
  .arrow {
    display: none;
  }
  @media (hover: hover) and (pointer: fine) {
    .arrow {
      display: inline-grid;
      width: 32px;
      height: 32px;
    }
  }
  .track {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    scrollbar-width: none;
    margin: 0 -16px;
    padding: 0 16px 4px;
    scroll-padding: 0 16px;
  }
  .track::-webkit-scrollbar {
    display: none;
  }
  .track > :global(*) {
    scroll-snap-align: start;
    flex: none;
  }
  @media (min-width: 900px) {
    .track {
      margin: 0 -32px;
      padding: 0 32px 4px;
      scroll-padding: 0 32px;
    }
  }
</style>
