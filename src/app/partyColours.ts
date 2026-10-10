/** Left-to-right order of the headline chart and the seats table. */
export const HEADLINE_ORDER = [
  'tepatimaori',
  'greenparty',
  'labourparty',
  'opportunity',
  'newzealandfirstparty',
  'nationalparty',
  'actnewzealand',
];

export const COLOURS: Record<string, string> = {
  tepatimaori: '#8c1d40',
  greenparty: '#1c9a47',
  labourparty: '#d82a20',
  opportunity: '#12a4c6',
  newzealandfirstparty: '#222222',
  nationalparty: '#00529f',
  actnewzealand: '#e0b800',
};

/** For parties with no fixed colour. */
export const FALLBACK = ['#6b5b95', '#c47f17', '#4d7c8a', '#a05195', '#7a8b3a', '#b5524b', '#5a6b73'];

export const INDEPENDENT_COLOUR = '#8b8f94';

export const partyColour = (partyId: string | null | undefined) => (partyId && COLOURS[partyId]) || INDEPENDENT_COLOUR;

export const headlineRank = (partyId: string) => {
  const index = HEADLINE_ORDER.indexOf(partyId);
  return index < 0 ? HEADLINE_ORDER.length : index;
};
