import { describe, expect, it } from 'vitest';
import { en } from './en';
import { fr } from './fr';

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe('translations', () => {
  it('French has every English key, and no other', () => {
    expect(Object.keys(fr).sort()).toEqual(Object.keys(en).sort());
  });

  it('each French text uses the same {placeholders} as the English one', () => {
    const en_ = en as Record<string, string>;
    const fr_ = fr as Record<string, string>;
    const wrong = Object.keys(en_).filter((key) => placeholders(en_[key]).join() !== placeholders(fr_[key] ?? '').join());
    expect(wrong).toEqual([]);
  });
});
