const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

/** `2026-10-10` or a longer ISO timestamp → `10 October 2026`, with no time-zone shift. */
export function longDate(iso: string): string {
  const [year, month, day] = iso.slice(0, 10).split('-').map(Number);
  return `${day} ${MONTHS[month - 1]} ${year}`;
}

export const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

/** A probability rounded to a whole percent; never shows a rounded 0% or 100% for something not certain. */
export function prob(p: number): string {
  if (p > 0 && p < 0.005) return '<1%';
  if (p < 1 && p > 0.995) return '>99%';
  return `${Math.round(p * 100)}%`;
}

/** `2026-09-21`, `2026-09-28` → `21–28 September 2026`; across months `21 September – 3 October 2026`. */
export function dateRange(start: string | null, end: string): string {
  if (!start || start === end) return longDate(end);
  const [startYear, startMonth, startDay] = start.slice(0, 10).split('-').map(Number);
  const [endYear, endMonth, endDay] = end.slice(0, 10).split('-').map(Number);
  if (startYear !== endYear) return `${longDate(start)} – ${longDate(end)}`;
  if (startMonth === endMonth) return `${startDay}–${endDay} ${MONTHS[endMonth - 1]} ${endYear}`;
  return `${startDay} ${MONTHS[startMonth - 1]} – ${endDay} ${MONTHS[endMonth - 1]} ${endYear}`;
}
