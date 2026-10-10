import type { ForecastSnapshot } from '../types/export';

/** The names NZ media use, one form each. */
const NAMES: Record<string, string> = {
  nationalparty: 'National',
  labourparty: 'Labour',
  greenparty: 'Greens',
  actnewzealand: 'ACT',
  newzealandfirstparty: 'NZ First',
  opportunity: 'TOP',
  tepatimaori: 'Te Pāti Māori',
  other: 'Other',
};

/** Parties with no name here keep the name from the export. */
export function partyLabel(snapshot: ForecastSnapshot, id: string): string {
  return NAMES[id] ?? snapshot.directory.parties.find((p) => p.partyId === id)?.name ?? id;
}

type Candidate = ForecastSnapshot['directory']['candidates'][number];

export function candidatePartyName(snapshot: ForecastSnapshot, candidate: Candidate | undefined): string {
  if (candidate?.partyId) return partyLabel(snapshot, candidate.partyId);
  return candidate?.partyLabel ?? 'Independent';
}
