<script lang="ts">
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';

  let { id, rating = $bindable(0) }: { id: string; rating?: number } = $props();

  async function rate(event: MouseEvent, stars: number) {
    event.stopPropagation();
    const previous = rating;
    const next = stars === rating ? 0 : stars; // clicking the current rating clears it
    rating = next;
    try {
      await api.setRating(id, next);
    } catch {
      rating = previous;
      store.notify('navidrome_unavailable');
    }
  }
</script>

<span class="rating" role="group" aria-label={t('song.rating')}>
  {#each [1, 2, 3, 4, 5] as stars (stars)}
    <button
      class:on={stars <= rating}
      aria-label={stars === rating ? t('rating.clear') : t('rating.set', { stars })}
      title={stars === rating ? t('rating.clear') : t('rating.set', { stars })}
      onclick={(e) => rate(e, stars)}>{stars <= rating ? '★' : '☆'}</button
    >
  {/each}
</span>

<style>
  .rating {
    display: inline-flex;
  }
  button {
    background: none;
    border: 0;
    padding: 4px 2px;
    font-size: 18px;
    color: var(--muted);
  }
  button.on {
    color: var(--star);
  }
</style>
