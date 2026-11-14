<script lang="ts">
  // "Favorites only" filter chip, shared by Tracks, Albums and Artists. The
  // state lives in the URL (?fav=1) so links and Back keep it.
  import { t } from '../lib/i18n';
  import { router } from '../lib/router.svelte';
  import Icon from './Icon.svelte';

  let { active }: { active: boolean } = $props();

  function toggle() {
    const [path, query = ''] = router.hash.split('?');
    const params = new URLSearchParams(query);
    if (active) params.delete('fav');
    else params.set('fav', '1');
    const next = params.toString();
    router.navigate(`${path || '#/'}${next ? `?${next}` : ''}`, { replace: true });
  }
</script>

<button class="fav" class:on={active} aria-pressed={active} onclick={toggle}>
  <Icon name={active ? 'starFilled' : 'star'} size={16} />{t('favorites.filter')}
</button>

<style>
  .fav {
    flex: none;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.9rem;
  }
  .fav.on {
    background: color-mix(in srgb, var(--star) 18%, transparent);
    color: var(--star);
  }
</style>
