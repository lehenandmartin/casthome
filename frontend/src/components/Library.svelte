<script lang="ts">
  import { t } from '../lib/i18n';
  import type { MessageKey } from '../lib/i18n/en';
  import type { IconName } from '../lib/icons';
  import Icon from './Icon.svelte';
  import { store } from '../lib/store.svelte';

  const ENTRIES: { href: string; label: MessageKey; icon: IconName }[] = [
    { href: '#/playlists', label: 'nav.playlists', icon: 'playlist' },
    { href: '#/tracks', label: 'nav.tracks', icon: 'music' },
    { href: '#/artists', label: 'nav.artists', icon: 'artist' },
    { href: '#/genres', label: 'nav.genres', icon: 'tag' },
    { href: '#/albums', label: 'nav.albums', icon: 'disc' },
  ];
</script>

<section>
  <h2>{t('nav.library')}</h2>
  <ul role="list">
    {#each ENTRIES.filter((e) => e.href !== '#/tracks' || store.capabilities.all_tracks) as entry (entry.href)}
      <li>
        <a href={entry.href}>
          <span class="icon"><Icon name={entry.icon} size={22} /></span>
          <span class="label">{t(entry.label)}</span>
          <Icon name="chevronRight" size={18} />
        </a>
      </li>
    {/each}
  </ul>
  <ul role="list">
    <li>
      <a href="#/settings">
        <span class="icon"><Icon name="settings" size={22} /></span>
        <span class="label">{t('nav.settings')}</span>
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
    background: var(--surface-2);
    color: var(--muted);
  }
  .label {
    flex: 1;
    font-weight: 500;
    color: var(--text);
  }
</style>
