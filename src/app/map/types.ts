export type Box = [number, number, number, number];

export interface MapSeat {
  id: string;
  name: string;
  kind: 'general' | 'maori';
  path: string;
  box: Box;
}

export interface MapData {
  width: number;
  height: number;
  insets: { name: string; box: Box }[];
  seats: MapSeat[];
  source: string;
}

/** A candidate as the hover card lists them. */
export interface MapCandidate {
  id: string;
  name: string;
  partyName: string;
  colour: string;
  winP: number;
  /** Lower and upper win chance where the model gives a range (polled Māori seats). */
  winRange?: [number, number] | null;
  share: number | null;
  incumbent: boolean;
}

/**
 * Whether the seat's sitting MP is standing, and how they fare:
 * `unknown` no incumbent data, `open` no sitting MP standing, `standing` standing but the seat has no forecast,
 * `leads` the favourite, `trails` not the favourite (a projected flip).
 */
export type IncumbentStatus = 'unknown' | 'open' | 'standing' | 'leads' | 'trails';

export interface MapForecast {
  id: string;
  name: string;
  kind: 'general' | 'maori';
  leaderParty: string | null;
  leaderPartyName: string;
  leaderName: string;
  leaderP: number;
  leaderRange?: [number, number] | null;
  available: boolean;
  incumbent: string | null;
  incumbentStatus: IncumbentStatus;
  candidates: MapCandidate[];
}

/** Matches seat names however the export spells them: ignores case, macrons, hyphens and spaces. */
export const seatKey = (name: string) =>
  name
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '');

/** Spoken or tooltip suffix naming the sitting MP; empty when there is no incumbent data. */
export function incumbentNote(seat: MapForecast) {
  if (seat.incumbentStatus === 'unknown') return '';
  if (seat.incumbentStatus === 'open' || !seat.incumbent) return '. No sitting MP is standing';
  const standing =
    seat.incumbentStatus === 'leads'
      ? ' (most likely winner)'
      : seat.incumbentStatus === 'trails'
        ? ' (not the most likely winner)'
        : '';
  return `. Incumbent: ${seat.incumbent}${standing}`;
}

/** Paler for toss-ups, solid for safe seats. */
export const opacityFor = (winChance: number) => 0.2 + 0.8 * Math.max(0, Math.min(1, (winChance - 0.4) / 0.6));
