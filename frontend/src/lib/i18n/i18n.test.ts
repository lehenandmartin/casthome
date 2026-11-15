import { describe, expect, it } from 'vitest';
import { de } from './de';
import { en } from './en';
import { es } from './es';
import { fr } from './fr';

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
const translations: Record<string, Record<string, string>> = { French: fr, German: de, Spanish: es };

describe.each(Object.entries(translations))('%s', (_name, messages) => {
  const en_ = en as Record<string, string>;

  it('has every English key, and no other', () => {
    expect(Object.keys(messages).sort()).toEqual(Object.keys(en_).sort());
  });

  it('uses the same {placeholders} as the English text', () => {
    const wrong = Object.keys(en_).filter((key) => placeholders(en_[key]).join() !== placeholders(messages[key] ?? '').join());
    expect(wrong).toEqual([]);
  });
});
