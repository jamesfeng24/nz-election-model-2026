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
  newzealandfirstparty: '#707070',
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

const luminance = (hex: string) => {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const lin = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
};

/** The median line is near-black, or white on a colour too dark for it to show (contrast under 2.5 to 1). */
export const medianColour = (colour: string) =>
  (luminance(colour) + 0.05) / (luminance('#222222') + 0.05) < 2.5 ? '#fff' : '#222';
