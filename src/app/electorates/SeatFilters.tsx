import { useMemo } from 'react';
import { CLOSE_BELOW, NO_FILTERS, anyFilterSet, partyOptions, type Filters } from './filters';
import type { SeatRow } from './rows';

function PartySelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: [string, string][];
  onChange: (value: string) => void;
}) {
  return (
    <label>
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="any">Any party</option>
        {options.map(([id, name]) => (
          <option key={id} value={id}>
            {name}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Party, type, close-contest and flip filters. The incumbent filters only appear when the forecast has incumbent data. */
export function SeatFilters({
  rows,
  hasIncumbency,
  filters,
  onChange,
}: {
  rows: SeatRow[];
  hasIncumbency: boolean;
  filters: Filters;
  onChange: (filters: Filters) => void;
}) {
  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => onChange({ ...filters, [key]: value });
  const winnerParties = useMemo(
    () => partyOptions(rows.filter((r) => r.available).map((r) => [r.leaderParty ?? 'independent', r.leaderPartyName])),
    [rows],
  );
  const incumbentParties = useMemo(
    () =>
      partyOptions(
        rows.flatMap((r) => (r.incumbentParty ? [[r.incumbentParty, r.incumbentPartyName!] as [string, string]] : [])),
      ),
    [rows],
  );
  return (
    <div className="picker filters" role="group" aria-label="Filter seats">
      <PartySelect
        label="Projected winner's party"
        value={filters.winner}
        options={winnerParties}
        onChange={(value) => set('winner', value)}
      />
      {hasIncumbency && (
        <PartySelect
          label="Incumbent's party"
          value={filters.incumbent}
          options={incumbentParties}
          onChange={(value) => set('incumbent', value)}
        />
      )}
      <label>
        Type
        <select value={filters.kind} onChange={(event) => set('kind', event.target.value as Filters['kind'])}>
          <option value="any">General and Māori</option>
          <option value="general">General</option>
          <option value="maori">Māori</option>
        </select>
      </label>
      <label className="check">
        <input type="checkbox" checked={filters.close} onChange={(event) => set('close', event.target.checked)} /> Close
        contests (winner under {Math.round(CLOSE_BELOW * 100)}%)
      </label>
      {hasIncumbency && (
        <label className="check">
          <input type="checkbox" checked={filters.flip} onChange={(event) => set('flip', event.target.checked)} />{' '}
          Projected flips
        </label>
      )}
      {anyFilterSet(filters) && (
        <button type="button" className="more" onClick={() => onChange(NO_FILTERS)}>
          Clear filters
        </button>
      )}
    </div>
  );
}
