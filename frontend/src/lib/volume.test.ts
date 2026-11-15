import { describe, expect, it, vi } from 'vitest';

// volume.svelte.ts imports the app store; only the pure step function is tested here.
vi.mock('./store.svelte', () => ({ store: {} }));
vi.mock('./api', () => ({ api: {} }));

const { nextVolume } = await import('./volume.svelte');

describe('nextVolume', () => {
  it('moves by 5 % on a 5 % grid', () => {
    expect(nextVolume(0.2, 1)).toBe(0.25);
    expect(nextVolume(0.2, -1)).toBe(0.15);
  });

  it('snaps an in-between level to the grid', () => {
    expect(nextVolume(0.01, 1)).toBe(0.05);
    expect(nextVolume(0.01, -1)).toBe(0);
    expect(nextVolume(0.43, 1)).toBe(0.45);
    expect(nextVolume(0.43, -1)).toBe(0.4);
  });

  it('stays within 0–100 %', () => {
    expect(nextVolume(0, -1)).toBe(0);
    expect(nextVolume(1, 1)).toBe(1);
    expect(nextVolume(0.98, 1)).toBe(1);
  });

  it('is not fooled by floating point (0.15 + 0.05)', () => {
    expect(nextVolume(0.15000000000000002, 1)).toBe(0.2);
    expect(nextVolume(0.30000000000000004, -1)).toBe(0.25);
  });
});
