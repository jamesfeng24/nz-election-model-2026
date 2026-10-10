import { chance } from '../format';
import type { SeatRow } from './rows';

export function SeatList({
  rows,
  caption,
  selectedId,
  onSelect,
}: {
  rows: SeatRow[];
  caption: string;
  selectedId: string | null;
  onSelect: (id: string) => void;
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
        {rows.map((row) => (
          <tr key={row.id} aria-selected={row.id === selectedId || undefined}>
            <td>
              <a href={`#seat=${row.id}`} onClick={() => onSelect(row.id)}>
                {row.name}
              </a>
              {row.kind === 'maori' ? ' (Māori)' : ''}
              {row.wide ? ' ·\u00a0wider' : ''}
            </td>
            <td>
              {row.available ? row.leaderName : '–'}
              {row.incumbentStatus === 'trails' && (
                <>
                  {' '}
                  <span className="flip-tag">Flip</span>
                </>
              )}
            </td>
            <td>{row.available ? chance(row.leaderP, row.leaderRange) : 'No forecast'}</td>
            <td>{row.margin === null ? '–' : `${(row.margin * 100).toFixed(1)} pts`}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
