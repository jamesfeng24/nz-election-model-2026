export interface Seat { x: number; y: number; angle: number }

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

/**
 * Seat positions for a parliament chart: concentric semicircular rows, with seats per row proportional to the row's
 * radius, then ordered by angle from the left so each party fills one wedge. Coordinates are in a 2 x 1 box (x 0 to 2, y 0 to 1).
 */
export function hemicycle(total: number): Seat[] {
  if (total <= 0) return [];
  const rows = Math.max(1, Math.round(Math.sqrt(total / 2.2)));
  const inner = 0.4, outer = 1;
  const radii = Array.from({ length: rows }, (_, r) => (rows === 1 ? outer : inner + ((outer - inner) * r) / (rows - 1)));
  const sum = radii.reduce((a, b) => a + b, 0);
  const counts = largestRemainder(radii.map(r => (r / sum) * total), total);
  const seats: Seat[] = [];
  radii.forEach((radius, r) => {
    const n = counts[r];
    for (let k = 0; k < n; k++) {
      const angle = n === 1 ? Math.PI / 2 : Math.PI - (Math.PI * k) / (n - 1);
      seats.push({ x: 1 + radius * Math.cos(angle), y: 1 - radius * Math.sin(angle), angle });
    }
  });
  return seats.sort((a, b) => b.angle - a.angle || a.y - b.y);
}
