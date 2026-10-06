import type { ForecastSnapshot } from '../types/export';
import { PLACEHOLDER_RULES_PREFIX } from '../types/export';

const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

export function SnapshotBanner({ snapshot }: { snapshot: ForecastSnapshot }) {
  const synthetic = snapshot.provenance.kind === 'synthetic-fixture';
  return <>
    {synthetic && <p role="alert" className="banner banner-synthetic"><strong>SYNTHETIC DATA.</strong> {snapshot.provenance.kind === 'synthetic-fixture' ? snapshot.provenance.label : ''}</p>}
    {snapshot.calibrationStatus === 'uncalibrated' && <p role="note" className="banner">Uncalibrated output: probabilities and intervals have not been validated and must not be read as calibrated forecasts.</p>}
  </>;
}

const partyName = (s: ForecastSnapshot) => (id: string) => s.directory.parties.find(p => p.partyId === id)?.name ?? id;

export function ForecastView({ snapshot }: { snapshot: ForecastSnapshot }) {
  const name = partyName(snapshot);
  return <section aria-label="Forecast summary">
    <p className="eyebrow">DATA CUTOFF {snapshot.dataCutoff.slice(0, 10)} · {snapshot.simulation.completedDraws} DRAWS</p>
    <h2>Party vote</h2>
    <table><caption>{snapshot.national.basis}. Median and {Math.round(snapshot.national.partyVoteShares[0].share.level * 100)}% interval.</caption>
      <thead><tr><th>Party</th><th>Median</th><th>Interval</th></tr></thead>
      <tbody>{snapshot.national.partyVoteShares.map(p => <tr key={p.partyId}><td>{name(p.partyId)}</td><td>{pct(p.share.median)}</td><td>{pct(p.share.lower)} – {pct(p.share.upper)}</td></tr>)}</tbody></table>
    <h2>Seats</h2>
    <table><caption>Seats per party across draws: median and 90% interval.</caption>
      <thead><tr><th>Party</th><th>Median</th><th>Interval</th></tr></thead>
      <tbody>{snapshot.simulation.partySeatSummaries.map(p => <tr key={p.partyId}><td>{name(p.partyId)}</td><td>{p.seats.median}</td><td>{p.seats.lower} – {p.seats.upper}</td></tr>)}</tbody></table>
    {snapshot.simulation.governmentOutcomes.length > 0 && <><h2>Majority combinations</h2>
      <ul>{snapshot.simulation.governmentOutcomes.map(g => { const c = snapshot.simulation.config.governmentCombinations.find(x => x.id === g.combinationId); return <li key={g.combinationId}>{c?.partyIds.map(name).join(' + ')}: {pct(g.probability)} of draws reach {c?.requiredSeats} seats</li>; })}</ul></>}
    <h2>Limitations</h2><ul>{snapshot.limitations.map(l => <li key={l}>{l}</li>)}</ul>
  </section>;
}

export function ElectoratesView({ snapshot }: { snapshot: ForecastSnapshot }) {
  const name = partyName(snapshot);
  return <section aria-label="Electorate forecasts">
    {snapshot.directory.electorates.map(e => {
      const prediction = snapshot.simulation.electoratePredictions.find(p => p.electorateId === e.electorateId);
      const missing = snapshot.unavailableElectorates.find(u => u.electorateId === e.electorateId);
      return <article key={e.electorateId}><h2>{e.name}</h2>
        {prediction ? <table><caption>Share of draws won</caption><thead><tr><th>Candidate</th><th>Party</th><th>Won</th></tr></thead>
          <tbody>{[...prediction.candidates].sort((a, b) => b.winProbability - a.winProbability).map(c => { const cand = snapshot.directory.candidates.find(x => x.candidateId === c.candidateId); return <tr key={c.candidateId}><td>{cand?.name ?? c.candidateId}</td><td>{cand?.partyId ? name(cand.partyId) : 'Independent'}</td><td>{pct(c.winProbability)}</td></tr>; })}</tbody></table>
          : <p>No forecast available: {missing?.reason ?? 'unknown reason'}.</p>}
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
    <p>One simulated draw shown to illustrate seat accounting; it is not a forecast. {a.nominalSeats} nominal seats, {a.overhangSeats} overhang, Parliament of {a.parliamentSize}.</p>
    <table><thead><tr><th>Party</th><th>Qualified</th><th>Electorate</th><th>List</th><th>Total</th></tr></thead>
      <tbody>{a.parties.map(p => <tr key={p.partyId}><td>{name(p.partyId)}</td><td>{p.qualified ? 'yes' : 'no'}</td><td>{p.electorateSeats}</td><td>{p.listSeats}</td><td>{p.totalSeats}</td></tr>)}
        <tr><td>Independent</td><td>–</td><td>{a.independentElectorateSeats}</td><td>0</td><td>{a.independentElectorateSeats}</td></tr></tbody></table>
  </section>;
}
