// Client-side routing on the URL hash (#/albums, #/album/<id>, ...).
//
// Internal links are intercepted and applied with history.pushState instead of
// letting the browser follow them: installed iOS web apps may otherwise reload
// the whole page on a link tap, which drops the live connection and flashes
// an empty player.

class Router {
  hash = $state(location.hash);

  constructor() {
    const sync = () => {
      this.hash = location.hash;
    };
    window.addEventListener('popstate', sync);
    window.addEventListener('hashchange', sync);
    document.addEventListener('click', (event) => this.#intercept(event));
  }

  /** Go to an internal route such as "#/album/123". */
  navigate(href: string, { replace = false }: { replace?: boolean } = {}): void {
    if (href === location.hash && !replace) {
      window.scrollTo(0, 0);
      return;
    }
    if (replace) history.replaceState(null, '', href);
    else history.pushState(null, '', href);
    this.hash = location.hash;
    window.scrollTo(0, 0);
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
