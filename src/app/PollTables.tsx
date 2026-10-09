import type { ForecastSnapshot } from '../types/export';
import { longDate } from './format';

type ElectorateDetail = ForecastSnapshot['electorateDetail'][number];
export type SeatPoll = NonNullable<ElectorateDetail['evidence']>['polls'][number];

const dates = (p: SeatPoll) => p.fieldworkEnd
  ? `fieldwork ${p.fieldworkStart ? `${longDate(p.fieldworkStart)} to ` : 'to '}${longDate(p.fieldworkEnd)}`
  : `published ${longDate(p.published!)} (fieldwork dates not stated)`;

/** One seat poll with its citation: pollster, client, dates, sample, whether the forecast used it, and where it was published. */
export function SeatPollTable({ poll }: { poll: SeatPoll }) {
  return <table className="poll">
    <caption>
      <strong>{poll.pollster}</strong>{poll.commissioner ? `, for ${poll.commissioner}` : ''}; {dates(poll)}
      {poll.sampleSize ? `; ${poll.sampleSize} people` : ''}{poll.marginOfError ? `; margin of error ±${poll.marginOfError} points` : ''}.{' '}
      <em>{poll.usedInModel ? 'Used in this forecast.' : 'Found but not used in this forecast.'}</em>
    </caption>
    <thead><tr><th>Candidate</th><th>Poll</th></tr></thead>
    <tbody>{poll.results.map(r => <tr key={r.name}><td>{r.name}{r.party ? ` (${r.party})` : ''}</td><td>{r.approximate ? '~' : ''}{r.percent}%</td></tr>)}</tbody>
    <tfoot>
      {poll.sources.length > 0 && <tr><td colSpan={2}><small>Source: {poll.sources.map((s, i) => <span key={s.label + i}>{i > 0 ? '; ' : ''}{s.url ? <a href={s.url} rel="noopener noreferrer">{s.label}</a> : s.label}</span>)}</small></td></tr>}
      {poll.note && <tr><td colSpan={2}><small>{poll.note}</small></td></tr>}
    </tfoot>
  </table>;
}
