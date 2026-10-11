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

/** Minor parties that stand candidates but have no national group, by the ballot-group key the export keeps; the short names media use. */
const MINOR_NAMES: Record<string, string> = {
  newzealandloyal: 'NZ Loyal',
  aotearoalegalisecannabisparty: 'Legalise Cannabis',
  conservativepartynz: 'Conservative',
  alliancepartyofaotearoanewzealand: 'Alliance',
  nzoutdoorsfreedomparty: 'Outdoors & Freedom',
  animaljusticeparty: 'Animal Justice',
  visionnewzealand: 'Vision NZ',
  freepalestine: 'Free Palestine',
  tetaitokerauparty: 'Te Tai Tokerau Party',
};

/** Parties with no name here keep the name from the export. */
export function partyLabel(snapshot: ForecastSnapshot, id: string): string {
  return NAMES[id] ?? MINOR_NAMES[id] ?? snapshot.directory.parties.find((p) => p.partyId === id)?.name ?? id;
}

type Candidate = ForecastSnapshot['directory']['candidates'][number];

export function candidatePartyName(snapshot: ForecastSnapshot, candidate: Candidate | undefined): string {
  const label = candidate?.partyLabel;
  if (label && MINOR_NAMES[label]) return MINOR_NAMES[label];
  if (candidate?.partyId && candidate.partyId !== 'other') return partyLabel(snapshot, candidate.partyId);
  if (!label) return candidate?.partyId ? partyLabel(snapshot, candidate.partyId) : 'Independent';
  // A ballot-group key is lower case with no spaces; a party missing from the table above never shows as that raw key.
  return /^[a-z0-9]+$/.test(label) ? 'Other party' : label;
}

/** A candidate of a party that is not one of the seven parties the site lists (an independent or a minor party). */
export function isMainParty(candidate: Candidate | undefined): boolean {
  return !!candidate?.partyId && candidate.partyId !== 'other' && candidate.partyId in NAMES;
}
