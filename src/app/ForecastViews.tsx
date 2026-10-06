import type { ForecastSnapshot } from '../types/export';
import { PLACEHOLDER_RULES_PREFIX } from '../types/export';
import { PRIMARY_INTERVAL_LEVEL, type IntervalSet } from '../types/domain';

const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
const at = (set: IntervalSet, level: number) => set.find(v => v.level === level)!;
const range = (set: IntervalSet, level: number, fmt: (x: number) => string) => `${fmt(at(set, level).lower)} – ${fmt(at(set, level).upper)}`;
const seatsFmt = (x: number) => String(x);
/** Full lower–upper ranges, never ± half-widths: 80% is primary, 50% and 90% are shown beside it. */
function IntervalTable({ caption, rows, fmt }: { caption: string; rows: { key: string; label: string; set: IntervalSet }[]; fmt: (x: number) => string }) {
  return <table><caption>{caption}</caption>
    <thead><tr><th>Party</th><th>Median</th><th>80% range</th><th>50% range</th><th>90% range</th></tr></thead>
    <tbody>{rows.map(r => <tr key={r.key}><td>{r.label}</td><td>{fmt(r.set[0].median)}</td><td>{range(r.set, PRIMARY_INTERVAL_LEVEL, fmt)}</td><td>{range(r.set, 0.5, fmt)}</td><td>{range(r.set, 0.9, fmt)}</td></tr>)}</tbody></table>;
}

export function SnapshotBanner({ snapshot }: { snapshot: ForecastSnapshot }) {
  const synthetic = snapshot.provenance.kind === 'synthetic-fixture';
  return <>
    {synthetic && <p role="alert" className="banner banner-synthetic"><strong>SYNTHETIC DATA.</strong> {snapshot.provenance.kind === 'synthetic-fixture' ? snapshot.provenance.label : ''}</p>}
    {snapshot.calibrationStatus === 'uncalibrated' && <p role="note" className="banner">Uncalibrated output: probabilities and intervals have not been validated and must not be read as calibrated.</p>}
    {snapshot.targetType === 'nowcast'
      ? <p className="banner">Nowcast: what would happen if an election were held under current political conditions (latent state as of the week of {snapshot.modelStateAsOf}). Ranges are central intervals across simulated elections, not margins of error and not ranges for movement before election day ({snapshot.electionDate}).</p>
      : <p role="note" className="banner">Election-day scenario, not the primary nowcast.</p>}
  </>;
}

const partyName = (s: ForecastSnapshot) => (id: string) => s.directory.parties.find(p => p.partyId === id)?.name ?? id;

export function ForecastView({ snapshot }: { snapshot: ForecastSnapshot }) {
  const name = partyName(snapshot);
  return <section aria-label="Nowcast summary">
    <p className="eyebrow">MODEL STATE {snapshot.modelStateAsOf} · DATA CUTOFF {snapshot.dataCutoff.slice(0, 10)} · {snapshot.simulation.completedDraws} DRAWS</p>
    <h2>Party vote</h2>
    <IntervalTable caption={`${snapshot.national.basis}. Median with 80% (primary), 50% and 90% ranges.`} fmt={pct}
      rows={snapshot.national.partyVoteShares.map(p => ({ key: p.partyId, label: name(p.partyId), set: p.share }))} />
    <h2>Seats</h2>
    <IntervalTable caption="Seats per party across simulated elections: median with 80% (primary), 50% and 90% ranges." fmt={seatsFmt}
      rows={snapshot.simulation.partySeatSummaries.map(p => ({ key: p.partyId, label: name(p.partyId), set: p.seats }))} />
    {snapshot.simulation.governmentOutcomes.length > 0 && <><h2>Majority combinations</h2>
      <ul>{snapshot.simulation.governmentOutcomes.map(g => { const c = snapshot.simulation.config.governmentCombinations.find(x => x.id === g.combinationId); return <li key={g.combinationId}>{c?.partyIds.map(name).join(' + ')}: {pct(g.probability)} of draws reach {c?.requiredSeats} seats</li>; })}</ul></>}
    <h2>Limitations</h2><ul>{snapshot.limitations.map(l => <li key={l}>{l}</li>)}</ul>
  </section>;
}

export function ElectoratesView({ snapshot }: { snapshot: ForecastSnapshot }) {
  const name = partyName(snapshot);
  return <section aria-label="Electorate nowcasts">
    {snapshot.directory.electorates.map(e => {
      const prediction = snapshot.simulation.electoratePredictions.find(p => p.electorateId === e.electorateId);
      const missing = snapshot.unavailableElectorates.find(u => u.electorateId === e.electorateId);
      return <article key={e.electorateId}><h2>{e.name}</h2>
        {prediction ? <table><caption>Share of draws won</caption><thead><tr><th>Candidate</th><th>Party</th><th>Won</th></tr></thead>
          <tbody>{[...prediction.candidates].sort((a, b) => b.winProbability - a.winProbability).map(c => { const cand = snapshot.directory.candidates.find(x => x.candidateId === c.candidateId); return <tr key={c.candidateId}><td>{cand?.name ?? c.candidateId}</td><td>{cand?.partyId ? name(cand.partyId) : 'Independent'}</td><td>{pct(c.winProbability)}</td></tr>; })}</tbody></table>
          : <p>No nowcast available: {missing?.reason ?? 'unknown reason'}.</p>}
      </article>;
    })}
  </section>;
}

export function MmpView({ snapshot }: { snapshot: ForecastSnapshot }) {
  const name = partyName(snapshot);
  if (snapshot.mmp.status === 'unavailable') return <p>No seat allocation available: {snapshot.mmp.reason}.</p>;
  const a = snapshot.mmp.exampleDrawAllocation;
  const placeholder = a.rulesVersion.toUpperCase().startsWith(PLACEHOLDER_RULES_PREFIX);
  return <section aria-label="Seat allocation">
    {placeholder && <p role="alert" className="banner banner-synthetic">Placeholder seat rules ({a.rulesVersion}), not the New Zealand electoral rules.</p>}
    <p>One simulated draw shown to illustrate seat accounting; it is not the nowcast. {a.nominalSeats} nominal seats, {a.overhangSeats} overhang, Parliament of {a.parliamentSize}.</p>
    <table><thead><tr><th>Party</th><th>Qualified</th><th>Electorate</th><th>List</th><th>Total</th></tr></thead>
      <tbody>{a.parties.map(p => <tr key={p.partyId}><td>{name(p.partyId)}</td><td>{p.qualified ? 'yes' : 'no'}</td><td>{p.electorateSeats}</td><td>{p.listSeats}</td><td>{p.totalSeats}</td></tr>)}
        <tr><td>Independent</td><td>–</td><td>{a.independentElectorateSeats}</td><td>0</td><td>{a.independentElectorateSeats}</td></tr></tbody></table>
  </section>;
}
