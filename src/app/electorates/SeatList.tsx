import type { ReactNode } from 'react';
import { chance } from '../format';
import type { SeatRow } from './rows';

const COLUMNS = 4;

/** Every listed electorate; the selected one opens in place with its full detail under its row. */
export function SeatList({
  rows,
  caption,
  selectedId,
  detail,
  onToggle,
}: {
  rows: SeatRow[];
  caption: string;
  selectedId: string | null;
  /** The selected seat's detail, shown under its row. */
  detail: ReactNode;
  onToggle: (id: string) => void;
}) {
  return (
    <table className="seatlist">
      <caption>
        {caption} ({rows.length} shown)
      </caption>
      <thead>
        <tr>
          <th>Electorate</th>
          <th>Most likely winner</th>
          <th>Chance</th>
          <th>Expected margin</th>
        </tr>
      </thead>
      <tbody>
        {rows.flatMap((row) => {
          const open = row.id === selectedId;
          return [
            <tr key={row.id} id={`seatrow-${row.id}`} aria-selected={open || undefined}>
              <td>
                <button type="button" className="rowlink" aria-expanded={open} onClick={() => onToggle(row.id)}>
                  {row.name}
                </button>
                {row.kind === 'maori' ? ' (Māori)' : ''}
              </td>
              <td>
                {row.available ? row.leaderName : '–'}
                {row.partyFlip && (
                  <>
                    {' '}
                    <span className="flip-tag">Flip</span>
                  </>
                )}
              </td>
              <td>{row.available ? chance(row.leaderP, row.leaderRange) : 'No forecast'}</td>
              <td>{row.margin === null ? '–' : `${(row.margin * 100).toFixed(1)} pts`}</td>
            </tr>,
            ...(open
              ? [
                  <tr key={`${row.id}-detail`} className="seatdetail">
                    <td colSpan={COLUMNS}>{detail}</td>
                  </tr>,
                ]
              : []),
          ];
        })}
      </tbody>
    </table>
  );
}
