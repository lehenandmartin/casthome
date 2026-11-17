<script lang="ts">
  // One track of the queue (upcoming or history): cover, title, artist and
  // length; tap to play it, ✕ or swipe left to remove it. Upcoming tracks also
  // have a reorder handle and, from the album/playlist, swipe right to move
  // them to "Next in queue".
  import { dragHandle } from 'svelte-dnd-action';
  import { coverUrl } from '../lib/api';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import Icon from './Icon.svelte';
  import SwipeRow from './SwipeRow.svelte';

  interface Track {
    title: string;
    artist: string;
    cover_art?: string | null;
    duration: number;
  }

  let {
    item,
    handle = false,
    onplay,
    onremove,
    onqueue,
  }: {
    item: Track;
    /** Show the drag handle (inside a svelte-dnd-action zone). */
    handle?: boolean;
    onplay: () => void;
    onremove: () => void;
    /** Swipe right: move to "Next in queue". */
    onqueue?: () => void;
  } = $props();
</script>

<SwipeRow
  left={{ label: t('queue.remove'), icon: 'trash', action: onremove, dismiss: true }}
  right={onqueue ? { label: t('song.addToQueue'), icon: 'queue', action: onqueue } : undefined}
>
  {#if handle}
    <span class="handle" data-no-swipe use:dragHandle aria-label={t('queue.drag')} title={t('queue.drag')}>
      <Icon name="grip" size={18} />
    </span>
  {/if}
  <button class="row" class:no-handle={!handle} onclick={onplay}>
    {#if item.cover_art}
      <img src={coverUrl(item.cover_art, 96)} alt="" loading="lazy" />
    {:else}
      <span class="thumb"><Icon name="disc" size={18} /></span>
    {/if}
    <span class="text">
      <span class="ellipsis">{item.title}</span>
      <span class="muted ellipsis">{item.artist}</span>
    </span>
    <span class="muted time figures">{formatTime(item.duration)}</span>
  </button>
  <button class="icon-btn remove" aria-label={t('queue.remove')} title={t('queue.remove')} onclick={onremove}
    ><Icon name="close" size={18} /></button
  >
</SwipeRow>

<style>
  .handle {
    flex: none;
    width: 34px;
    height: 48px;
    display: grid;
    place-items: center;
    color: var(--muted);
    cursor: grab;
    touch-action: none;
  }
  .row {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    text-align: left;
    background: none;
    padding: 6px 4px;
    border-radius: 10px;
    min-height: 0;
  }
  .row.no-handle {
    padding-left: 10px;
  }
  img,
  .thumb {
    width: 44px;
    height: 44px;
    border-radius: 6px;
    object-fit: cover;
    background: var(--surface-2);
    color: var(--muted);
    display: grid;
    place-items: center;
    flex: none;
  }
  .text {
    flex: 1;
    display: grid;
    min-width: 0;
  }
  .time {
    font-variant-numeric: tabular-nums;
  }
  .remove {
    color: var(--muted);
    flex: none;
  }
  /* Touch screens: swipe left removes, so no ✕; the reorder handle moves to
     the right edge, under the thumb. Mouse users keep handle left + ✕. */
  @media (hover: none) and (pointer: coarse) {
    .remove {
      display: none;
    }
    .handle {
      order: 1;
      width: 48px;
      height: 52px;
    }
    .row {
      padding-left: 10px;
    }
  }
</style>
