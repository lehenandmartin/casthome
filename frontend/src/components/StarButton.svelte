<script lang="ts">
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { StarKind } from '../lib/types';

  let { kind, id, starred = $bindable(false) }: { kind: StarKind; id: string; starred?: boolean } = $props();
  let busy = $state(false);

  async function toggle(event: MouseEvent) {
    event.stopPropagation();
    if (busy) return;
    busy = true;
    const next = !starred;
    starred = next; // optimistic
    try {
      await api.setStarred(kind, id, next);
    } catch {
      starred = !next;
      store.notify('navidrome_unavailable');
    } finally {
      busy = false;
    }
  }
</script>

<button
  class="star"
  class:on={starred}
  aria-pressed={starred}
  aria-label={starred ? t('star.remove') : t('star.add')}
  title={starred ? t('star.remove') : t('star.add')}
  onclick={toggle}>{starred ? '★' : '☆'}</button
>

<style>
  .star {
    background: none;
    border: 0;
    width: 40px;
    height: 40px;
    padding: 0;
    font-size: 20px;
    color: var(--muted);
    flex: none;
  }
  .star.on {
    color: var(--star);
  }
</style>
