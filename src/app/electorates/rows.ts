import { useMemo } from 'react';
import type { ForecastSnapshot } from '../../types/export';
import type { IncumbentStatus, MapCandidate } from '../map/types';
import { partyColour } from '../partyColours';
import { candidatePartyName, partyLabel } from '../partyNames';

type Directory = ForecastSnapshot['directory'];

/** One electorate as the search, filters, list and map need it. */
export interface SeatRow {
  id: string;
  name: string;
  kind: 'general' | 'maori';
  available: boolean;
  leaderName: string;
  leaderParty: string | null;
  leaderPartyName: string;
  leaderP: number;
  /** The most likely winner's lower and upper win chance where the model gives a range. */
  secondP: number;
  /** Most likely winner's median vote share minus the runner-up's; null without two shares. */
  margin: number | null;
  incumbent: string | null;
  incumbentParty: string | null;
  incumbentPartyName: string | null;
  incumbentStatus: IncumbentStatus;
  /** The sitting MP is standing and the projected winner is from a different party. */
  partyFlip: boolean;
  candidates: MapCandidate[];
}

const byWinChance = (a: { winProbability: number }, b: { winProbability: number }) =>
  b.winProbability - a.winProbability;

function incumbentStatusOf(
  snapshot: ForecastSnapshot,
  sitting: Directory['candidates'][number] | undefined,
  hasForecast: boolean,
  leaderId: string | undefined,
): IncumbentStatus {
  if (!snapshot.incumbency) return 'unknown';
  if (!sitting) return 'open';
  if (!hasForecast) return 'standing';
  return sitting.candidateId === leaderId ? 'leads' : 'trails';
}

function buildRow(snapshot: ForecastSnapshot, electorate: Directory['electorates'][number]): SeatRow {
  const { electorateId } = electorate;
  const prediction = snapshot.simulation.electoratePredictions.find((p) => p.electorateId === electorateId);
  const detail = snapshot.electorateDetail.find((d) => d.electorateId === electorateId);
  const ranked = prediction ? [...prediction.candidates].sort(byWinChance) : [];
  const findCandidate = (candidateId: string | undefined) =>
    snapshot.directory.candidates.find((c) => c.candidateId === candidateId);
  const leader = findCandidate(ranked[0]?.candidateId);
  const sitting = snapshot.incumbency
    ? snapshot.directory.candidates.find((c) => c.electorateId === electorateId && c.incumbent)
    : undefined;

  const candidates: MapCandidate[] = ranked.flatMap((entry) => {
    const candidate = findCandidate(entry.candidateId);
    if (!candidate) return [];
    return [
      {
        id: candidate.candidateId,
        name: candidate.name,
        partyName: candidatePartyName(snapshot, candidate),
        colour: partyColour(candidate.partyId),
        winP: entry.winProbability,
        share: detail?.candidates.find((d) => d.candidateId === entry.candidateId)?.share[0].median ?? null,
        incumbent: candidate.incumbent === true,
      },
    ];
  });

  const [first, second] = candidates;
  const margin = first?.share != null && second?.share != null ? first.share - second.share : null;
  const sittingParty = sitting ? (sitting.partyId ?? 'independent') : null;
  return {
    id: electorateId,
    name: electorate.name,
    kind: electorate.kind,
    available: !!prediction,
    leaderName: leader?.name ?? '',
    leaderParty: leader?.partyId ?? null,
    leaderPartyName: candidatePartyName(snapshot, leader),
    leaderP: ranked[0]?.winProbability ?? 0,
    secondP: ranked[1]?.winProbability ?? 0,
    margin,
    incumbent: sitting?.name ?? null,
    incumbentParty: sittingParty,
    incumbentPartyName:
      sittingParty && (sittingParty === 'independent' ? 'Independent' : partyLabel(snapshot, sittingParty)),
    partyFlip: !!sitting && !!prediction && (leader?.partyId ?? 'independent') !== sittingParty,
    incumbentStatus: incumbentStatusOf(snapshot, sitting, !!prediction, leader?.candidateId),
    candidates,
  };
}

export const useSeatRows = (snapshot: ForecastSnapshot): SeatRow[] =>
  useMemo(() => snapshot.directory.electorates.map((electorate) => buildRow(snapshot, electorate)), [snapshot]);
