import { describe, expect, it } from 'vitest';
import { hemicycle, largestRemainder } from './hemicycle';

describe('parliament chart layout', () => {
  it.each([1, 7, 61, 120, 123])('places exactly %i seats, ordered left to right', n => {
    const seats = hemicycle(n);
    expect(seats).toHaveLength(n);
    for (let i = 1; i < n; i++) expect(seats[i].order).toBeGreaterThanOrEqual(seats[i - 1].order);
    for (const s of seats) { expect(s.x).toBeGreaterThanOrEqual(0); expect(s.x).toBeLessThanOrEqual(2); expect(s.y).toBeGreaterThanOrEqual(0); expect(s.y).toBeLessThanOrEqual(1); }
  });
  it('allocates integer seats that sum to the total and stay within one of each mean', () => {
    const means = [33.4, 34.6, 16.5, 12.2, 12.9, 4.9, 8.5];
    const total = Math.round(means.reduce((a, b) => a + b, 0));
    const seats = largestRemainder(means, total);
    expect(seats.reduce((a, b) => a + b, 0)).toBe(total);
    seats.forEach((s, i) => expect(Math.abs(s - means[i])).toBeLessThan(1));
  });
});
