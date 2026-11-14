// One action menu for the whole app, rendered by ContextMenu.svelte:
// - from a ⋯ button: a bottom sheet (a centered card on wide screens);
// - from a right-click (mouse or trackpad): a compact menu at the pointer.
// Touch screens never get the right-click menu, so long-press and swipes keep
// working. Shift + right-click keeps the browser's own menu.
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
  /** Songs waiting for "Add to playlist" (the playlist picker is open). */
  pickerFor = $state.raw<string[] | null>(null);

  /** Open as a sheet (from a ⋯ button). */
  open(spec: MenuSpec, target: HTMLElement | null = null): void {
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
    if (event.shiftKey || !finePointer.matches) return;
    const built = spec();
    if (!built) return;
    event.preventDefault();
    event.stopPropagation();
    const target = event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
    let { clientX: x, clientY: y } = event;
    if (x === 0 && y === 0 && target) {
      // Opened from the keyboard (menu key, Shift+F10): next to the element.
      const rect = target.getBoundingClientRect();
      x = rect.left + 24;
      y = Math.min(rect.bottom, window.innerHeight - 8);
    }
    this.current = { spec: prepare(built), at: { x, y }, target };
  }
}

export const contextMenu = new ContextMenuStore();

/** Svelte action: `use:menu={() => spec}` opens that menu on right-click. */
export function menu(node: HTMLElement, spec: () => MenuSpec | null) {
  let build = spec;
  const handler = (event: MouseEvent) => contextMenu.contextMenu(event, build);
  node.addEventListener('contextmenu', handler);
  return {
    update(next: () => MenuSpec | null) {
      build = next;
    },
    destroy() {
      node.removeEventListener('contextmenu', handler);
    },
  };
}
