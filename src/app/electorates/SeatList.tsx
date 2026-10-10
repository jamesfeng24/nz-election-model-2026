import { useState, type ReactNode } from 'react';
import { Collapsible } from './Collapsible';
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
  // The seat that was open folds shut while the new one opens, so both move at once. `shown` is the open seat as
  // of the last render; when the selection changes the previous one becomes `closing` until its fold has finished.
  const [shown, setShown] = useState<{ id: string; detail: ReactNode } | null>(null);
  const [closing, setClosing] = useState<{ id: string; detail: ReactNode } | null>(null);
  if ((shown?.id ?? null) !== selectedId) {
    if (shown) setClosing(shown);
    setShown(selectedId ? { id: selectedId, detail } : null);
  }
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
            ...(open || closing?.id === row.id
              ? [
                  <tr key={`${row.id}-detail`} className="seatdetail">
                    <td colSpan={COLUMNS}>
                      <Collapsible open={open} onClosed={() => setClosing(null)}>
                        {open ? detail : closing?.detail}
                      </Collapsible>
                    </td>
                  </tr>,
                ]
              : []),
          ];
        })}
      </tbody>
    </table>
  );
}
