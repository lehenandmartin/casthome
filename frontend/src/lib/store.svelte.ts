import { ApiError, api, setBeforePlayHook, setUnauthorizedHandler } from './api';
import { browserPlayer } from './browserPlayer';
import type { AppStatus, Device, Me, Notification, PlayerState, QueueState } from './types';
import { describeUserAgent } from './useragent';
import { setShowRatings } from './display.svelte';


// Last known state, shown instantly when the app (re)starts so a reload never
// flashes an empty player. Only a per-device convenience: the server's
// snapshot replaces it as soon as the live connection opens.
const CACHE_KEY = 'casthome.snapshot';
interface Cached {
  player: PlayerState | null;
  queue: QueueState;
  devices: Device[];
  savedAt: number;
}

function readCache(): Cached | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as Cached) : null;
  } catch {
    return null;
  }
}

const DESKTOP_QUERY = '(min-width: 900px)';
const QUEUE_PANEL_KEY = 'casthome.queuePanel';

function readFlag(key: string): boolean {
  try {
    return localStorage.getItem(key) === '1';
  } catch {
    return false;
  }
}

// One id per tab, kept across reloads of that tab.
function tabId(): string {
  try {
    const existing = sessionStorage.getItem('casthome.tab');
    if (existing) return existing;
    const id = crypto.randomUUID?.() ?? Math.random().toString(36).slice(2);
    sessionStorage.setItem('casthome.tab', id);
    return id;
  } catch {
    return Math.random().toString(36).slice(2);
  }
}

type AuthState = 'unknown' | 'setup' | 'signed-out' | 'signed-in';

class AppStore {
  auth = $state<AuthState>('unknown');
  /** Who is signed in and how (set once signed in). */
  me = $state<Me | null>(null);
  /** Navidrome refused the saved password: ask to update it in Settings. */
  navidromeRejected = $state(false);
  online = $state(false);
  /** True only after the live connection has been down for a while. */
  offlineNotice = $state(false);
  player = $state<PlayerState | null>(null);
  queue = $state<QueueState>({ version: 0, index: null, items: [] });
  devices = $state<Device[]>([]);
  notifications = $state<Notification[]>([]);
  /** Local clock (seconds) when the last player snapshot arrived. */
  receivedAt = $state(0);
  now = $state(Date.now() / 1000);
  /** UI state shared by several components. */
  nowPlayingOpen = $state(false);
  devicePickerOpen = $state(false);
  /** Mobile: the queue sheet over the page / Now Playing (part of Back history). */
  queueOpen = $state(false);
  /** Desktop: the queue side panel, remembered on the device. */
  queuePanel = $state(readFlag(QUEUE_PANEL_KEY));
  /** Same breakpoint as the CSS: sidebar + side panel layout. */
  isDesktop = $state(window.matchMedia(DESKTOP_QUERY).matches);

  readonly clientId = tabId();
  readonly browserUuid = `browser:${this.clientId}`;
  readonly browserName = describeUserAgent(navigator.userAgent);

  #ws: WebSocket | null = null;
  #retry = 0;
  #nextId = 1;
  #pingTimer: ReturnType<typeof setInterval> | undefined;
  #offlineTimer: ReturnType<typeof setTimeout> | undefined;
  #cacheTimer: ReturnType<typeof setTimeout> | undefined;

