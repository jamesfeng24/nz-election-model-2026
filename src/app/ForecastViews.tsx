import type { ReactNode } from 'react';
import type { IntervalSet } from '../types/domain';
import type { ForecastSnapshot } from '../types/export';
import { longDate, pct, prob } from './format';
import { mainRange } from './intervals';
import { partyLabel } from './partyNames';
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
        <caption>
          Chance each group wins more than half of Parliament's seats, with the group's seats across simulated elections
        </caption>
        <thead>
          <tr>
            <th>Group</th>
            <th>Chance of a majority</th>
            <th>Median seats</th>
            <th>80% range</th>
          </tr>
        </thead>
        <tbody>
          {blocs.map((bloc) => {
            const range = mainRange(bloc.seats);
            return (
              <tr key={bloc.id}>
                <td>{groupName(bloc.partyIds)}</td>
                <td>{prob(bloc.probMajority.p)}</td>
                <td>{bloc.seats[0].median}</td>
                <td>
                  {range.lower} – {range.upper}
                </td>
              </tr>
            );
          })}
          {noMajority && (
            <tr>
              <td>
                No majority
                <br />
                <small>Neither National + ACT + NZ First nor Labour + Greens + Te Pāti Māori reaches a majority</small>
              </td>
              <td>{prob(noMajority.probability.p)}</td>
              <td>–</td>
              <td>–</td>
            </tr>
          )}
        </tbody>
      </table>
    </>
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
      <Governing snapshot={snapshot} />
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
      <p>
        Updated weekly until election day. <a href="../methodology/">How it works and where the data comes from</a>.
      </p>
    </section>
  );
}
