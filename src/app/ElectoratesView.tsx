import { useEffect, useMemo, useState } from 'react';
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
import { glideTo } from './electorates/scroll';
import { useSelectedSeat } from './electorates/useSelectedSeat';

/** Search, filters, map and seat pages for every electorate. */
export function ElectoratesView({ snapshot }: { snapshot: ForecastSnapshot }) {
  const rows = useSeatRows(snapshot);
  const { seatId, choose, clear } = useSelectedSeat();
  const [scrollRequest, setScrollRequest] = useState<{ id: string } | null>(null);
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
  const open = (id: string) => {
    choose(id);
    setScrollRequest({ id });
  };
  const toggle = (id: string) => (id === seatId ? clear() : open(id));

  // Glide to the seat once its detail has rendered, so the target sits where the page ends up.
  useEffect(() => {
    if (scrollRequest) glideTo(document.getElementById(`seatrow-${scrollRequest.id}`));
  }, [scrollRequest]);

  const selected = seatId && rows.some((row) => row.id === seatId) ? seatId : null;
  const detail = selected ? <SeatDetail snapshot={snapshot} seatId={selected} /> : null;
  const inList = selected !== null && listed.some((row) => row.id === selected);

  return (
    <>
      <p className="intro">Pick a seat for each candidate's chance of winning, vote share and polls.</p>
      <div className="picker">
        <SeatSearch rows={rows} query={query} onQueryChange={setQuery} onChoose={choose} onPick={open} />
        <label>
          Sort by
          <select value={sort} onChange={(event) => setSort(event.target.value as SortKey)}>
            <option value="name">Alphabetical</option>
            <option value="close">Closest contest first</option>
          </select>
        </label>
      </div>
      <SeatFilters rows={rows} hasIncumbency={hasIncumbency} filters={filters} onChange={setFilters} />
      <ElectorateMap snapshot={snapshot} forecasts={rows} onSelect={open} highlight={matching} />
      {selected && !inList && <div id={`seatrow-${selected}`}>{detail}</div>}
      <SeatList
        rows={listed}
        caption={filtered ? 'Electorates matching the filters' : `All ${rows.length} electorates`}
        selectedId={selected}
        detail={detail}
        onToggle={toggle}
      />
    </>
  );
}
