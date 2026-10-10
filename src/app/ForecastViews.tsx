import type { ForecastSnapshot } from '../types/export';
import { partyLabel } from './partyNames';
import { PRIMARY_INTERVAL_LEVEL, type IntervalSet } from '../types/domain';
import { longDate, pct, prob } from './format';
import { SeatChart } from './SeatChart';
import { SeatBars, OverhangNote } from './SeatBars';
import { SupportTrend } from './SupportTrend';

const at = (set: IntervalSet, level: number) => set.find(v => v.level === level)!;
const range = (set: IntervalSet, level: number, fmt: (x: number) => string) => `${fmt(at(set, level).lower)} – ${fmt(at(set, level).upper)}`;
const whole = (x: number) => String(x);
/** Full lower–upper ranges, never ± half-widths: the main page shows the median and the 80% range only. */
function IntervalTable({ caption, label, rows, fmt }: { caption: string; label: string; rows: { key: string; label: string; set: IntervalSet }[]; fmt: (x: number) => string }) {
  return <table><caption>{caption}</caption>
    <thead><tr><th>{label}</th><th>Median</th><th>80% range</th></tr></thead>
    <tbody>{rows.map(r => <tr key={r.key}><td>{r.label}</td><td>{fmt(r.set[0].median)}</td><td>{range(r.set, PRIMARY_INTERVAL_LEVEL, fmt)}</td></tr>)}</tbody></table>;
}

export function SnapshotBanner({ snapshot }: { snapshot: ForecastSnapshot }) {
  const synthetic = snapshot.provenance.kind === 'synthetic-fixture';
  return <>
    {synthetic && <p role="alert" className="banner banner-synthetic"><strong>SYNTHETIC DATA.</strong> {snapshot.provenance.kind === 'synthetic-fixture' ? snapshot.provenance.label : ''}</p>}
    {snapshot.targetType === 'nowcast'
      ? <p className="banner"><strong>Forecast if the election were held today</strong> · Updated {longDate(snapshot.dataCutoff)}</p>
      : <p role="note" className="banner">Election-day scenario, not the primary forecast.</p>}
    {snapshot.adjustments && <p className="banner">Includes manual adjustments by {snapshot.adjustments.by}. <a href="../methodology/">What was changed and why</a>.</p>}
  </>;
}

const partyName = (s: ForecastSnapshot) => (id: string) => partyLabel(s, id);

function Governing({ snapshot }: { snapshot: ForecastSnapshot }) {
  if (snapshot.seatLayer.status !== 'available') return null;
  const { blocs, scenarios } = snapshot.seatLayer.summary;
  const hung = scenarios.find(s => s.id === 'hung');
  const group = (ids: string[]) => ids.map(id => partyLabel(snapshot, id)).join(' + ');
  return <>
    <h2>Chance of a majority</h2>
    <p>Seat arithmetic only. It does not predict who would govern together.</p>
    <table><caption>Chance each group wins more than half of Parliament's seats</caption>
      <thead><tr><th>Group</th><th>Chance of a majority</th></tr></thead>
      <tbody>{blocs.map(b => <tr key={b.id}><td>{group(b.partyIds)}</td><td>{prob(b.probMajority.p)}</td></tr>)}
        {hung && <tr><td>No majority<br /><small>Neither National + ACT + NZ First nor Labour + Greens + Te Pāti Māori reaches a majority</small></td><td>{prob(hung.probability.p)}</td></tr>}</tbody></table>
  </>;
}

function Electorates({ snapshot }: { snapshot: ForecastSnapshot }) {
  const name = partyName(snapshot);
  const electorates = [...snapshot.directory.electorates].sort((a, b) => a.name.localeCompare(b.name, 'en-NZ'));
  const cell = (candidateId: string, p: number) => {
    const c = snapshot.directory.candidates.find(x => x.candidateId === candidateId);
    return <>{c?.name ?? candidateId}{c?.incumbent ? ' – incumbent' : ''} ({c?.partyId ? name(c.partyId) : c?.partyLabel ?? 'Independent'}) {prob(p)}</>;
  };
  return <details><summary>All {electorates.length} electorates</summary>
    <table><caption>Chance of winning each electorate, two most likely candidates</caption>
      <thead><tr><th>Electorate</th><th>Most likely</th><th>Next</th><th>Range of outcomes</th></tr></thead>
      <tbody>{electorates.map(e => {
        const prediction = snapshot.simulation.electoratePredictions.find(p => p.electorateId === e.electorateId);
        if (!prediction) return <tr key={e.electorateId}><td>{e.name}</td><td colSpan={3}>No forecast available: {snapshot.unavailableElectorates.find(u => u.electorateId === e.electorateId)?.reason ?? 'unknown reason'}</td></tr>;
        const [first, second] = [...prediction.candidates].sort((a, b) => b.winProbability - a.winProbability);
        const cls = snapshot.electorateDetail.find(d => d.electorateId === e.electorateId)?.uncertaintyClass;
        return <tr key={e.electorateId}><td><a href={`../electorates/#seat=${e.electorateId}`}>{e.name}</a>{e.kind === 'maori' ? ' (Māori)' : ''}</td><td>{cell(first.candidateId, first.winProbability)}</td>
          <td>{second ? cell(second.candidateId, second.winProbability) : '–'}</td><td>{cls === 'exceptional' ? 'Wider' : cls === 'maori-layer' ? 'Wider (fewer polls)' : 'Standard'}</td></tr>;
      })}</tbody></table>
    <p><small>"Wider" marks seats with unusual local circumstances or thin polling, where the model is less certain.</small></p>
  </details>;
}

export function ForecastView({ snapshot, trend = null }: { snapshot: ForecastSnapshot; trend?: React.ReactNode }) {
  const name = partyName(snapshot);
  const seats = snapshot.seatLayer.status === 'available'
    ? snapshot.seatLayer.summary.parties.map(p => ({ key: p.partyId, label: name(p.partyId), set: p.seats }))
    : snapshot.simulation.partySeatSummaries.map(p => ({ key: p.partyId, label: name(p.partyId), set: p.seats }));
  return <section aria-label="Forecast summary">
    <h2>Expected seats</h2>
    <SeatChart snapshot={snapshot} />
    {snapshot.seatLayer.status === 'available'
      ? <><SeatBars snapshot={snapshot} /><OverhangNote snapshot={snapshot} /></>
      : <IntervalTable caption="Seats per party across simulated elections: median with 80% range." label="Party" fmt={whole} rows={seats} />}
    <Governing snapshot={snapshot} />
    <h2>Party vote</h2>
    <IntervalTable caption={`${snapshot.national.basis}. Median with 80% range.`} label="Party" fmt={pct}
      rows={snapshot.national.partyVoteShares.map(p => ({ key: p.partyId, label: name(p.partyId), set: p.share }))} />
    {snapshot.evidence?.trend && <><h2>How support has moved</h2><SupportTrend snapshot={snapshot} /></>}
    {trend && <><h2>How the odds have moved</h2>{trend}</>}
    <h2>Electorates</h2>
    <p><a href="../electorates/">Look up any seat</a> for candidate chances, vote shares and polls.</p>
    <Electorates snapshot={snapshot} />
    <p>Updated weekly until election day. <a href="../methodology/">How it works and where the data comes from</a>.</p>
  </section>;
}
