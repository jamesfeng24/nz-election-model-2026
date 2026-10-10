/** Shares `total` whole seats among non-negative means by largest remainder; no party gets less than its mean's floor. */
export function largestRemainder(means: number[], total: number): number[] {
  const floors = means.map((mean) => Math.floor(Math.max(0, mean)));
  let left = total - floors.reduce((a, b) => a + b, 0);
  const byRemainder = means
    .map((mean, index) => ({ index, remainder: Math.max(0, mean) - floors[index] }))
    .sort((a, b) => b.remainder - a.remainder || a.index - b.index);
  const seats = [...floors];
  for (let k = 0; left > 0 && byRemainder.length > 0; k = (k + 1) % byRemainder.length, left--) {
    seats[byRemainder[k].index]++;
  }
  for (let k = byRemainder.length - 1; left < 0; k = k === 0 ? byRemainder.length - 1 : k - 1) {
    if (seats[byRemainder[k].index] > 0) {
      seats[byRemainder[k].index]--;
      left++;
    }
  }
  return seats;
}

const INNER_RADIUS = 0.4;
const OUTER_RADIUS = 1;
const ROW_COUNT_DIVISOR = 2.2;
const DOT_FILL = 0.44;

const rowCount = (total: number) => Math.max(1, Math.round(Math.sqrt(total / ROW_COUNT_DIVISOR)));
const rowRadii = (rows: number) =>
  Array.from({ length: rows }, (_, row) =>
    rows === 1 ? OUTER_RADIUS : INNER_RADIUS + ((OUTER_RADIUS - INNER_RADIUS) * row) / (rows - 1),
  );

export interface Seat {
  x: number;
  y: number;
  /** Runs from pi (left end of the row) to 0 (right end). */
  angle: number;
  /** Fractional place along the seat's own row, half a step in from the start. */
  order: number;
  row: number;
}

/**
 * Seat positions for a parliament chart: concentric semicircular rows with seats in proportion to each row's radius,
 * the ends of every row on the baseline. Seats are sorted by `order`, so a party's seats form one wedge whose edges
 * step by at most a seat per row and do not line up in columns. Coordinates fill a 2 x 1 box.
 */
export function hemicycle(total: number): Seat[] {
  if (total <= 0) return [];
  const radii = rowRadii(rowCount(total));
  const radiiSum = radii.reduce((a, b) => a + b, 0);
  const seatsPerRow = largestRemainder(
    radii.map((radius) => (radius / radiiSum) * total),
    total,
  );
  const seats: Seat[] = [];
  radii.forEach((radius, row) => {
    const n = seatsPerRow[row];
    for (let k = 0; k < n; k++) {
      const angle = n === 1 ? Math.PI / 2 : Math.PI - (Math.PI * k) / (n - 1);
      seats.push({
        x: 1 + radius * Math.cos(angle),
        y: 1 - radius * Math.sin(angle),
        angle,
        order: (k + 0.5) / n,
        row,
      });
    }
  });
  return seats.sort((a, b) => a.order - b.order || a.row - b.row);
}

/** The largest dot radius, in the same units, that leaves a gap between neighbours in a row and between rows. */
export function hemicycleDot(total: number): number {
  const rows = rowCount(total);
  const rowGap = rows === 1 ? OUTER_RADIUS : (OUTER_RADIUS - INNER_RADIUS) / (rows - 1);
  const arcGap = (Math.PI * rowRadii(rows).reduce((a, b) => a + b, 0)) / Math.max(1, total);
  return DOT_FILL * Math.min(rowGap, arcGap);
}
