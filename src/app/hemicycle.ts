/** Allocate `total` integer seats to non-negative means by largest remainder, keeping every mean's floor. */
export function largestRemainder(means: number[], total: number): number[] {
  const floors = means.map(m => Math.floor(Math.max(0, m)));
  let left = total - floors.reduce((a, b) => a + b, 0);
  const order = means.map((m, i) => ({ i, r: Math.max(0, m) - floors[i] })).sort((a, b) => b.r - a.r || a.i - b.i);
  const out = [...floors];
  for (let k = 0; left > 0 && order.length > 0; k = (k + 1) % order.length, left--) out[order[k].i]++;
  for (let k = order.length - 1; left < 0; k = k === 0 ? order.length - 1 : k - 1) if (out[order[k].i] > 0) { out[order[k].i]--; left++; }
  return out;
}

const INNER = 0.4, OUTER = 1;
const rowCount = (total: number) => Math.max(1, Math.round(Math.sqrt(total / 2.2)));
const rowRadii = (rows: number) => Array.from({ length: rows }, (_, r) => (rows === 1 ? OUTER : INNER + ((OUTER - INNER) * r) / (rows - 1)));

/**
 * Seat positions for a parliament chart: concentric semicircular rows with seats per row proportional to the row's radius,
 * the ends of every row on the baseline. Seats come back ordered by `order`, each seat's fractional place along its own row
 * (half a step in from the row's start), so a party's seats form one wedge whose edges step by at most a seat per row and
 * do not line up in columns. Coordinates are in a 2 x 1 box (x 0 to 2, y 0 to 1); `angle` runs from pi (left) to 0.
 */
export interface Seat { x: number; y: number; angle: number; order: number; row: number }
export function hemicycle(total: number): Seat[] {
  if (total <= 0) return [];
  const radii = rowRadii(rowCount(total));
  const sum = radii.reduce((a, b) => a + b, 0);
  const counts = largestRemainder(radii.map(r => (r / sum) * total), total);
  const seats: Seat[] = [];
  radii.forEach((radius, row) => {
    const n = counts[row];
    for (let k = 0; k < n; k++) {
      const angle = n === 1 ? Math.PI / 2 : Math.PI - (Math.PI * k) / (n - 1);
      seats.push({ x: 1 + radius * Math.cos(angle), y: 1 - radius * Math.sin(angle), angle, order: (k + 0.5) / n, row });
    }
  });
  return seats.sort((a, b) => a.order - b.order || a.row - b.row);
}

/** Largest dot radius, in the same 2 x 1 units, that leaves a gap between neighbours in a row and between rows. */
export function hemicycleDot(total: number): number {
  const rows = rowCount(total);
  const rowGap = rows === 1 ? OUTER : (OUTER - INNER) / (rows - 1);
  const arcGap = (Math.PI * rowRadii(rows).reduce((a, b) => a + b, 0)) / Math.max(1, total);
  return 0.44 * Math.min(rowGap, arcGap);
}
