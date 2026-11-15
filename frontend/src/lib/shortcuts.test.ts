import { describe, expect, it } from 'vitest';
import { isTextEntry, shortcutFor } from './shortcuts';

const el = (tagName: string, extra: Record<string, unknown> = {}) => ({ tagName, closest: () => null, ...extra });
const key = (k: string, extra: Record<string, unknown> = {}) => ({
  key: k,
  ctrlKey: false,
  metaKey: false,
  altKey: false,
  repeat: false,
  defaultPrevented: false,
  target: el('BODY') as unknown as EventTarget,
  ...extra,
});

describe('shortcutFor', () => {
  it('Space plays/pauses, / searches', () => {
    expect(shortcutFor(key(' '))).toBe('toggle');
    expect(shortcutFor(key('/'))).toBe('search');
    expect(shortcutFor(key('/', { target: el('BUTTON') }))).toBe('search');
  });

  it('+ and − set the volume, held down too; Ctrl/Cmd +/− stay the browser zoom', () => {
    expect(shortcutFor(key('+'))).toBe('volumeUp');
    expect(shortcutFor(key('='))).toBe('volumeUp');
    expect(shortcutFor(key('-'))).toBe('volumeDown');
    expect(shortcutFor(key('-', { repeat: true }))).toBe('volumeDown');
    expect(shortcutFor(key('+', { ctrlKey: true }))).toBeNull();
    expect(shortcutFor(key('-', { metaKey: true }))).toBeNull();
    expect(shortcutFor(key('-', { target: el('INPUT', { type: 'text' }) }))).toBeNull();
  });

  it('leaves other keys alone, the arrows included', () => {
    for (const k of ['ArrowRight', 'ArrowLeft', 'k', 'Enter']) expect(shortcutFor(key(k))).toBeNull();
  });

  it('not while typing, with a modifier, held down or already handled', () => {
    expect(shortcutFor(key(' ', { target: el('INPUT', { type: 'search' }) }))).toBeNull();
    expect(shortcutFor(key('/', { target: el('TEXTAREA') }))).toBeNull();
    expect(shortcutFor(key('/', { ctrlKey: true }))).toBeNull();
    expect(shortcutFor(key(' ', { metaKey: true }))).toBeNull();
    expect(shortcutFor(key(' ', { repeat: true }))).toBeNull();
    expect(shortcutFor(key(' ', { defaultPrevented: true }))).toBeNull();
  });

  it('not inside an open action menu', () => {
    expect(shortcutFor(key(' ', { target: el('BUTTON', { closest: () => ({}) }) }))).toBeNull();
  });

  it('Space plays/pauses on a slider or a button, but ticks a checkbox', () => {
    expect(shortcutFor(key(' ', { target: el('INPUT', { type: 'range' }) }))).toBe('toggle');
    expect(shortcutFor(key(' ', { target: el('BUTTON') }))).toBe('toggle');
    expect(shortcutFor(key(' ', { target: el('INPUT', { type: 'checkbox' }) }))).toBeNull();
    expect(isTextEntry(el('INPUT', { type: 'checkbox' }) as unknown as EventTarget)).toBe(false);
    expect(isTextEntry(el('DIV', { isContentEditable: true }) as unknown as EventTarget)).toBe(true);
  });
});
