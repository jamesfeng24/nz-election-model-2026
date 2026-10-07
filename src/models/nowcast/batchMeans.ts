import { chainPosition } from './drawBank';

/**
 * Effective-sample Monte Carlo error by non-overlapping batch means within MCMC chains.
 *
 * Bank rows are a seeded subset of the national MCMC draws, so neighbouring draws of a chain are correlated and
 * sqrt(p(1-p)/n) overstates precision (docs/nowcast-specification.md §2). Rows are put back in chain order, each chain
 * is cut into contiguous batches of equal size, and the variance of the batch means estimates the long-run variance.
 * With b batches of size m: MCSE = sqrt(m * var(batch means) / n), ESS = n * var(series) / (m * var(batch means)).
 */
export interface McseResult { mean: number; mcse: number; ess: number; batches: number; batchSize: number }

export interface ChainOrder { order: number[]; chains: number[][] }

/**
 * Row indices grouped by chain, each chain in draw order. With layer replication, row r belongs to national draw
 * floor(r / replicates); a draw's replicates stay together, so batches never split one national draw.
 */
export function chainOrder(drawIds: string[], replicates = 1): ChainOrder {
  const byChain = new Map<string, { row: number; index: number }[]>();
  drawIds.forEach((drawId, national) => {
    const { chain, index } = chainPosition(drawId);
    if (!byChain.has(chain)) byChain.set(chain, []);
    for (let r = 0; r < replicates; r++) byChain.get(chain)!.push({ row: national * replicates + r, index: index * replicates + r });
  });
  const chains = [...byChain.keys()].sort().map(k => byChain.get(k)!.sort((a, b) => a.index - b.index).map(x => x.row));
  return { order: chains.flat(), chains };
}

export function batchMeansMcse(values: ArrayLike<number>, layout: ChainOrder, unit = 1): McseResult {
  const n = values.length;
  if (n === 0) throw new RangeError('No values');
  const mean = Array.from(values).reduce((a, b) => a + b, 0) / n;
  const variance = Array.from(values).reduce((s, v) => s + (v - mean) ** 2, 0) / Math.max(1, n - 1);
  // About sqrt(n) batches in total, spread over chains; batch size is common so the batch means are comparable.
  const target = Math.max(2, Math.floor(Math.sqrt(n)));
  const m = Math.max(unit, Math.floor(n / target / unit) * unit);
  const means: number[] = [];
  for (const rows of layout.chains) {
    for (let start = 0; start + m <= rows.length; start += m) {
      let s = 0;
      for (let k = start; k < start + m; k++) s += values[rows[k]];
      means.push(s / m);
    }
  }
  if (means.length < 2) throw new RangeError('Too few draws for batch means');
  const bm = means.reduce((a, b) => a + b, 0) / means.length;
  const longRun = m * means.reduce((s, v) => s + (v - bm) ** 2, 0) / (means.length - 1);
  if (longRun === 0) return { mean, mcse: 0, ess: n, batches: means.length, batchSize: m };
  return { mean, mcse: Math.sqrt(longRun / n), ess: variance === 0 ? n : (n * variance) / longRun, batches: means.length, batchSize: m };
}
