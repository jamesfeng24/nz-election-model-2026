import { useState } from 'react';
import type { ForecastSnapshot } from '../../types/export';
import { pct, prob } from '../format';
import { intervalAt, mainRange } from '../intervals';
import { partyColour } from '../partyColours';
import { candidatePartyName, isMainParty } from '../partyNames';
import { SeatPollLine } from '../polls/SeatPollLine';
import { RangeBar, ShareAxis } from './RangeBar';

/** A minor candidate sits under "Other" when its chance of winning is below 1% and its median share below 5%. */
const MINOR_WIN = 0.01;
const MINOR_SHARE = 0.05;

/** Candidates, chances, vote-share ranges and polls for one electorate. */
export function SeatDetail({ snapshot, seatId }: { snapshot: ForecastSnapshot; seatId: string }) {
  const [otherOpen, setOtherOpen] = useState(false);
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
    }));
  const widestUpper = Math.max(0.1, ...rows.map((r) => (r.share ? mainRange(r.share.share).upper : 0)));
  const axisMax = Math.min(1, Math.ceil(widestUpper * 20) / 20);
  const rangeLabel = (name: string | undefined, share: NonNullable<(typeof rows)[number]['share']>) => {
    const range50 = intervalAt(share.share, 0.5);
    const range80 = mainRange(share.share);
    return `${name}: median ${pct(share.share[0].median)}, 50% range ${pct(range50.lower)} to ${pct(range50.upper)}, 80% range ${pct(range80.lower)} to ${pct(range80.upper)}`;
  };

  // Two or more minor candidates fold into one "Other" row; a single one is simply listed.
  const isMinor = (r: (typeof rows)[number]) =>
    !isMainParty(r.candidate) && r.entry.winProbability < MINOR_WIN && (r.share?.share[0].median ?? 0) < MINOR_SHARE;
  const minor = rows.filter(isMinor);
  const grouped = minor.length >= 2;
  const listed = grouped ? rows.filter((r) => !minor.includes(r)) : rows;
  const otherChance = minor.reduce((sum, r) => sum + r.entry.winProbability, 0);

  const candidateRow = ({ entry, candidate, share }: (typeof rows)[number], className?: string) => (
    <tr key={entry.candidateId} className={className}>
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
      <td data-label="Chance">
        <span className="odds">{prob(entry.winProbability)}</span>
      </td>
      <td className="num" data-label="Median">
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
  );

  return (
    <section aria-labelledby="seat-heading" className="seat">
      <h2 id="seat-heading">
        {seat.name}
        {seat.kind === 'maori' ? ' (Māori electorate)' : ''}
      </h2>
      {snapshot.incumbency && !rows.some((r) => r.candidate?.incumbent) && (
        <p className="note">No sitting MP for this seat is standing here.</p>
      )}
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
          {listed.map((row) => candidateRow(row))}
          {grouped && (
            <tr className="otherrow">
              <td>
                <button
                  type="button"
                  className="otherbutton"
                  aria-expanded={otherOpen}
                  onClick={() => setOtherOpen((open) => !open)}
                >
                  <strong>Other</strong> <small>({minor.length} candidates)</small>
                  <span aria-hidden="true" className="otherchevron">
                    {otherOpen ? ' ▴' : ' ▾'}
                  </span>
                </button>
                <br />
                <small>Minor parties and independents</small>
              </td>
              <td data-label="Chance">
                <span className="odds">{prob(otherChance)}</span>
              </td>
              <td className="num" data-label="Median">
                –
              </td>
              <td className="barcell">
                <small>{otherOpen ? 'Shown below' : 'Select to show each candidate'}</small>
              </td>
            </tr>
          )}
          {grouped && otherOpen && minor.map((row) => candidateRow(row, 'otherchild'))}
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
