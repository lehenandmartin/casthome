<script lang="ts">
  import { ApiError, api } from './lib/api';
  import { t } from './lib/i18n';
  import type { IconName } from './lib/icons';
  import type { MessageKey } from './lib/i18n/en';
  import type { AlbumListType } from './lib/types';
  import { router } from './lib/router.svelte';
  import { store } from './lib/store.svelte';
  import AlbumView from './components/AlbumView.svelte';
  import Albums from './components/Albums.svelte';
  import ArtistView from './components/ArtistView.svelte';
  import Artists from './components/Artists.svelte';
  import DevicePicker from './components/DevicePicker.svelte';
  import Dialog from './components/Dialog.svelte';
  import GenreView from './components/GenreView.svelte';
  import Genres from './components/Genres.svelte';
  import Icon from './components/Icon.svelte';
  import Home from './components/Home.svelte';
  import Library from './components/Library.svelte';
  import Login from './components/Login.svelte';
  import NowPlaying from './components/NowPlaying.svelte';
  import PlayerBar from './components/PlayerBar.svelte';
  import PlaylistView from './components/PlaylistView.svelte';
  import Playlists from './components/Playlists.svelte';
  import QueuePanel from './components/QueuePanel.svelte';
  import Search from './components/Search.svelte';
  import Settings from './components/Settings.svelte';
  import Toasts from './components/Toasts.svelte';
  import Tracks from './components/Tracks.svelte';

  const hash = $derived(router.hash);

  const PAGES = ['albums', 'artists', 'genres', 'playlists', 'tracks', 'search', 'settings', 'library'] as const;
  type Page = (typeof PAGES)[number] | 'home';
  type Route = { name: Page } | { name: 'album' | 'artist' | 'genre' | 'playlist'; id: string };

  const route = $derived.by((): Route => {
    const path = hash.split('?')[0];
    const detail = path.match(/^#\/(album|artist|genre|playlist)\/(.+)$/);
    if (detail) return { name: detail[1] as 'album' | 'artist' | 'genre' | 'playlist', id: decodeURIComponent(detail[2]) };
    const page = path.replace(/^#\//, '');
    return { name: (PAGES as readonly string[]).includes(page) ? (page as Page) : 'home' };
  });
  // Query options: #/albums?type=recent, and ?fav=1 (favorites only) on
  // Tracks, Albums and Artists.
  const query = $derived(new URLSearchParams(hash.split('?')[1] ?? ''));
  const albumsType = $derived((query.get('type') as AlbumListType | null) ?? 'newest');
  const favOnly = $derived(query.get('fav') === '1');

  const PARENT: Record<string, string> = { album: 'albums', artist: 'artists', genre: 'genres', playlist: 'playlists' };
  const section = $derived(PARENT[route.name] ?? route.name);
  // Mobile tabs: Library groups albums, tracks, artists, genres, playlists and settings.
  const LIBRARY_SECTIONS = new Set(['library', 'albums', 'artists', 'genres', 'playlists', 'tracks', 'settings']);
  const tab = $derived(LIBRARY_SECTIONS.has(section) ? 'library' : section);

  interface NavItem {
    href: string;
    name: string;
    label: MessageKey;
    icon: IconName;
  }
  const SIDEBAR: NavItem[] = [
    { href: '#/', name: 'home', label: 'nav.home', icon: 'home' },
    { href: '#/search', name: 'search', label: 'nav.search', icon: 'search' },
    { href: '#/albums', name: 'albums', label: 'nav.albums', icon: 'disc' },
    { href: '#/tracks', name: 'tracks', label: 'nav.tracks', icon: 'music' },
    { href: '#/artists', name: 'artists', label: 'nav.artists', icon: 'artist' },
    { href: '#/genres', name: 'genres', label: 'nav.genres', icon: 'tag' },
    { href: '#/playlists', name: 'playlists', label: 'nav.playlists', icon: 'playlist' },
  ];
  const TABS: NavItem[] = [
    { href: '#/', name: 'home', label: 'nav.home', icon: 'home' },
    { href: '#/search', name: 'search', label: 'nav.search', icon: 'search' },
    { href: '#/library', name: 'library', label: 'nav.library', icon: 'library' },
  ];

  const upcoming = $derived(
    store.queue.index !== null ? Math.max(0, store.queue.items.length - store.queue.index - 1) : store.queue.items.length,
  );

  // Restore the session (cookie) on load.
  // Only a 401 signs out: if the server is briefly unreachable, keep the cached
  // state on screen and let the live connection retry.
  api
    .me()
    .then(() => store.signedIn())
    .catch((err) => (err instanceof ApiError && err.status === 401 ? store.signedOut() : store.signedIn()));
</script>

<Toasts />
<Dialog />
<!-- Installed iOS app: the status bar is translucent; keep scrolled content from showing through it. -->
<div class="statusbar-bg" aria-hidden="true"></div>

{#if store.auth === 'signed-out'}
  <Login />
{:else if store.auth === 'signed-in'}
  <aside class="sidebar">
    <div class="brand"><Icon name="cast" size={24} />{t('app.name')}</div>
    <nav>
      {#each SIDEBAR as item (item.name)}
        <a href={item.href} class:active={section === item.name}>
          <Icon name={item.icon} size={20} />{t(item.label)}
        </a>
      {/each}
      <!-- The queue is a panel next to the page, not a page. -->
      <button class="nav-btn" class:active={store.queuePanel} aria-pressed={store.queuePanel} onclick={() => store.toggleQueue()}>
        <Icon name="queue" size={20} />{t('nav.queue')}
        {#if upcoming > 0}<span class="badge">{upcoming}</span>{/if}
      </button>
    </nav>
    <a class="settings-link" href="#/settings" class:active={section === 'settings'}>
      <Icon name="settings" size={20} />{t('nav.settings')}
    </a>
  </aside>

  <main class="content" class:with-queue={store.isDesktop && store.queuePanel}>
    {#if route.name === 'album'}
      <AlbumView id={route.id} />
    {:else if route.name === 'artist'}
      <ArtistView id={route.id} />
    {:else if route.name === 'genre'}
      {#key route.id}<GenreView name={route.id} />{/key}
    {:else if route.name === 'playlist'}
      <PlaylistView id={route.id} />
    {:else if route.name === 'settings'}
      <Settings />
    {:else if route.name === 'library'}
      <Library />
    {:else if route.name === 'playlists'}
      <Playlists />
    {:else if route.name === 'tracks'}
      <Tracks fav={favOnly} />
    {:else if route.name === 'artists'}
      <Artists fav={favOnly} />
    {:else if route.name === 'genres'}
      <Genres />
    {:else if route.name === 'search'}
      <Search />
    {:else if route.name === 'albums'}
      {#key `${albumsType}-${favOnly}`}<Albums type={albumsType} fav={favOnly} />{/key}
    {:else}
      <Home />
    {/if}
  </main>

  <PlayerBar />

  <nav class="tabbar">
    {#each TABS as item (item.name)}
      <a href={item.href} class:active={tab === item.name}>
        <span class="tab-icon"><Icon name={item.icon} size={22} /></span>
        <span>{t(item.label)}</span>
      </a>
    {/each}
  </nav>

  {#if store.nowPlayingOpen}<NowPlaying />{/if}
  {#if store.queueVisible}<QueuePanel />{/if}
  {#if store.devicePickerOpen}<DevicePicker />{/if}
{/if}

<style>
  .statusbar-bg {
    position: fixed;
    z-index: 45;
    top: 0;
    left: 0;
    right: 0;
    /* Solid under the status bar, then a short fade for content scrolling under it. */
    height: calc(env(safe-area-inset-top) + 14px);
    background: linear-gradient(var(--bg) calc(100% - 14px), transparent);
    pointer-events: none;
  }

  .content {
    /* Extra room at the top: installed iOS apps blur the area under the status bar. */
    padding: calc(env(safe-area-inset-top) + 28px) 16px calc(var(--tabbar-h) + var(--player-h) + 24px);
    max-width: 1200px;
    margin: 0 auto;
  }

  .badge {
    display: inline-grid;
    place-items: center;
    min-width: 18px;
    height: 18px;
    padding: 0 5px;
    border-radius: 999px;
    background: var(--accent);
    color: var(--on-accent);
    font-size: 0.68rem;
    font-weight: 700;
  }

  /* --- mobile tab bar --- */
  .sidebar {
    display: none;
  }
  .tabbar {
    position: fixed;
    z-index: 31;
    left: 0;
    right: 0;
    bottom: 0;
    height: var(--tabbar-h);
    padding-bottom: env(safe-area-inset-bottom);
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    background: var(--surface);
    border-top: 1px solid var(--border);
  }
  .tabbar a {
    display: grid;
    justify-items: center;
    align-content: center;
    gap: 2px;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--muted);
    text-decoration: none;
  }
  .tabbar a.active {
    color: var(--accent);
  }
  .tab-icon {
    position: relative;
  }

  /* --- desktop sidebar --- */
  @media (min-width: 900px) {
    .tabbar {
      display: none;
    }
    .sidebar {
      position: fixed;
      z-index: 20;
      inset: 0 auto 0 0;
      width: var(--sidebar-w);
      display: flex;
      flex-direction: column;
      gap: 4px;
      /* The player bar starts right of the sidebar, so nothing to clear at the bottom. */
      padding: 20px 12px 20px;
      background: var(--surface);
      border-right: 1px solid var(--border);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 800;
      font-size: 1.15rem;
      padding: 0 12px 16px;
      color: var(--accent);
    }
    .sidebar nav {
      display: grid;
      gap: 2px;
    }
    .sidebar a {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      border-radius: 10px;
      color: var(--muted);
      text-decoration: none;
      font-weight: 600;
    }
    .sidebar a:hover {
      background: var(--surface-2);
      color: var(--text);
    }
    .nav-btn {
      display: flex;
      align-items: center;
      gap: 12px;
      width: 100%;
      padding: 10px 12px;
      border-radius: 10px;
      background: none;
      color: var(--muted);
      font-weight: 600;
      text-align: left;
      min-height: 0;
    }
    .nav-btn:hover {
      background: var(--surface-2);
      color: var(--text);
    }
    .nav-btn.active {
      background: var(--accent-soft);
      color: var(--accent);
    }
    .nav-btn .badge {
      margin-left: auto;
    }
    .content.with-queue {
      margin-right: var(--queue-w);
    }
    .sidebar a.active {
      background: var(--accent-soft);
      color: var(--accent);
    }
    .sidebar .badge {
      margin-left: auto;
    }
    .settings-link {
      margin-top: auto;
    }
    .content {
      margin-left: var(--sidebar-w);
      padding: 28px 32px 120px;
    }
  }
</style>
