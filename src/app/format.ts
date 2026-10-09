const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

/** `2026-10-10` or a longer ISO timestamp → `10 October 2026`, without locale or time-zone surprises. */
export function longDate(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

export const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

/** A probability rounded to a whole percent; never shows a rounded 0% or 100% for something not certain. */
export function prob(p: number): string {
  if (p > 0 && p < 0.005) return '<1%';
  if (p < 1 && p > 0.995) return '>99%';
  return `${Math.round(p * 100)}%`;
}
