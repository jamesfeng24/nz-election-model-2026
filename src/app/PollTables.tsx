import type { ForecastSnapshot } from '../types/export';
import { dateRange, longDate } from './format';

type ElectorateDetail = ForecastSnapshot['electorateDetail'][number];
export type SeatPoll = NonNullable<ElectorateDetail['evidence']>['polls'][number];

/** Poll-sheet party codes, shown as the site's party names. */
export const CODES: Record<string, string> = { LAB: 'Labour', NAT: 'National', GRN: 'Greens', ACT: 'ACT', NZF: 'NZ First', TOP: 'TOP', MP: 'Te Pāti Māori', TPM: 'Te Pāti Māori', IND: 'Independent' };

/** The poll's full name, client first: "Taxpayers' Union–Curia", "The Spinoff–Curia". */
export const pollName = (poll: { pollster: string; commissioner: string | null }) =>
  poll.commissioner && !poll.pollster.includes(poll.commissioner) ? `${poll.commissioner}–${poll.pollster}` : poll.pollster;

/** One seat poll in a line or two: name, dates, sample, each candidate's figure, whether the forecast used it, and where it was published. */
export function SeatPollLine({ poll }: { poll: SeatPoll }) {
  return <p className="pollline">
    <strong>{pollName(poll)}</strong>, {poll.fieldworkEnd ? dateRange(poll.fieldworkStart, poll.fieldworkEnd) : `published ${longDate(poll.published!)}`}
    {poll.sampleSize ? `, ${poll.sampleSize} people` : ''}{poll.marginOfError ? `, ±${poll.marginOfError}` : ''}:{' '}
    {poll.results.map(r => `${r.name}${r.party ? ` (${CODES[r.party] ?? r.party})` : ''} ${r.approximate ? '~' : ''}${r.percent}%`).join(', ')}.{' '}
    <em>{poll.usedInModel ? 'Used in this forecast.' : 'Not used in this forecast.'}</em>
    {poll.sources.length > 0 && <> Source: {poll.sources.map((s, i) => <span key={s.label + i}>{i > 0 ? '; ' : ''}{s.url ? <a href={s.url} rel="noopener noreferrer">{s.label}</a> : s.label}</span>)}.</>}
    {poll.note && <><br /><small>{poll.note}</small></>}
  </p>;
}
