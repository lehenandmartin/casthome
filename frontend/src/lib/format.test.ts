import { describe, expect, it } from 'vitest';
import { formatTime } from './format';
import { fullRows } from './grid';

describe('formatTime', () => {
  it('formats minutes and hours', () => {
    expect(formatTime(0)).toBe('0:00');
    expect(formatTime(65.9)).toBe('1:05');
    expect(formatTime(3725)).toBe('1:02:05');
  });

  it('shows 0:00 for missing or invalid values', () => {
    expect(formatTime(null)).toBe('0:00');
    expect(formatTime(-3)).toBe('0:00');
    expect(formatTime(Number.NaN)).toBe('0:00');
    expect(formatTime(Number.POSITIVE_INFINITY)).toBe('0:00');
  });
});

describe('fullRows', () => {
  it('keeps only full rows', () => {
    expect(fullRows([1, 2, 3, 4, 5, 6, 7], 3)).toEqual([1, 2, 3, 4, 5, 6]);
  });

  it('keeps everything when there is less than a row or no column count', () => {
    expect(fullRows([1, 2], 3)).toEqual([1, 2]);
    expect(fullRows([1, 2, 3], 0)).toEqual([1, 2, 3]);
  });
});
