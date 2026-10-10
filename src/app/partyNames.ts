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

/** Parties the site has no name for keep the name the export gives them. */
export function partyLabel(snapshot: ForecastSnapshot, id: string): string {
  return NAMES[id] ?? snapshot.directory.parties.find(p => p.partyId === id)?.name ?? id;
}
