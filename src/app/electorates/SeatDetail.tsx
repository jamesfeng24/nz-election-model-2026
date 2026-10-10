import type { ForecastSnapshot } from '../../types/export';
import { chance, pct } from '../format';
import { intervalAt, mainRange } from '../intervals';
import { partyColour } from '../partyColours';
import { candidatePartyName } from '../partyNames';
import { SeatPollLine } from '../polls/SeatPollLine';
import { RangeBar, ShareAxis } from './RangeBar';
import { chanceRange } from './rows';

const UNCERTAINTY_NOTES: Record<string, string> = {
  'maori-layer': 'Māori electorates are modelled separately, with fewer polls, so ranges here are wider.',
  exceptional: 'This seat has unusual local circumstances, so the model allows wider uncertainty.',
};

const RANGE_NOTE =
  "Chances are a range between two estimates: one takes the seat polls at face value, the other allows for past Māori seat polls having ended up further from the results than the model's uncertainty implied.";

/** Candidates, chances, vote-share ranges and polls for one electorate. */
export function SeatDetail({ snapshot, seatId }: { snapshot: ForecastSnapshot; seatId: string }) {
  const seat = snapshot.directory.electorates.find((e) => e.electorateId === seatId)!;
  const prediction = snapshot.simulation.electoratePredictions.find((p) => p.electorateId === seatId);
  const detail = snapshot.electorateDetail.find((d) => d.electorateId === seatId);

  if (!prediction) {
    const reason = snapshot.unavailableElectorates.find((u) => u.electorateId === seatId)?.reason ?? 'unknown reason';
    return (
      <section aria-labelledby="seat-heading">
        <h2 id="seat-heading">{seat.name}</h2>
        <p>No forecast available: {reason}.</p>
      </section>
    );
  }

  const rows = [...prediction.candidates]
    .sort((a, b) => b.winProbability - a.winProbability)
    .map((entry) => ({
      entry,
      candidate: snapshot.directory.candidates.find((c) => c.candidateId === entry.candidateId),
      share: detail?.candidates.find((d) => d.candidateId === entry.candidateId),
    }))
    .map((row) => ({ ...row, range: chanceRange(row.entry.winProbability, detail, row.entry.candidateId) }));
  const hasRange = rows.some((row) => row.range);
  const widestUpper = Math.max(0.1, ...rows.map((r) => (r.share ? mainRange(r.share.share).upper : 0)));
  const axisMax = Math.min(1, Math.ceil(widestUpper * 20) / 20);
  const uncertaintyNote =
    detail && detail.uncertaintyClass !== 'ordinary' && UNCERTAINTY_NOTES[detail.uncertaintyClass];
  const rangeLabel = (name: string | undefined, share: NonNullable<(typeof rows)[number]['share']>) => {
    const range50 = intervalAt(share.share, 0.5);
    const range80 = mainRange(share.share);
    return `${name}: median ${pct(share.share[0].median)}, 50% range ${pct(range50.lower)} to ${pct(range50.upper)}, 80% range ${pct(range80.lower)} to ${pct(range80.upper)}`;
  };

  return (
    <section aria-labelledby="seat-heading" className="seat">
      <h2 id="seat-heading">
        {seat.name}
        {seat.kind === 'maori' ? ' (Māori electorate)' : ''}
      </h2>
      {snapshot.incumbency && !rows.some((r) => r.candidate?.incumbent) && (
        <p className="note">No sitting MP for this seat is standing here.</p>
      )}
      {uncertaintyNote && <p className="note">{uncertaintyNote}</p>}
      {hasRange && <p className="note">{RANGE_NOTE}</p>}
      <table className="candidates">
        <caption>Chance of winning and share of the electorate vote</caption>
        <thead>
          <tr>
            <th>Candidate</th>
            <th>Chance of winning</th>
            <th>Median share</th>
            <th>Share of electorate vote</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ entry, candidate, share, range }) => (
            <tr key={entry.candidateId}>
              <td>
                <strong>{candidate?.name ?? entry.candidateId}</strong>
                {candidate?.incumbent && (
                  <>
                    {' '}
                    <span className="incumbent" title="The sitting MP for this seat">
                      Incumbent
                    </span>
                  </>
                )}
                <br />
                <small>{candidatePartyName(snapshot, candidate)}</small>
              </td>
              <td>
                <span className="odds">{chance(entry.winProbability, range)}</span>
              </td>
              <td className="num">
                <strong>{share ? pct(share.share[0].median) : '–'}</strong>
              </td>
              <td className="barcell">
                {share ? (
                  <RangeBar
                    colour={partyColour(candidate?.partyId)}
                    set={share.share}
                    axisMax={axisMax}
                    label={rangeLabel(candidate?.name, share)}
                  />
                ) : (
                  <small>Not available</small>
                )}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={3} />
            <td className="axiscell">
              <ShareAxis axisMax={axisMax} />
            </td>
          </tr>
        </tfoot>
      </table>
      <p className="legend">
        Bars show each candidate's share of the electorate vote on the scale below. Hover the solid part for the 50%
        range and the light part for the 80% range; the median is the line and the number. Ranges cover half and
        four-fifths of simulated elections.
      </p>
      <h3>Polls</h3>
      {!detail?.evidence ? (
        <p>No seat poll information for this forecast.</p>
      ) : (
        <>
          <p>{detail.evidence.basis}</p>
          {detail.evidence.polls.length === 0 ? (
            <p>No poll of this seat.</p>
          ) : (
            <>
              {detail.evidence.polls.map((poll, i) => (
                <SeatPollLine key={i} poll={poll} />
              ))}
              {detail.evidence.polls.some((poll) => poll.usedInModel) && (
                <p>
                  <a href={`../polls/#seat-${seatId}`}>See all polls</a>
                </p>
              )}
            </>
          )}
        </>
      )}
      <p>
        <small>
          Chance of winning is the share of simulated elections the candidate wins. Simulation error is under one
          percentage point.
        </small>
      </p>
    </section>
  );
}
