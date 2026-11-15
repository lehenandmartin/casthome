// "This browser" as a playback device. The server keeps the queue and tells
// this tab what to play (`browser_cmd`); this module plays it in an <audio>
// element and reports its state back, like a Chromecast would.
import { api } from './api';

type Send = (type: string, data: Record<string, unknown>) => void;

interface LoadCommand {
  action: 'load';
  url: string;
  content_type: string;
  metadata: { title?: string; artist?: string; albumName?: string; images?: { url: string }[] };
  start_at: number;
}

type Command =
  | LoadCommand
  | { action: 'play' | 'pause' | 'stop' | 'status' }
  | { action: 'seek'; position: number }
  | { action: 'volume'; level: number }
  | { action: 'mute'; muted: boolean };

// 0.1 s of silence: playing it inside a user gesture unlocks the element on iOS,
// so later play() calls triggered by the server are allowed.
const SILENT_WAV =
  'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=';

export const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

export class BrowserPlayer {
  readonly audio = new Audio();
  #url: string | null = null; // content id of the media the server loaded
  #unlocked = false;
  #send: Send = () => {};
  #lastPositionReport = 0;

  constructor() {
    this.audio.preload = 'auto';
    const a = this.audio;
    a.addEventListener('playing', () => this.#report('PLAYING'));
    a.addEventListener('pause', () => !a.ended && this.#report('PAUSED'));
    a.addEventListener('waiting', () => this.#report('BUFFERING'));
    a.addEventListener('seeked', () => this.#report(a.paused ? 'PAUSED' : 'PLAYING'));
    a.addEventListener('ended', () => this.#report('IDLE', 'FINISHED'));
    a.addEventListener('error', () => this.#url && this.#report('IDLE', 'ERROR'));
    a.addEventListener('volumechange', () => this.#send('browser_volume', { volume: a.volume, muted: a.muted }));
    a.addEventListener('timeupdate', () => {
      const now = Date.now();
      if (now - this.#lastPositionReport > 5000 && !a.paused) this.#report('PLAYING');
      this.#updatePositionState();
    });

    const unlock = () => this.unlock();
    document.addEventListener('pointerdown', unlock, { capture: true });
    document.addEventListener('keydown', unlock, { capture: true });
    this.#setupMediaSession();
  }

  connect(send: Send): void {
    this.#send = send;
  }

  get active(): boolean {
    return this.#url !== null;
  }

  /** Must run inside a user gesture (called on the first tap). */
  unlock(): void {
    if (this.#unlocked || this.#url) return;
    this.#unlocked = true;
    const a = this.audio;
    a.src = SILENT_WAV;
    a.play()
      .then(() => {
        if (!this.#url) a.pause();
      })
      .catch(() => (this.#unlocked = false));
  }

  /** Tell the server this tab is not playing anything (e.g. after a reload). */
  reportIdle(): void {
    this.#send('browser_status', { player_state: 'IDLE', idle_reason: 'CANCELLED', content_id: null });
  }

  handle(cmd: Command): void {
    const a = this.audio;
    switch (cmd.action) {
      case 'load': {
        this.#url = cmd.url;
        a.src = cmd.url;
        if (cmd.start_at > 0) {
          a.addEventListener('loadedmetadata', () => (a.currentTime = cmd.start_at), { once: true });
        }
        this.#setMetadata(cmd.metadata);
        this.#play();
        break;
      }
      case 'play':
        this.#play();
        break;
      case 'pause':
        a.pause();
        break;
      case 'stop':
        this.#url = null;
        a.pause();
        a.removeAttribute('src');
        a.load();
        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'none';
        break;
      case 'seek':
        a.currentTime = cmd.position;
        break;
      case 'volume':
        a.volume = cmd.level;
        break;
      case 'mute':
        a.muted = cmd.muted;
        break;
      case 'status':
        if (this.#url) this.#report(a.ended ? 'IDLE' : a.paused ? 'PAUSED' : 'PLAYING', a.ended ? 'FINISHED' : undefined);
        break;
    }
  }

  #play(): void {
    this.audio.play().catch((err: DOMException) => {
      // Autoplay refused (no user gesture yet): report paused; a tap on Play resumes.
      if (err.name === 'NotAllowedError') this.#report('PAUSED');
    });
  }

  #report(state: string, reason?: string): void {
    if (!this.#url) return;
    const a = this.audio;
    this.#lastPositionReport = Date.now();
    this.#send('browser_status', {
      player_state: state,
      idle_reason: reason ?? null,
      content_id: this.#url,
      current_time: a.currentTime || 0,
      duration: Number.isFinite(a.duration) ? a.duration : null,
    });
    if ('mediaSession' in navigator) {
      navigator.mediaSession.playbackState = state === 'PLAYING' ? 'playing' : state === 'IDLE' ? 'none' : 'paused';
    }
  }

  #setMetadata(meta: LoadCommand['metadata']): void {
    if (!('mediaSession' in navigator)) return;
    // iOS may drop the controls when the track changes: declare them again.
    this.#setupMediaSession();
    navigator.mediaSession.metadata = new MediaMetadata({
      title: meta.title ?? '',
      artist: meta.artist ?? '',
      album: meta.albumName ?? '',
      artwork: (meta.images ?? []).map((img) => ({ src: img.url, sizes: '600x600' })),
    });
  }

  #updatePositionState(): void {
    const a = this.audio;
    if (!('mediaSession' in navigator) || !Number.isFinite(a.duration) || !a.duration) return;
    try {
      navigator.mediaSession.setPositionState({ duration: a.duration, position: Math.min(a.currentTime, a.duration), playbackRate: 1 });
    } catch {
      /* some browsers reject transient values */
    }
  }

  // Lock-screen / headset controls go through the server like every other command.
  #setupMediaSession(): void {
    if (!('mediaSession' in navigator)) return;
    const session = navigator.mediaSession;
    const safe = (fn: () => Promise<unknown>) => () => void fn().catch(() => {});
    session.setActionHandler('play', safe(() => api.action('play')));
    session.setActionHandler('pause', safe(() => api.action('pause')));
    session.setActionHandler('nexttrack', safe(() => api.action('next')));
    session.setActionHandler('previoustrack', safe(() => api.action('previous')));
    // Safari adds its own ±10 s buttons to any audio player (lock screen,
    // Dynamic Island) unless they are removed: show previous/next instead.
    for (const action of ['seekbackward', 'seekforward'] as const) {
      try {
        session.setActionHandler(action, null);
      } catch {
        /* unsupported action */
      }
    }
    try {
      session.setActionHandler('seekto', (details) => {
        if (details.seekTime !== undefined) void api.seek(details.seekTime).catch(() => {});
      });
    } catch {
      /* seekto unsupported */
    }
  }
}

export const browserPlayer = new BrowserPlayer();
