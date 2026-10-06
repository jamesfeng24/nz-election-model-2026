/** Seeded, DOM-free PRNG. Same seed and label always give the same stream, in any environment. */
export const PRNG_NAME = 'sfc32-xmur3';
export const PRNG_VERSION = '1';

function xmur3(text: string): () => number {
  let h = 1779033703 ^ text.length;
  for (let i = 0; i < text.length; i++) {
    h = Math.imul(h ^ text.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return () => {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return (h ^= h >>> 16) >>> 0;
  };
}

export interface Rng {
  /** Uniform on [0, 1). */
  uniform(): number;
  /** Standard normal (Box–Muller; the spare deviate is discarded so streams stay simple to reason about). */
  normal(): number;
}

export function createRng(seed: string, stream: string): Rng {
  const next = xmur3(`${seed}\u0000${stream}`);
  let a = next(), b = next(), c = next(), d = next();
  const u32 = () => {
    a >>>= 0; b >>>= 0; c >>>= 0; d >>>= 0;
    const t = (((a + b) | 0) + d) | 0;
    d = (d + 1) | 0;
    a = b ^ (b >>> 9);
    b = (c + (c << 3)) | 0;
    c = (c << 21) | (c >>> 11);
    c = (c + t) | 0;
    return t >>> 0;
  };
  for (let i = 0; i < 15; i++) u32();
  const uniform = () => u32() / 4294967296;
  return {
    uniform,
    normal() {
      const u = 1 - uniform(); // (0, 1]
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * uniform());
    },
  };
}

/** Independent stream per draw: results do not depend on how draws are chunked across workers. */
export const drawRng = (seed: string, draw: number): Rng => createRng(seed, `draw:${draw}`);
