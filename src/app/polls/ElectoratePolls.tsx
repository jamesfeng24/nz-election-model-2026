import { useState } from 'react';
import type { ForecastSnapshot } from '../../types/export';
import { dateRange, longDate } from '../format';
import { partyLabel } from '../partyNames';
import { INITIAL_POLLS, SeeMore, monthRows } from './MonthRows';
import { PARTY_CODES, pollName } from './pollNames';
import type { SeatPoll } from './SeatPollLine';

interface ElectoratePoll {
  poll: SeatPoll;
  seatId: string;
  seatName: string;
  /** Fieldwork end, or the publication date when fieldwork dates are not stated. */
  date: string;
  /** The seat's newest poll: where a link to the seat's polls lands. */
  firstForSeat: boolean;
}

/** Poll results sit under the party's column; candidates with no party, or independents, go under "Other". */
const columnOf = (code: string | null) => {
  const name = code ? (PARTY_CODES[code] ?? code) : null;
  return name && name !== 'Independent' ? name : 'Other';
};

function electoratePolls(snapshot: ForecastSnapshot): ElectoratePoll[] {
  const polls = snapshot.electorateDetail.flatMap((detail) => {
    const seatId = detail.electorateId;
    const seatName = snapshot.directory.electorates.find((e) => e.electorateId === seatId)?.name ?? seatId;
    return (detail.evidence?.polls ?? []).map((poll) => ({
      poll,
      seatId,
      seatName,
      date: (poll.fieldworkEnd ?? poll.published)!,
      firstForSeat: false,
    }));
  });
  polls.sort((a, b) => b.date.localeCompare(a.date) || a.seatName.localeCompare(b.seatName, 'en-NZ'));
  polls.forEach((entry, i) => {
    entry.firstForSeat = polls.findIndex((other) => other.seatId === entry.seatId) === i;
  });
  return polls;
}

/** The national party columns first, in their order, then any other party, then "Other". */
function partyColumns(polls: ElectoratePoll[], nationalParties: string[]) {
  const present = new Set(polls.flatMap((entry) => entry.poll.results.map((r) => columnOf(r.party))));
  return [
    ...nationalParties.filter((name) => present.has(name)),
    ...[...present].filter((name) => !nationalParties.includes(name) && name !== 'Other'),
    ...(present.has('Other') ? ['Other'] : []),
  ];
}

/** Polls of single electorates, in the same layout as the national polls with an Electorate column. */
export function ElectoratePolls({ snapshot }: { snapshot: ForecastSnapshot }) {
  const polls = electoratePolls(snapshot);
  const nationalParties = (snapshot.evidence?.nationalPolls[0]?.shares ?? []).map((share) =>
    share.partyId === 'other' ? 'Other' : partyLabel(snapshot, share.partyId),
  );
  const columns = partyColumns(polls, nationalParties);
  // A link to #seat-ID (from a seat page) needs that seat's row on the page.
  const [expanded, setExpanded] = useState(() => window.location.hash.startsWith('#seat-'));
  if (polls.length === 0) return <p>No electorate polls.</p>;
  const shown = expanded ? polls : polls.slice(0, INITIAL_POLLS);
  return (
    <>
      <table className="nationalpolls">
        <thead>
          <tr>
            <th>Poll</th>
            <th>Electorate</th>
            <th>Dates</th>
            <th>Sample</th>
            {columns.map((name) => (
              <th key={name}>{name}</th>
            ))}
            <th>In model</th>
          </tr>
        </thead>
        <tbody>
          {monthRows(
            shown,
            (entry) => entry.date,
            columns.length + 5,
            ({ poll, seatId, seatName, firstForSeat }, i) => {
              const sourceUrl = poll.sources.find((source) => source.url)?.url;
              return (
                <tr
                  key={i}
                  id={firstForSeat ? `seat-${seatId}` : undefined}
                  className={poll.usedInModel ? undefined : 'unused'}
                >
                  <td>
                    {sourceUrl ? (
                      <a href={sourceUrl} rel="noopener noreferrer">
                        {pollName(poll)}
                      </a>
                    ) : (
                      pollName(poll)
                    )}
                  </td>
                  <td>
                    <a href={`../electorates/#seat=${seatId}`}>{seatName}</a>
                  </td>
                  <td>
                    {poll.fieldworkEnd
                      ? dateRange(poll.fieldworkStart, poll.fieldworkEnd)
                      : `published ${longDate(poll.published!)}`}
                  </td>
                  <td>{poll.sampleSize ?? '–'}</td>
                  {columns.map((column) => {
                    const result = poll.results.find((r) => columnOf(r.party) === column);
                    return (
                      <td key={column}>
                        {result ? (
                          <span title={result.name}>
                            {result.approximate ? '~' : ''}
                            {result.percent}
                            <span className="sr-only"> ({result.name})</span>
                          </span>
                        ) : (
                          '–'
                        )}
                      </td>
                    );
                  })}
                  <td>{poll.usedInModel ? 'Yes' : <span title={poll.note ?? undefined}>No</span>}</td>
                </tr>
              );
            },
          )}
        </tbody>
      </table>
      <SeeMore total={polls.length} expanded={expanded} onToggle={() => setExpanded((v) => !v)} />
    </>
  );
}
