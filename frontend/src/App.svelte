<script lang="ts">
  import { t } from './lib/i18n';
  import type { IconName } from './lib/icons';
  import type { MessageKey } from './lib/i18n/en';
  import type { AlbumListType } from './lib/types';
  import { router } from './lib/router.svelte';
  import { contextMenu } from './lib/contextMenu.svelte';
  import { dialogs } from './lib/dialog.svelte';
  import { togglePlayback } from './lib/playback.svelte';
  import { shortcutFor } from './lib/shortcuts';
  import { stepVolume, volumeAvailable } from './lib/volume.svelte';
  import { store } from './lib/store.svelte';
  import AlbumView from './components/AlbumView.svelte';
  import Albums from './components/Albums.svelte';
  import ArtistView from './components/ArtistView.svelte';
  import Artists from './components/Artists.svelte';
  import DevicePicker from './components/DevicePicker.svelte';
  import ContextMenu from './components/ContextMenu.svelte';
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
  import Setup from './components/Setup.svelte';
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
  // #/tracks?artist=<id>&name=<name>: one artist's tracks (from the artist page).
  const tracksArtist = $derived(query.get('artist'));
  const tracksArtistName = $derived(query.get('name') ?? '');

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

  // Full-screen overlays freeze the page behind them (no scrollbar moving under them).
  $effect(() => {
    const locked = store.nowPlayingOpen || (store.queueVisible && !store.isDesktop) || store.devicePickerOpen;
    document.documentElement.classList.toggle('locked', locked);
  });

  // A link followed from Now Playing or the queue sheet (a song's menu, "Go to
  // album"...) opens a page: the overlay leaves with it instead of staying on top.
  // Back still returns to it, as its history entry is kept.
  $effect(() => {
    void hash;
    const state = history.state as { nowPlaying?: boolean; queue?: boolean } | null;
    if (store.nowPlayingOpen && !state?.nowPlaying) store.nowPlayingOpen = false;
    if (store.queueOpen && !state?.queue) store.queueOpen = false;
  });

  // On load: first-run setup, sign-in, or the app. If the server is briefly
  // unreachable, the cached state stays on screen while the connection retries.
  store.checkStatus();

  // Keyboard shortcuts (see lib/shortcuts.ts): Space plays/pauses, / searches, +/− volume.
  function onShortcut(e: KeyboardEvent) {
    // Not behind a confirmation or an action menu: Space belongs to their buttons.
    if (store.auth !== 'signed-in' || dialogs.current || contextMenu.current) return;
    const shortcut = shortcutFor(e);
    if (!shortcut) return;
    if ((shortcut === 'volumeUp' || shortcut === 'volumeDown') && !volumeAvailable()) return;
    e.preventDefault();
    if (shortcut === 'volumeUp' || shortcut === 'volumeDown') {
      stepVolume(shortcut === 'volumeUp' ? 1 : -1);
      return;
    } // no page scroll, no button click, no "/" typed
    if (shortcut === 'toggle') {
      if (store.queue.items.length > 0) togglePlayback();
      return;
    }
    const search = () => {
      if (route.name === 'search') {
        const input = document.querySelector<HTMLInputElement>('main input[type="search"]');
        input?.focus();
        input?.select();
      } else {
        location.hash = '#/search';
      }
    };
    // After Now Playing has closed (a history "back"), or that back would undo the change of page.
    if (store.nowPlayingOpen) store.closeNowPlaying().then(search);
    else search();
  }
</script>

<svelte:window onkeydown={onShortcut} />

<Toasts />
<ContextMenu />
<Dialog />
<!-- Installed iOS app: the status bar is translucent; keep scrolled content from showing through it. -->
<div class="statusbar-bg" aria-hidden="true"></div>

{#if store.auth === 'setup'}
  <Setup />
{:else if store.auth === 'signed-out'}
  <Login />
{:else if store.auth === 'signed-in'}
  <!-- Hash routing: a "#main" link would change the page, so this moves the focus itself. -->
  <button class="skip-link" onclick={() => document.getElementById('main')?.focus()}>{t('nav.skip')}</button>
  <aside class="sidebar">
    <div class="brand"><Icon name="cast" size={24} />{t('app.name')}</div>
    <nav>
      {#each SIDEBAR.filter((i) => i.name !== 'tracks' || store.capabilities.all_tracks) as item (item.name)}
        <a href={item.href} class:active={section === item.name}>
          <Icon name={item.icon} size={20} />{t(item.label)}
        </a>
      {/each}
      <!-- The queue is a panel next to the page, not a page. -->
      <button class="nav-btn" class:active={store.queuePanel} aria-pressed={store.queuePanel} onclick={() => store.toggleQueue()}>
        <Icon name="queue" size={20} />{t('nav.queue')}
        {#if upcoming > 0}<span class="badge figures">{upcoming}</span>{/if}
      </button>
    </nav>
    <a class="settings-link" href="#/settings" class:active={section === 'settings'}>
      <Icon name="settings" size={20} />{t('nav.settings')}
    </a>
  </aside>

  <main id="main" tabindex="-1" class="content" class:with-queue={store.isDesktop && store.queuePanel}>
    {#if store.navidromeRejected && route.name !== 'settings'}
      <div class="banner" role="alert">
        <span>{t('navidrome.rejected')}</span>
        <a href="#/settings">{t('navidrome.rejectedLink')}</a>
      </div>
    {/if}
    <!-- Each page fades in when the route changes (app.css: .page). -->
    {#key hash}
      <div class="page">
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
          <Tracks fav={favOnly || !store.capabilities.all_tracks} artist={tracksArtist} artistName={tracksArtistName} />
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
      </div>
    {/key}
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

  .banner {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px 16px;
    margin-bottom: 20px;
    padding: 12px 16px;
    border-radius: 10px;
    border: 1px solid var(--danger);
    color: var(--text);
    background: var(--surface);
  }
  .banner a {
    color: var(--accent);
    font-weight: 600;
    white-space: nowrap;
  }

  /* A count, not an alert: quiet text that follows the row colour. */
  .badge {
    font-size: var(--text-xs);
    font-variant-numeric: tabular-nums;
    opacity: 0.75;
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
    font-size: var(--text-xs);
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
      gap: 8px;
      font-weight: 600;
      font-size: var(--text-lg);
      padding: 0 12px 16px;
      color: var(--text);
    }
    /* The name in the text colour, the Cast mark lit like the amp's power light. */
    .brand :global(svg) {
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
      padding: 8px 12px;
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
      padding: 8px 12px;
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
