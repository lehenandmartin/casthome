// `use:modal` on a dialog (aria-modal): keyboard focus goes into it when it
// opens, Tab and Shift+Tab stay inside it, and focus goes back to where it was
// (usually the button that opened it) when it closes. Dialogs can stack (the
// queue sheet over Now Playing, the device picker over both): only the top one
// keeps the focus.

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

const stack: HTMLElement[] = [];

function focusables(node: HTMLElement): HTMLElement[] {
  return [...node.querySelectorAll<HTMLElement>(FOCUSABLE)].filter(
    (el) => el.getClientRects().length > 0 && !el.closest('[inert], [aria-hidden="true"]'),
  );
}

interface Options {
  /** Move the focus into the dialog on open (false when it picks its own field). */
  autofocus?: boolean;
}

export function modal(node: HTMLElement, options: Options = {}) {
  const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  stack.push(node);

  if (options.autofocus !== false) {
    // After the dialog's content has rendered.
    queueMicrotask(() => {
      if (node.contains(document.activeElement)) return;
      const first = focusables(node)[0];
      if (first) first.focus({ preventScroll: true });
      else {
        if (!node.hasAttribute('tabindex')) node.tabIndex = -1;
        node.focus({ preventScroll: true });
      }
    });
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key !== 'Tab' || stack[stack.length - 1] !== node) return;
    const items = focusables(node);
    if (items.length === 0) {
      e.preventDefault();
      return;
    }
    const first = items[0];
    const last = items[items.length - 1];
    const active = document.activeElement;
    if (e.shiftKey && (active === first || !node.contains(active))) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && (active === last || !node.contains(active))) {
      e.preventDefault();
      first.focus();
    }
  }
  document.addEventListener('keydown', onKeydown);

  return {
    destroy() {
      document.removeEventListener('keydown', onKeydown);
      const at = stack.indexOf(node);
      if (at >= 0) stack.splice(at, 1);
      // Back to where the focus was, unless it has moved on to something else.
      const lost = !document.activeElement || document.activeElement === document.body || node.contains(document.activeElement);
      if (lost && opener?.isConnected) opener.focus({ preventScroll: true });
    },
  };
}
