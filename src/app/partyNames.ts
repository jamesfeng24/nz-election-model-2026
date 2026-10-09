import type { ForecastSnapshot } from '../types/export';

/** How the site names parties everywhere (James, 2026-10-09): the names NZ media use, one form each. */
const NAMES: Record<string, string> = {
  nationalparty: 'National',
  labourparty: 'Labour',
  greenparty: 'Greens',
  actnewzealand: 'ACT',
  newzealandfirstparty: 'NZ First',
  opportunity: 'TOP',
  tepatimaori: 'Te Pāti Māori',
};

/** The registered names, shown once on the methodology page. */
export const REGISTERED_NAMES: [string, string][] = [
  ['National', 'New Zealand National Party'], ['Labour', 'New Zealand Labour Party'], ['Greens', 'Green Party of Aotearoa New Zealand'],
  ['ACT', 'ACT New Zealand'], ['NZ First', 'New Zealand First'], ['TOP', 'The Opportunity Party (TOP)'], ['Te Pāti Māori', 'Te Pāti Māori'],
];

/** Parties the site has no name for keep the name the export gives them. */
export function partyLabel(snapshot: ForecastSnapshot, id: string): string {
  return NAMES[id] ?? snapshot.directory.parties.find(p => p.partyId === id)?.name ?? id;
}
