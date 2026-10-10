import type { SeatRow } from './rows';

export type SortKey = 'name' | 'close';

export interface Filters {
  winner: string;
  incumbent: string;
  kind: 'any' | 'general' | 'maori';
  close: boolean;
  flip: boolean;
}

export const NO_FILTERS: Filters = { winner: 'any', incumbent: 'any', kind: 'any', close: false, flip: false };

/** A seat is close when its most likely winner has under this chance. */
export const CLOSE_BELOW = 0.7;

export const anyFilterSet = (filters: Filters) => JSON.stringify(filters) !== JSON.stringify(NO_FILTERS);

export const passesFilters = (row: SeatRow, filters: Filters) =>
  (filters.winner === 'any' || (row.available && (row.leaderParty ?? 'independent') === filters.winner)) &&
  (filters.incumbent === 'any' || row.incumbentParty === filters.incumbent) &&
  (!filters.flip || row.partyFlip) &&
  (filters.kind === 'any' || row.kind === filters.kind) &&
  (!filters.close || (row.available && row.leaderP < CLOSE_BELOW));

const normalise = (text: string) => text.trim().toLocaleLowerCase('en-NZ');

export const nameContains = (row: SeatRow, query: string) => normalise(row.name).includes(normalise(query));
export const nameEquals = (row: SeatRow, query: string) => normalise(row.name) === normalise(query);

const byName = (a: SeatRow, b: SeatRow) => a.name.localeCompare(b.name, 'en-NZ');

export const SORTS: Record<SortKey, (a: SeatRow, b: SeatRow) => number> = {
  name: byName,
  close: (a, b) => a.leaderP - a.secondP - (b.leaderP - b.secondP) || byName(a, b),
};

/** Distinct parties as [id, name] pairs, sorted by name. */
export const partyOptions = (pairs: [string, string][]) =>
  [...new Map(pairs).entries()].sort((a, b) => a[1].localeCompare(b[1], 'en-NZ'));
