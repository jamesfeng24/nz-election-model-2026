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

/** `2026-09-21`, `2026-09-28` → `21–28 September 2026`; across months `21 September – 3 October 2026`; no start → the end date. */
export function dateRange(start: string | null, end: string): string {
  if (!start || start === end) return longDate(end);
  const [y0, m0, d0] = start.slice(0, 10).split('-').map(Number), [y1, m1, d1] = end.slice(0, 10).split('-').map(Number);
  if (y0 === y1 && m0 === m1) return `${d0}–${d1} ${MONTHS[m1 - 1]} ${y1}`;
  return y0 === y1 ? `${d0} ${MONTHS[m0 - 1]} – ${d1} ${MONTHS[m1 - 1]} ${y1}` : `${longDate(start)} – ${longDate(end)}`;
}
