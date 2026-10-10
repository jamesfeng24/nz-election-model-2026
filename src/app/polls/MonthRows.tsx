import type { ReactNode } from 'react';
import { longDate } from '../format';

/** Tables open on this many of the newest polls; every poll stays on the page behind "See more". */
export const INITIAL_POLLS = 10;

const monthOf = (isoDate: string) => longDate(`${isoDate.slice(0, 7)}-01`).replace(/^1 /, '');

/** Table rows for newest-first polls, with a month heading row wherever the month changes. */
export function monthRows<T>(
  items: T[],
  dateOf: (item: T) => string,
  columns: number,
  row: (item: T, index: number) => ReactNode,
) {
  return items.flatMap((item, i) => {
    const date = dateOf(item);
    const startsMonth = i === 0 || monthOf(date) !== monthOf(dateOf(items[i - 1]));
    return [
      ...(startsMonth
        ? [
            <tr key={`month-${i}`} className="month">
              <th colSpan={columns} scope="colgroup">
                {monthOf(date)}
              </th>
            </tr>,
          ]
        : []),
      row(item, i),
    ];
  });
}

export function SeeMore({ total, expanded, onToggle }: { total: number; expanded: boolean; onToggle: () => void }) {
  if (total <= INITIAL_POLLS) return null;
  return (
    <p>
      <button type="button" className="more" aria-expanded={expanded} onClick={onToggle}>
        {expanded ? 'Show fewer polls' : `See more (${total - INITIAL_POLLS} older polls)`}
      </button>
    </p>
  );
}
