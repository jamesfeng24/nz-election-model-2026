/** Party codes used in the poll sheets, mapped to the site's party names. */
export const PARTY_CODES: Record<string, string> = {
  LAB: 'Labour',
  NAT: 'National',
  GRN: 'Greens',
  ACT: 'ACT',
  NZF: 'NZ First',
  TOP: 'TOP',
  MP: 'Te Pāti Māori',
  TPM: 'Te Pāti Māori',
  IND: 'Independent',
};

/** The poll's full name with the client first: "Taxpayers' Union–Curia". */
export const pollName = (poll: { pollster: string; commissioner: string | null }) =>
  poll.commissioner && !poll.pollster.includes(poll.commissioner)
    ? `${poll.commissioner}–${poll.pollster}`
    : poll.pollster;