  constructor() {
    const cached = readCache();
    if (cached) {
      // Optimistic: render right away; /status confirms or signs out.
      this.auth = 'signed-in';
      this.player = cached.player;
      this.queue = cached.queue;
      this.devices = cached.devices;
      this.receivedAt = cached.savedAt;
    }
    setUnauthorizedHandler(() => void this.checkStatus());
    setBeforePlayHook(() => this.#ensureDevice());
    // Moves the position on between server messages: only while playing and
    // while the app is on screen (no need to wake the phone otherwise).
    const tick = () => {
      if (!document.hidden && this.player?.status === 'playing') this.now = Date.now() / 1000;
    };
    setInterval(tick, 500);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) this.now = Date.now() / 1000;
    });
    browserPlayer.connect((type, data) => this.send(type, data));
    // Back button / swipe-back closes the Now Playing sheet.
    // Back button / swipe-back closes the queue sheet, then the Now Playing view.
    window.addEventListener('popstate', () => {
      this.nowPlayingOpen = Boolean(history.state?.nowPlaying);
      this.queueOpen = Boolean(history.state?.queue);
    });
    window.matchMedia(DESKTOP_QUERY).addEventListener('change', (e) => (this.isDesktop = e.matches));
  }

  /** True when this tab is the playback device. */
  get isThisBrowser(): boolean {
    return this.player?.device_uuid === this.browserUuid;
  }

  openNowPlaying(): void {
    if (this.nowPlayingOpen) return;
    history.pushState({ ...(history.state ?? {}), nowPlaying: true }, '');
    this.nowPlayingOpen = true;
  }

  closeNowPlaying(): void {
    if (!this.nowPlayingOpen) return;
    if (history.state?.nowPlaying) history.back();
    else this.nowPlayingOpen = false;
  }

  /** Is the queue visible (sheet on mobile, side panel on desktop)? */
  get queueVisible(): boolean {
    return this.isDesktop ? this.queuePanel : this.queueOpen;
  }

  openQueue(): void {
    if (this.isDesktop) {
      // Desktop: the side panel sits next to the page, so leave Now Playing for it.
      this.#setQueuePanel(true);
      this.closeNowPlaying();
      return;
    }
    if (this.queueOpen) return;
    // Stacked on top of whatever is shown (e.g. Now Playing): Back returns to it.
    history.pushState({ ...(history.state ?? {}), queue: true }, '');
    this.queueOpen = true;
  }

  closeQueue(): void {
    if (this.isDesktop) {
      this.#setQueuePanel(false);
      return;
    }
    if (!this.queueOpen) return;
    if (history.state?.queue) history.back();
    else this.queueOpen = false;
  }

  toggleQueue(): void {
    if (this.queueVisible) this.closeQueue();
    else this.openQueue();
  }

  #setQueuePanel(open: boolean): void {
    this.queuePanel = open;
    try {
      localStorage.setItem(QUEUE_PANEL_KEY, open ? '1' : '0');
    } catch {
      /* ignore */
    }
  }

  send(type: string, data: Record<string, unknown>): void {
    if (this.#ws?.readyState === WebSocket.OPEN) this.#ws.send(JSON.stringify({ type, data }));
  }

  async #ensureDevice(): Promise<void> {
    if (this.player && !this.player.device_uuid) {
      await api.selectDevice(this.browserUuid);
    }
  }

  /** Current position, interpolated locally while playing. */
  get position(): number {
    const p = this.player;
    if (!p) return 0;
    if (p.status !== 'playing') return p.position;
    const pos = p.position + Math.max(0, this.now - this.receivedAt);
    return p.duration ? Math.min(pos, p.duration) : pos;
  }

  #statusCheck: Promise<void> | null = null;

  /** Ask the server what to show: setup, sign-in or the app. */
  checkStatus(): Promise<void> {
    this.#statusCheck ??= this.#checkStatus().finally(() => (this.#statusCheck = null));
    return this.#statusCheck;
  }

  async #checkStatus(): Promise<void> {
    let status: AppStatus;
    try {
      status = await api.status();
    } catch {
      // Server briefly unreachable: keep the cached state and let the live connection retry.
      if (this.auth !== 'signed-in') this.signedIn();
      return;
    }
    // `setup.access`: no access rule yet, so the setup is open to this browser.
    if (status.setup_required && (status.setup.access || status.signed_in)) this.#enterSetup();
    else if (status.signed_in && !status.setup_required) this.signedIn();
    else this.signedOut();
  }

  signedIn(): void {
    this.auth = 'signed-in';
    this.connect();
    api
      .me()
      .then((me) => {
        this.me = me;
        setShowRatings(me.show_ratings ?? true);
      })
      .catch(() => {});
  }

  #enterSetup(): void {
    this.signedOut();
    this.auth = 'setup';
  }

  #saveCache(): void {
    clearTimeout(this.#cacheTimer);
    this.#cacheTimer = setTimeout(() => {
      try {
        const data: Cached = {
          player: $state.snapshot(this.player),
          queue: $state.snapshot(this.queue),
          devices: $state.snapshot(this.devices),
          savedAt: this.receivedAt || Date.now() / 1000,
        };
        localStorage.setItem(CACHE_KEY, JSON.stringify(data));
      } catch {
        /* storage full or unavailable */
      }
    }, 500);
  }

  signedOut(): void {
    this.auth = 'signed-out';
    this.me = null;
    this.offlineNotice = false;
    clearTimeout(this.#cacheTimer);
    try {
      localStorage.removeItem(CACHE_KEY);
    } catch {
      /* ignore */
    }
    clearTimeout(this.#offlineTimer);
    this.#ws?.close();
    this.#ws = null;
    this.player = null;
  }

  connect(): void {
    if (this.#ws) return;
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const params = new URLSearchParams({ client: this.clientId, name: this.browserName });
    const ws = new WebSocket(`${proto}://${location.host}/api/ws?${params}`);
    this.#ws = ws;
    this.#armOfflineNotice();
    ws.onopen = () => {
      this.online = true;
      clearTimeout(this.#offlineTimer);
      this.offlineNotice = false;
      this.#retry = 0;
      clearInterval(this.#pingTimer);
      this.#pingTimer = setInterval(() => ws.readyState === WebSocket.OPEN && ws.send('ping'), 25_000);
    };
    ws.onmessage = (event) => this.#handle(JSON.parse(event.data));
    ws.onclose = (event) => {
      clearInterval(this.#pingTimer);
      this.online = false;
      this.#ws = null;
      this.#armOfflineNotice();
      if (event.code === 4401) {
        // Signed out, or the access rules changed: ask what to show now.
        void this.checkStatus();
        return;
      }
      if (this.auth === 'signed-in') {
        const delay = Math.min(30_000, 1000 * 2 ** this.#retry++);
        setTimeout(() => this.connect(), delay);
      }
    };
  }

  // Short drops (app start, a reconnect, the phone waking up) are normal:
  // only tell the user when the connection stays down.
  #armOfflineNotice(): void {
    clearTimeout(this.#offlineTimer);
    this.#offlineTimer = setTimeout(() => {
      if (!this.online && this.auth === 'signed-in') this.offlineNotice = true;
    }, 3000);
  }

  #handle(msg: { type: string; data: any }): void {
    if (msg.type === 'hello' || msg.type === 'player' || msg.type === 'queue' || msg.type === 'devices') {
      queueMicrotask(() => this.#saveCache());
    }
    switch (msg.type) {
      case 'hello':
        this.devices = msg.data.devices;
        this.queue = msg.data.queue;
        this.#setPlayer(msg.data.player);
        this.navidromeRejected = Boolean(msg.data.server?.navidrome_rejected);
        // After a reload the server may still think this tab is playing.
        if (this.isThisBrowser && !browserPlayer.active) browserPlayer.reportIdle();
        break;
      case 'browser_cmd':
        browserPlayer.handle(msg.data);
        break;
      case 'player':
        this.#setPlayer(msg.data);
        break;
      case 'queue':
        this.queue = msg.data;
        break;
      case 'devices':
        this.devices = msg.data;
        break;
      case 'server':
        this.navidromeRejected = Boolean(msg.data.navidrome_rejected);
        break;
      case 'notification':
        this.notify(msg.data.code, msg.data.params, msg.data.level);
        break;
      case 'auth_expired':
        this.notify(msg.data.reason ?? 'not_signed_in', {}, 'warning');
        this.signedOut();
        break;
    }
  }

  #setPlayer(player: PlayerState): void {
    this.player = player;
    this.receivedAt = Date.now() / 1000;
    this.now = this.receivedAt;
    // Moving to another track only sends a player update: keep the queue's
    // current index in step (same queue version only).
    if (player.queue_version === this.queue.version && player.index !== this.queue.index) {
      this.queue = { ...this.queue, index: player.index };
    }
  }

  notify(code: string, params: Record<string, unknown> = {}, level: Notification['level'] = 'error'): void {
    const id = this.#nextId++;
    this.notifications = [...this.notifications, { id, code, params, level }];
    setTimeout(() => this.dismiss(id), 5000);
  }

  dismiss(id: number): void {
    this.notifications = this.notifications.filter((n) => n.id !== id);
  }

  /** Run an API call and turn failures into a toast. */
  async run(call: () => Promise<unknown>): Promise<void> {
    try {
      await call();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status !== 401) this.notify(err.code, err.params);
      } else {
        this.notify('navidrome_unavailable');
      }
    }
  }
}

export const store = new AppStore();
