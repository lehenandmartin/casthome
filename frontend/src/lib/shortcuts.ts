// Keyboard shortcuts:
//   Space  play / pause
//   /      search
//   + / −  volume up / down (also = , the + key without Shift, and the keypad)
// Never while typing in a field, nor with Ctrl/Cmd/Alt held (the browser's own
// shortcuts), nor inside an open action menu (Space picks its item there).

export type Shortcut = 'toggle' | 'search' | 'volumeUp' | 'volumeDown';

interface KeyLike {
  key: string;
  ctrlKey: boolean;
  metaKey: boolean;
  altKey: boolean;
  repeat: boolean;
  defaultPrevented: boolean;
  target: EventTarget | null;
}

interface ElementLike {
  tagName?: string;
  type?: string;
  isContentEditable?: boolean;
  closest?: (selector: string) => unknown;
}

// Inputs where a key does nothing but move a value: Space still plays/pauses.
const NOT_TEXT = new Set(['range', 'checkbox', 'radio', 'button', 'submit', 'reset', 'color', 'file']);

/** Is the key going into a text field (input, textarea, select, editable)? */
export function isTextEntry(target: EventTarget | null): boolean {
  const el = target as ElementLike | null;
  if (!el?.tagName) return false;
  const tag = el.tagName.toUpperCase();
  if (tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable) return true;
  return tag === 'INPUT' && !NOT_TEXT.has((el.type ?? 'text').toLowerCase());
}

export function shortcutFor(e: KeyLike): Shortcut | null {
  if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || isTextEntry(e.target)) return null;
  if ((e.target as ElementLike | null)?.closest?.('[role="menu"]')) return null;
  if (e.key === ' ') {
    const el = e.target as ElementLike | null;
    const ticks = el?.tagName?.toUpperCase() === 'INPUT' && (el.type === 'checkbox' || el.type === 'radio');
    return e.repeat || ticks ? null : 'toggle';
  }
  if (e.key === '/') return 'search';
  // Held down, the volume keeps moving.
  if (e.key === '+' || e.key === '=') return 'volumeUp';
  if (e.key === '-' || e.key === '−') return 'volumeDown';
  return null;
}
