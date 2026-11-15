// One action menu for the whole app, rendered by ContextMenu.svelte:
// - from a ⋯ button: a bottom sheet (a centered card on wide screens);
// - from a right-click (mouse or trackpad): a compact menu at the pointer;
// - from a long-press (touch screens): the sheet, like the ⋯ button.
// Shift + right-click keeps the browser's own menu.
import type { IconName } from './icons';

export interface MenuAction {
  label: string;
  icon: IconName;
  /** Run when chosen; the menu closes first. */
  action?: () => unknown;
  /** A link instead of an action. */
  href?: string;
  danger?: boolean;
}

export interface MenuRating {
  id: string;
  value: number;
  onchange: (value: number) => void;
}

export interface MenuSpec {
  title: string;
  subtitle?: string;
  /** Rating stars under the title (tracks and albums). */
  rating?: MenuRating;
  /** Falsy entries are skipped, so items can be written `cond && {...}`. */
  items: (MenuAction | false | null | undefined)[];
}

export interface OpenMenu {
  spec: MenuSpec;
  /** Pointer position for a right-click menu; null for the sheet. */
  at: { x: number; y: number } | null;
  /** The element right-clicked, highlighted while the menu is open. */
  target: HTMLElement | null;
}

const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');

/** The rating is edited in the menu: make it reactive so the stars follow. */
function prepare(spec: MenuSpec): MenuSpec {
  if (!spec.rating) return spec;
  const rating = $state({ ...spec.rating });
  return { ...spec, rating };
}

class ContextMenuStore {
  current = $state.raw<OpenMenu | null>(null);
  /** When the menu opened: the tap that ends a long-press must not close it. */
  openedAt = 0;
  /** Songs waiting for "Add to playlist" (the playlist picker is open). */
  pickerFor = $state.raw<string[] | null>(null);

  /** Open as a sheet (from a ⋯ button). */
  open(spec: MenuSpec, target: HTMLElement | null = null): void {
    this.openedAt = Date.now();
    this.current = { spec: prepare(spec), at: null, target };
  }

  close(): void {
    this.current = null;
  }

  pickPlaylist(songIds: string[]): void {
    this.pickerFor = songIds;
  }

  /**
   * oncontextmenu handler: opens `spec` at the pointer. `spec` is a function so
   * the menu is built only when needed, from the item's current state.
   */
  contextMenu(event: MouseEvent, spec: () => MenuSpec | null): void {
    // From the keyboard (menu key, Shift+F10) the event has no position.
    const fromKeyboard = event.clientX === 0 && event.clientY === 0;
    // Shift + right-click keeps the browser's menu; Shift+F10 still opens ours.
    if ((event.shiftKey && !fromKeyboard) || !finePointer.matches) return;
    const built = spec();
    if (!built) return;
    event.preventDefault();
    event.stopPropagation();
    const target = event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
    let { clientX: x, clientY: y } = event;
    if (fromKeyboard && target) {
      // Next to the element.
      const rect = target.getBoundingClientRect();
      x = rect.left + 24;
      y = Math.min(rect.bottom, window.innerHeight - 8);
    }
    this.openedAt = Date.now();
    this.current = { spec: prepare(built), at: { x, y }, target };
  }
}

export const contextMenu = new ContextMenuStore();

const LONG_PRESS_MS = 500;
/** A finger moving more than this is scrolling or swiping, not pressing. */
const MOVE_TOLERANCE = 10;
/** Presses already taken by an inner element with its own menu. */
const claimed = new WeakSet<Event>();

/**
 * Svelte action: `use:menu={() => spec}` opens that menu on right-click
 * (mouse, trackpad) and on a long-press (touch screens).
 */
export function menu(node: HTMLElement, spec: () => MenuSpec | null) {
  let build = spec;
  let press: { x: number; y: number; id: number } | null = null;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let fired = false;
  let lastTouch = 0;

  // Touch screens: no iOS link preview or text selection under the finger (app.css).
  node.classList.add('has-menu');

  function cancel() {
    clearTimeout(timer);
    timer = undefined;
    press = null;
  }

  function down(event: PointerEvent) {
    if (event.pointerType !== 'touch' || !event.isPrimary || claimed.has(event)) return;
    lastTouch = Date.now();
    // The queue's drag handle has its own long-press (dragging).
    if ((event.target as HTMLElement).closest('[data-no-swipe]')) return;
    claimed.add(event);
    fired = false;
    press = { x: event.clientX, y: event.clientY, id: event.pointerId };
    clearTimeout(timer);
    timer = setTimeout(() => {
      timer = undefined;
      const built = press && build();
      press = null;
      if (!built) return;
      fired = true;
      navigator.vibrate?.(10);
      contextMenu.open(built, node);
    }, LONG_PRESS_MS);
  }

  function move(event: PointerEvent) {
    if (!press || event.pointerId !== press.id) return;
    if (Math.hypot(event.clientX - press.x, event.clientY - press.y) > MOVE_TOLERANCE) cancel();
  }

  function up() {
    cancel();
    // The release after a long-press is not a tap: keep it from playing or opening the item.
    if (fired) setTimeout(() => (fired = false), 400);
  }

  function click(event: MouseEvent) {
    if (!fired) return;
    fired = false;
    event.preventDefault();
    event.stopImmediatePropagation();
  }

  function onContextMenu(event: MouseEvent) {
    // A long-press on a touch screen: handled above; keep the browser's own menu away.
    if (Date.now() - lastTouch < 2000 && !finePointer.matches) {
      event.preventDefault();
      return;
    }
    contextMenu.contextMenu(event, build);
  }

  node.addEventListener('pointerdown', down);
  node.addEventListener('pointermove', move);
  node.addEventListener('pointerup', up);
  node.addEventListener('pointercancel', cancel);
  node.addEventListener('click', click, true);
  node.addEventListener('contextmenu', onContextMenu);
  return {
    update(next: () => MenuSpec | null) {
      build = next;
    },
    destroy() {
      cancel();
      node.removeEventListener('pointerdown', down);
      node.removeEventListener('pointermove', move);
      node.removeEventListener('pointerup', up);
      node.removeEventListener('pointercancel', cancel);
      node.removeEventListener('click', click, true);
      node.removeEventListener('contextmenu', onContextMenu);
    },
  };
}
