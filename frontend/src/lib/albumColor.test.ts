import { describe, expect, it } from 'vitest';
import { dominantColor } from './albumColor';

const px = (...colors: [number, number, number][]) => colors.flatMap(([r, g, b]) => [r, g, b, 255]);

describe('dominantColor', () => {
  it('finds the vivid colour on a dark picture', () => {
    const pixels = px(...Array(20).fill([10, 10, 12]), ...Array(4).fill([220, 60, 160]));
    const color = dominantColor(pixels)!;
    expect(color.h).toBeGreaterThan(310);
    expect(color.h).toBeLessThan(330);
    expect(color.s).toBeGreaterThan(40);
  });

  it('gives nothing for a grey picture', () => {
    expect(dominantColor(px([30, 30, 30], [128, 128, 130], [240, 240, 240]))).toBeNull();
  });

  it('caps the saturation', () => {
    expect(dominantColor(px([255, 0, 0]))!.s).toBeLessThanOrEqual(72);
  });

  it('skips transparent pixels', () => {
    expect(dominantColor([255, 0, 0, 0])).toBeNull();
  });
});
