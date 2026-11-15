// Client-side routing on the URL hash (#/albums, #/album/<id>, ...).
//
// Internal links are intercepted and applied with history.pushState instead of
// letting the browser follow them: installed iOS web apps may otherwise reload
// the whole page on a link tap, which drops the live connection and flashes
// an empty player.

//
// Scroll: each history entry remembers where the page was scrolled, and Back
// or Forward returns there (pages render from memory, see cache.ts, so the
// content is usually there at once).

import { tick } from 'svelte';

const newKey = () => Math.random().toString(36).slice(2);
const RESTORE_TIMEOUT_MS = 1500;
// A page just opened stays at the top (see #pinTop): wheel events closer than
// FLICK_GAP_MS belong to the same flick; the pin ends SETTLE_MS after the last
// of them (or the opening), and never lasts longer than PIN_MAX_MS.
const FLICK_GAP_MS = 120;
const SETTLE_MS = 400;
const PIN_MAX_MS = 3000;

class Router {
  hash = $state(location.hash);
  #key: string;
  #positions = new Map<string, number>();
  #restoring = 0;
  #lastWheel = 0;

  constructor() {
    history.scrollRestoration = 'manual';
    this.#key = (history.state as { key?: string } | null)?.key ?? newKey();
    history.replaceState({ ...(history.state ?? {}), key: this.#key }, '');

    const sync = () => {
      this.hash = location.hash;
    };
    window.addEventListener('popstate', (event) => {
      sync();
      const key = (event.state as { key?: string } | null)?.key;
      // Entries made outside the router (none expected), and opening or closing
      // Now Playing or the queue (same key): no scroll change.
      if (!key || key === this.#key) return;
      this.#key = key;
      this.#restore(this.#positions.get(key) ?? 0);
    });
    window.addEventListener('hashchange', sync);
    document.addEventListener('click', (event) => this.#intercept(event));

    let frame = 0;
    window.addEventListener(
      'scroll',
      () => {
        if (frame) return;
        frame = requestAnimationFrame(() => {
          frame = 0;
          this.#positions.set(this.#key, window.scrollY);
        });
      },
      { passive: true },
    );
    window.addEventListener('wheel', (e) => (this.#lastWheel = e.timeStamp), { passive: true });
    // The user scrolling takes over from a restore still waiting for content.
    const stop = () => cancelAnimationFrame(this.#restoring);
    for (const type of ['wheel', 'touchstart', 'keydown']) window.addEventListener(type, stop, { passive: true });
  }

  /** Scroll back to `y` as soon as the page is tall enough (or after a time limit). */
  #restore(y: number): void {
    cancelAnimationFrame(this.#restoring);
    const started = performance.now();
    const attempt = () => {
      const room = document.documentElement.scrollHeight - window.innerHeight;
      if (room >= y - 2 || performance.now() - started > RESTORE_TIMEOUT_MS) {
        window.scrollTo(0, Math.min(y, Math.max(0, room)));
        return;
      }
      this.#restoring = requestAnimationFrame(attempt);
    };
    this.#restoring = requestAnimationFrame(attempt);
  }

  /** Go to an internal route such as "#/album/123". */
  navigate(href: string, { replace = false }: { replace?: boolean } = {}): void {
    if (href === location.hash && !replace) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    cancelAnimationFrame(this.#restoring);
    this.#positions.set(this.#key, window.scrollY);
    this.#key = newKey();
    if (replace) history.replaceState({ key: this.#key }, '', href);
    else history.pushState({ key: this.#key }, '', href);
    this.hash = location.hash;
    // Scroll up once the new page is in place (scrolling the old one could show its top).
    tick().then(() => window.scrollTo(0, 0));
    this.#pinTop();
  }

  /** Keep a page just opened at the top while the old page's scroll dies out.
   *  Firefox animates each wheel notch smoothly, and that animation went on
   *  after the link was followed, without any event, towards the old page's
   *  position: the new page (still short while it loads) ended up scrolled
   *  to its bottom, and Firefox showed an unpainted band there. A trackpad
   *  flick does the same with its tail of wheel events, which are cancelled.
   *  Any new gesture (a wheel after a pause, a touch, a key, a click) ends it. */
  #pinTop(): void {
    const opened = performance.now();
    // Event times are when each event was made: while the new page is being
    // built, the flick's events wait and then arrive all at once.
    let lastFlick = opened - this.#lastWheel <= FLICK_GAP_MS ? this.#lastWheel : opened;
    const top = () => {
      if (window.scrollY !== 0) window.scrollTo({ top: 0, behavior: 'instant' });
    };
    const onWheel = (event: WheelEvent) => {
      if (event.timeStamp - lastFlick > FLICK_GAP_MS) return release(); // a new gesture
      lastFlick = event.timeStamp;
      event.preventDefault();
      top();
    };
    const timer = setInterval(() => {
      const now = performance.now();
      if (now - lastFlick > SETTLE_MS || now - opened > PIN_MAX_MS) release();
    }, 100);
    const release = () => {
      clearInterval(timer);
      window.removeEventListener('wheel', onWheel);
      window.removeEventListener('scroll', top);
      for (const type of ['touchstart', 'keydown', 'pointerdown']) window.removeEventListener(type, release);
    };
    // Not passive, so a flick's events can be cancelled (only while pinned).
    window.addEventListener('wheel', onWheel, { passive: false });
    window.addEventListener('scroll', top, { passive: true });
    for (const type of ['touchstart', 'keydown', 'pointerdown']) window.addEventListener(type, release, { passive: true });
  }

  #intercept(event: MouseEvent): void {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    const link = (event.target as Element | null)?.closest?.('a');
    const href = link?.getAttribute('href');
    if (!link || !href || !href.startsWith('#') || link.target) return;
    event.preventDefault();
    this.navigate(href === '#' ? '#/' : href);
  }
}

export const router = new Router();
