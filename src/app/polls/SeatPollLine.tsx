import type { ForecastSnapshot } from '../../types/export';
import { dateRange, longDate } from '../format';
import { PARTY_CODES, pollName } from './pollNames';

type ElectorateDetail = ForecastSnapshot['electorateDetail'][number];
export type SeatPoll = NonNullable<ElectorateDetail['evidence']>['polls'][number];

/** One seat poll: name, dates, sample, each candidate's figure, whether the forecast used it, and its sources. */
export function SeatPollLine({ poll }: { poll: SeatPoll }) {
  const dates = poll.fieldworkEnd
    ? dateRange(poll.fieldworkStart, poll.fieldworkEnd)
    : `published ${longDate(poll.published!)}`;
  const results = poll.results
    .map((r) => {
      const party = r.party ? ` (${PARTY_CODES[r.party] ?? r.party})` : '';
      return `${r.name}${party} ${r.approximate ? '~' : ''}${r.percent}%`;
    })
    .join(', ');
  return (
    <p className="pollline">
      <strong>{pollName(poll)}</strong>, {dates}
      {poll.sampleSize ? `, ${poll.sampleSize} people` : ''}
      {poll.marginOfError ? `, ±${poll.marginOfError}` : ''}: {results}.{' '}
      <em>{poll.usedInModel ? 'Used in this forecast.' : 'Not used in this forecast.'}</em>
      {poll.sources.length > 0 && (
        <>
          {' '}
          Source:{' '}
          {poll.sources.map((source, i) => (
            <span key={source.label + i}>
              {i > 0 ? '; ' : ''}
              {source.url ? (
                <a href={source.url} rel="noopener noreferrer">
                  {source.label}
                </a>
              ) : (
                source.label
              )}
            </span>
          ))}
          .
        </>
      )}
      {poll.note && (
        <>
          <br />
          <small>{poll.note}</small>
        </>
      )}
    </p>
  );
}
