import { prob } from '../format';
import type { SeatRow } from './rows';

export function SeatList({
  rows,
  caption,
  hasIncumbency,
  selectedId,
  onSelect,
}: {
  rows: SeatRow[];
  caption: string;
  hasIncumbency: boolean;
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
          {hasIncumbency && <th>Incumbent</th>}
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
            <td>{row.available ? prob(row.leaderP) : 'No forecast'}</td>
            {hasIncumbency && <td>{row.incumbent ?? 'None standing'}</td>}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
