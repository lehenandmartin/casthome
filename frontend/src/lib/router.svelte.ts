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

class Router {
  hash = $state(location.hash);
  #key: string;
  #positions = new Map<string, number>();
  #restoring = 0;

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
