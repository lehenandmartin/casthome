<script lang="ts">
  import { t } from '../lib/i18n';
  import type { MessageKey } from '../lib/i18n/en';
  import type { IconName } from '../lib/icons';
  import Icon from './Icon.svelte';

  const ENTRIES: { href: string; label: MessageKey; icon: IconName }[] = [
    { href: '#/playlists', label: 'nav.playlists', icon: 'playlist' },
    { href: '#/favorites', label: 'nav.favorites', icon: 'star' },
    { href: '#/artists', label: 'nav.artists', icon: 'artist' },
    { href: '#/genres', label: 'nav.genres', icon: 'tag' },
    { href: '#/', label: 'nav.albums', icon: 'disc' },
  ];
</script>

<section>
  <h2>{t('nav.library')}</h2>
  <ul>
    {#each ENTRIES as entry (entry.href)}
      <li>
        <a href={entry.href}>
          <span class="icon"><Icon name={entry.icon} size={22} /></span>
          <span class="label">{t(entry.label)}</span>
          <Icon name="chevronRight" size={18} />
        </a>
      </li>
    {/each}
  </ul>
  <ul>
    <li>
      <a href="#/account">
        <span class="icon"><Icon name="account" size={22} /></span>
        <span class="label">{t('nav.account')}</span>
        <Icon name="chevronRight" size={18} />
      </a>
    </li>
  </ul>
</section>

<style>
  ul {
    list-style: none;
    margin: 0 0 16px;
    padding: 0;
    border-radius: var(--radius);
    background: var(--surface);
    border: 1px solid var(--border);
    overflow: hidden;
  }
  li + li {
    border-top: 1px solid var(--border);
  }
  a {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 14px;
    text-decoration: none;
    color: var(--muted);
  }
  a:active {
    background: var(--surface-2);
  }
  .icon {
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: var(--accent-soft);
    color: var(--accent);
  }
  .label {
    flex: 1;
    font-weight: 600;
    color: var(--text);
  }
</style>
