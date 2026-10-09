import type { ForecastSnapshot } from '../types/export';

/** How the site names parties (set by James, 2026-10-09): a full form for text and a short form where space is tight. */
const NAMES: Record<string, { long: string; short: string }> = {
  nationalparty: { long: 'National', short: 'National' },
  labourparty: { long: 'Labour', short: 'Labour' },
  actnewzealand: { long: 'ACT', short: 'ACT' },
  newzealandfirstparty: { long: 'New Zealand First', short: 'NZ First' },
  greenparty: { long: 'The Greens', short: 'Greens' },
  opportunity: { long: 'The Opportunity Party', short: 'TOP' },
  tepatimaori: { long: 'Te Pāti Māori', short: 'TPM' },
};

/** Parties the site has no override for keep the name the export gives them. */
export function partyLabel(snapshot: ForecastSnapshot, id: string, form: 'long' | 'short' = 'long'): string {
  const known = NAMES[id];
  if (known) return known[form];
  const party = snapshot.directory.parties.find(p => p.partyId === id);
  return (form === 'short' ? party?.abbreviation : party?.name) ?? party?.name ?? id;
}
