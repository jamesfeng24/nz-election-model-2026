import { useState } from 'react';
import type { ForecastSnapshot } from '../../types/export';
import { dateRange } from '../format';
import { partyLabel } from '../partyNames';
import { INITIAL_POLLS, SeeMore, monthRows } from './MonthRows';
import { pollName } from './pollNames';

type NationalPoll = NonNullable<ForecastSnapshot['evidence']>['nationalPolls'][number];

export function NationalPolls({ snapshot, polls: allPolls }: { snapshot: ForecastSnapshot; polls: NationalPoll[] }) {
  const polls = allPolls.filter((poll) => poll.usedInModel);
  const [expanded, setExpanded] = useState(false);
  const parties = allPolls[0]?.shares.map((share) => share.partyId) ?? [];
  const shown = expanded ? polls : polls.slice(0, INITIAL_POLLS);
  return (
    <>
      <table className="nationalpolls">
        <thead>
          <tr>
            <th>Poll</th>
            <th>Dates</th>
            <th>Sample</th>
            {parties.map((id) => (
              <th key={id}>{partyLabel(snapshot, id)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {monthRows(
            shown,
            (poll) => poll.fieldworkEnd,
            parties.length + 3,
            (poll) => (
              <tr key={poll.id}>
                <td>
                  {poll.publisherUrl ? (
                    <a href={poll.publisherUrl} rel="noopener noreferrer">
                      {pollName(poll)}
                    </a>
                  ) : (
                    pollName(poll)
                  )}
                </td>
                <td>{dateRange(poll.fieldworkStart, poll.fieldworkEnd)}</td>
                <td>{poll.sampleSize ?? '–'}</td>
                {poll.shares.map((share) => (
                  <td key={share.partyId}>
                    {share.percent === null ? '–' : `${share.approximate ? '~' : ''}${share.percent}`}
                  </td>
                ))}
              </tr>
            ),
          )}
        </tbody>
      </table>
      <SeeMore total={polls.length} expanded={expanded} onToggle={() => setExpanded((v) => !v)} />
    </>
  );
}
