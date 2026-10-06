import { describe, expect, it } from 'vitest';
import { createRng, drawRng } from './prng';

describe('seeded PRNG', () => {
  it('is deterministic per seed and stream, and independent across streams', () => {
    const a = createRng('s', 'x'), b = createRng('s', 'x'), c = createRng('s', 'y'), d = createRng('t', 'x');
    const seq = (r: ReturnType<typeof createRng>) => Array.from({ length: 5 }, () => r.uniform());
    expect(seq(a)).toEqual(seq(b));
    expect(seq(createRng('s', 'x'))).not.toEqual(seq(c));
    expect(seq(createRng('s', 'x'))).not.toEqual(seq(d));
  });
  it('is pinned so published seeds stay reproducible', () => {
    expect(Array.from({ length: 3 }, (() => { const r = createRng('pin', 'x'); return () => Number(r.uniform().toFixed(8)); })())).toMatchInlineSnapshot(`
      [
        0.54178332,
        0.19140185,
        0.83072255,
      ]
    `);
  });
  it('produces uniforms in [0,1) with sensible normal moments', () => {
    const r = drawRng('moments', 0);
    const u = Array.from({ length: 20000 }, () => r.uniform());
    expect(Math.min(...u)).toBeGreaterThanOrEqual(0);
    expect(Math.max(...u)).toBeLessThan(1);
    const n = Array.from({ length: 20000 }, () => r.normal());
    const mean = n.reduce((x, y) => x + y, 0) / n.length;
    const sd = Math.sqrt(n.reduce((x, y) => x + (y - mean) ** 2, 0) / n.length);
    expect(Math.abs(mean)).toBeLessThan(0.03);
    expect(Math.abs(sd - 1)).toBeLessThan(0.03);
  });
  it('gives each draw its own stream regardless of order', () => {
    const forward = [0, 1, 2].map(i => drawRng('order', i).uniform());
    const backward = [2, 1, 0].map(i => drawRng('order', i).uniform()).reverse();
    expect(forward).toEqual(backward);
  });
});
