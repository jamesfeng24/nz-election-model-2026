import type { ReactNode } from 'react';
import type { IntervalSet } from '../types/domain';
import type { ForecastSnapshot } from '../types/export';
import { longDate, pct, prob } from './format';
import { mainRange } from './intervals';
import { candidatePartyName, partyLabel } from './partyNames';
import { SeatBars, OverhangNote } from './SeatBars';
import { SeatChart } from './SeatChart';
import { SupportTrend } from './SupportTrend';

const whole = (value: number) => String(value);

/** Median and 80% range per row, always as lower – upper rather than ± half-widths. */
function IntervalTable({
  caption,
  label,
  rows,
  format,
}: {
  caption: string;
  label: string;
  rows: { key: string; label: string; set: IntervalSet }[];
  format: (value: number) => string;
}) {
  return (
    <table>
      <caption>{caption}</caption>
      <thead>
        <tr>
          <th>{label}</th>
          <th>Median</th>
          <th>80% range</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const range = mainRange(row.set);
          return (
            <tr key={row.key}>
              <td>{row.label}</td>
              <td>{format(row.set[0].median)}</td>
              <td>
                {format(range.lower)} – {format(range.upper)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export function SnapshotBanner({ snapshot }: { snapshot: ForecastSnapshot }) {
  return (
    <>
      {snapshot.provenance.kind === 'synthetic-fixture' && (
        <p role="alert" className="banner banner-synthetic">
          <strong>SYNTHETIC DATA.</strong> {snapshot.provenance.label}
        </p>
      )}
      {snapshot.targetType === 'nowcast' ? (
        <p className="banner">
          <strong>Forecast if the election were held today</strong> · Updated {longDate(snapshot.dataCutoff)}
        </p>
      ) : (
        <p role="note" className="banner">
          Election-day scenario, not the primary forecast.
        </p>
      )}
      {snapshot.adjustments && (
        <p className="banner">
          Includes manual adjustments by {snapshot.adjustments.by}.{' '}
          <a href="../methodology/">What was changed and why</a>.
        </p>
      )}
    </>
  );
}

function Governing({ snapshot }: { snapshot: ForecastSnapshot }) {
  if (snapshot.seatLayer.status !== 'available') return null;
  const { blocs, scenarios } = snapshot.seatLayer.summary;
  const noMajority = scenarios.find((s) => s.id === 'hung');
  const groupName = (partyIds: string[]) => partyIds.map((id) => partyLabel(snapshot, id)).join(' + ');
  return (
    <>
      <h2>Chance of a majority</h2>
      <p>Seat arithmetic only. It does not predict who would govern together.</p>
      <table>
        <caption>Chance each group wins more than half of Parliament's seats</caption>
        <thead>
          <tr>
            <th>Group</th>
            <th>Chance of a majority</th>
          </tr>
        </thead>
        <tbody>
          {blocs.map((bloc) => (
            <tr key={bloc.id}>
              <td>{groupName(bloc.partyIds)}</td>
              <td>{prob(bloc.probMajority.p)}</td>
            </tr>
          ))}
          {noMajority && (
            <tr>
              <td>
                No majority
                <br />
                <small>Neither National + ACT + NZ First nor Labour + Greens + Te Pāti Māori reaches a majority</small>
              </td>
              <td>{prob(noMajority.probability.p)}</td>
            </tr>
          )}
        </tbody>
      </table>
    </>
  );
}

const UNCERTAINTY_LABELS = {
  exceptional: 'Wider',
  'maori-layer': 'Wider (fewer polls)',
  ordinary: 'Standard',
} as const;

/** Every electorate with its two most likely winners, folded away by default. */
function ElectorateSummary({ snapshot }: { snapshot: ForecastSnapshot }) {
  const electorates = [...snapshot.directory.electorates].sort((a, b) => a.name.localeCompare(b.name, 'en-NZ'));
  const candidateCell = (candidateId: string, winProbability: number) => {
    const candidate = snapshot.directory.candidates.find((c) => c.candidateId === candidateId);
    return (
      <>
        {candidate?.name ?? candidateId}
        {candidate?.incumbent ? ' – incumbent' : ''} ({candidatePartyName(snapshot, candidate)}) {prob(winProbability)}
      </>
    );
  };
  return (
    <details>
      <summary>All {electorates.length} electorates</summary>
      <table>
        <caption>Chance of winning each electorate, two most likely candidates</caption>
        <thead>
          <tr>
            <th>Electorate</th>
            <th>Most likely</th>
            <th>Next</th>
            <th>Range of outcomes</th>
          </tr>
        </thead>
        <tbody>
          {electorates.map((electorate) => {
            const { electorateId } = electorate;
            const prediction = snapshot.simulation.electoratePredictions.find((p) => p.electorateId === electorateId);
            if (!prediction) {
              const reason =
                snapshot.unavailableElectorates.find((u) => u.electorateId === electorateId)?.reason ??
                'unknown reason';
              return (
                <tr key={electorateId}>
                  <td>{electorate.name}</td>
                  <td colSpan={3}>No forecast available: {reason}</td>
                </tr>
              );
            }
            const [first, second] = [...prediction.candidates].sort((a, b) => b.winProbability - a.winProbability);
            const uncertaintyClass = snapshot.electorateDetail.find(
              (d) => d.electorateId === electorateId,
            )?.uncertaintyClass;
            return (
              <tr key={electorateId}>
                <td>
                  <a href={`../electorates/#seat=${electorateId}`}>{electorate.name}</a>
                  {electorate.kind === 'maori' ? ' (Māori)' : ''}
                </td>
                <td>{candidateCell(first.candidateId, first.winProbability)}</td>
                <td>{second ? candidateCell(second.candidateId, second.winProbability) : '–'}</td>
                <td>{UNCERTAINTY_LABELS[uncertaintyClass ?? 'ordinary']}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p>
        <small>
          "Wider" marks seats with unusual local circumstances or thin polling, where the model is less certain.
        </small>
      </p>
    </details>
  );
}

export function ForecastView({ snapshot, trend = null }: { snapshot: ForecastSnapshot; trend?: ReactNode }) {
  const seatRows =
    snapshot.seatLayer.status === 'available'
      ? []
      : snapshot.simulation.partySeatSummaries.map((p) => ({
          key: p.partyId,
          label: partyLabel(snapshot, p.partyId),
          set: p.seats,
        }));
  return (
    <section aria-label="Forecast summary">
      <h2>Expected seats</h2>
      <SeatChart snapshot={snapshot} />
      {snapshot.seatLayer.status === 'available' ? (
        <>
          <SeatBars snapshot={snapshot} />
          <OverhangNote snapshot={snapshot} />
        </>
      ) : (
        <IntervalTable
          caption="Seats per party across simulated elections: median with 80% range."
          label="Party"
          format={whole}
          rows={seatRows}
        />
      )}
      <Governing snapshot={snapshot} />
      <h2>Party vote</h2>
      <IntervalTable
        caption={`${snapshot.national.basis}. Median with 80% range.`}
        label="Party"
        format={pct}
        rows={snapshot.national.partyVoteShares.map((p) => ({
          key: p.partyId,
          label: partyLabel(snapshot, p.partyId),
          set: p.share,
        }))}
      />
      {snapshot.evidence?.trend && (
        <>
          <h2>How support has moved</h2>
          <SupportTrend snapshot={snapshot} />
        </>
      )}
      {trend && (
        <>
          <h2>How the odds have moved</h2>
          {trend}
        </>
      )}
      <h2>Electorates</h2>
      <p>
        <a href="../electorates/">Look up any seat</a> for candidate chances, vote shares and polls.
      </p>
      <ElectorateSummary snapshot={snapshot} />
      <p>
        Updated weekly until election day. <a href="../methodology/">How it works and where the data comes from</a>.
      </p>
    </section>
  );
}
