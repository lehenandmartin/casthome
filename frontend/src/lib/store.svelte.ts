import { ApiError, api, setBeforePlayHook, setUnauthorizedHandler } from './api';
import { browserPlayer } from './browserPlayer';
import type { Device, Notification, PlayerState, QueueState } from './types';
import { describeUserAgent } from './useragent';

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

type AuthState = 'unknown' | 'signed-out' | 'signed-in';

class AppStore {
  auth = $state<AuthState>('unknown');
  online = $state(false);
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

  readonly clientId = tabId();
  readonly browserUuid = `browser:${this.clientId}`;
  readonly browserName = describeUserAgent(navigator.userAgent);

  #ws: WebSocket | null = null;
  #retry = 0;
  #nextId = 1;
  #pingTimer: ReturnType<typeof setInterval> | undefined;

  constructor() {
    setUnauthorizedHandler(() => this.signedOut());
    setBeforePlayHook(() => this.#ensureDevice());
    setInterval(() => (this.now = Date.now() / 1000), 500);
    browserPlayer.connect((type, data) => this.send(type, data));
    // Back button / swipe-back closes the Now Playing sheet.
    window.addEventListener('popstate', () => (this.nowPlayingOpen = Boolean(history.state?.nowPlaying)));
  }

  /** True when this tab is the playback device. */
  get isThisBrowser(): boolean {
    return this.player?.device_uuid === this.browserUuid;
  }

  openNowPlaying(): void {
    if (this.nowPlayingOpen) return;
    history.pushState({ nowPlaying: true }, '');
    this.nowPlayingOpen = true;
  }

  closeNowPlaying(): void {
    if (!this.nowPlayingOpen) return;
    if (history.state?.nowPlaying) history.back();
    else this.nowPlayingOpen = false;
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

  signedIn(): void {
    this.auth = 'signed-in';
    this.connect();
  }

  signedOut(): void {
    this.auth = 'signed-out';
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
    ws.onopen = () => {
      this.online = true;
      this.#retry = 0;
      clearInterval(this.#pingTimer);
      this.#pingTimer = setInterval(() => ws.readyState === WebSocket.OPEN && ws.send('ping'), 25_000);
    };
    ws.onmessage = (event) => this.#handle(JSON.parse(event.data));
    ws.onclose = (event) => {
      clearInterval(this.#pingTimer);
      this.online = false;
      this.#ws = null;
      if (event.code === 4401) {
        this.signedOut();
        return;
      }
      if (this.auth === 'signed-in') {
        const delay = Math.min(30_000, 1000 * 2 ** this.#retry++);
        setTimeout(() => this.connect(), delay);
      }
    };
  }

  #handle(msg: { type: string; data: any }): void {
    switch (msg.type) {
      case 'hello':
        this.devices = msg.data.devices;
        this.queue = msg.data.queue;
        this.#setPlayer(msg.data.player);
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
