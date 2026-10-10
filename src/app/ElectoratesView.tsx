import { useMemo, useState } from 'react';
import type { ForecastSnapshot } from '../types/export';
import { ElectorateMap } from './ElectorateMap';
import {
  NO_FILTERS,
  SORTS,
  anyFilterSet,
  nameContains,
  passesFilters,
  type Filters,
  type SortKey,
} from './electorates/filters';
import { useSeatRows } from './electorates/rows';
import { SeatDetail } from './electorates/SeatDetail';
import { SeatFilters } from './electorates/SeatFilters';
import { SeatList } from './electorates/SeatList';
import { SeatSearch } from './electorates/SeatSearch';
import { useSelectedSeat } from './electorates/useSelectedSeat';

/** Search, filters, map and seat pages for every electorate. */
export function ElectoratesView({ snapshot }: { snapshot: ForecastSnapshot }) {
  const rows = useSeatRows(snapshot);
  const { seatId, setSeatId, choose } = useSelectedSeat();
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortKey>('name');
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const hasIncumbency = !!snapshot.incumbency;
  const filtered = anyFilterSet(filters);

  const matching = useMemo(
    () => (filtered ? new Set(rows.filter((row) => passesFilters(row, filters)).map((row) => row.id)) : null),
    [rows, filters, filtered],
  );
  const listed = useMemo(
    () =>
      rows
        .filter((row) => (!query.trim() || nameContains(row, query)) && passesFilters(row, filters))
        .sort(SORTS[sort]),
    [rows, query, sort, filters],
  );
  const pick = (id: string) => {
    choose(id);
    document.getElementById('seat-heading')?.scrollIntoView?.({ block: 'start' });
  };

  return (
    <>
      <p className="intro">Pick a seat for each candidate's chance of winning, vote share and polls.</p>
      <div className="picker">
        <SeatSearch rows={rows} query={query} onQueryChange={setQuery} onChoose={choose} onPick={pick} />
        <label>
          Sort by
          <select value={sort} onChange={(event) => setSort(event.target.value as SortKey)}>
            <option value="name">Alphabetical</option>
            <option value="close">Closest contest first</option>
          </select>
        </label>
      </div>
      <SeatFilters rows={rows} hasIncumbency={hasIncumbency} filters={filters} onChange={setFilters} />
      <ElectorateMap snapshot={snapshot} forecasts={rows} onSelect={pick} highlight={matching} />
      {seatId && rows.some((row) => row.id === seatId) ? (
        <SeatDetail snapshot={snapshot} seatId={seatId} />
      ) : (
        <p>Pick a seat on the map, in the list or in the search box.</p>
      )}
      <SeatList
        rows={listed}
        caption={filtered ? 'Electorates matching the filters' : `All ${rows.length} electorates`}
        selectedId={seatId}
        onSelect={setSeatId}
      />
    </>
  );
}
