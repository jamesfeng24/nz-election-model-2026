import { useEffect, useMemo, useState } from 'react';
import { partyLabel } from './partyNames';
import type { ForecastSnapshot } from '../types/export';
import { PRIMARY_INTERVAL_LEVEL, type IntervalSet } from '../types/domain';
import { pct, prob } from './format';
import { SeatPollLine } from './PollTables';
import { ElectorateMap } from './ElectorateMap';
import { COLOURS } from './SeatChart';

type Sort = 'name' | 'close' | 'wide';
const level = (set: IntervalSet, l: number) => set.find(v => v.level === l)!;
const seatFromHash = () => new URLSearchParams(window.location.hash.slice(1)).get('seat');

interface Row { id: string; name: string; kind: 'general' | 'maori'; leader: string; leaderParty: string | null; leaderPartyName: string; leaderP: number; second: number; wide: boolean; available: boolean }

function useRows(snapshot: ForecastSnapshot): Row[] {
  return useMemo(() => snapshot.directory.electorates.map(e => {
    const prediction = snapshot.simulation.electoratePredictions.find(p => p.electorateId === e.electorateId);
    const sorted = prediction ? [...prediction.candidates].sort((a, b) => b.winProbability - a.winProbability) : [];
    const cls = snapshot.electorateDetail.find(d => d.electorateId === e.electorateId)?.uncertaintyClass;
    const leader = snapshot.directory.candidates.find(c => c.candidateId === sorted[0]?.candidateId);
    return { id: e.electorateId, name: e.name, kind: e.kind, leader: leader?.name ?? '', leaderParty: leader?.partyId ?? null, leaderPartyName: leader?.partyId ? partyLabel(snapshot, leader.partyId) : leader?.partyLabel ?? 'Independent', leaderP: sorted[0]?.winProbability ?? 0, second: sorted[1]?.winProbability ?? 0, wide: cls === 'exceptional' || cls === 'maori-layer', available: !!prediction };
  }), [snapshot]);
}

/** A share range drawn on a shared axis: the 80% range in a light shade, the 50% range darker, the median as a tick. */
function RangeBar({ set, axisMax, label, colour }: { set: IntervalSet; axisMax: number; label: string; colour: string }) {
  const x = (v: number) => `${(v / axisMax) * 100}%`;
  const r80 = level(set, PRIMARY_INTERVAL_LEVEL), r50 = level(set, 0.5);
  return <div className="rangebar" role="img" aria-label={label}>
    <span className="r80" style={{ background: colour, left: x(r80.lower), width: `calc(${x(r80.upper)} - ${x(r80.lower)})` }} />
    <span className="r50" style={{ background: colour, left: x(r50.lower), width: `calc(${x(r50.upper)} - ${x(r50.lower)})` }} />
    <span className="median" style={{ left: x(r50.median) }} />
  </div>;
}

function SeatDetail({ snapshot, seatId }: { snapshot: ForecastSnapshot; seatId: string }) {
  const seat = snapshot.directory.electorates.find(e => e.electorateId === seatId)!;
  const prediction = snapshot.simulation.electoratePredictions.find(p => p.electorateId === seatId);
  const detail = snapshot.electorateDetail.find(d => d.electorateId === seatId);
  const partyName = (id: string | null) => (id ? partyLabel(snapshot, id) : undefined);
  if (!prediction) return <section aria-labelledby="seat-heading"><h2 id="seat-heading">{seat.name}</h2><p>No forecast available: {snapshot.unavailableElectorates.find(u => u.electorateId === seatId)?.reason ?? 'unknown reason'}.</p></section>;
  const rows = [...prediction.candidates].sort((a, b) => b.winProbability - a.winProbability).map(c => {
    const cand = snapshot.directory.candidates.find(x => x.candidateId === c.candidateId);
    return { c, cand, share: detail?.candidates.find(d => d.candidateId === c.candidateId) };
  });
  const top = Math.max(0.1, ...rows.map(r => (r.share ? level(r.share.share, 0.8).upper : 0)));
  const axisMax = Math.min(1, Math.ceil(top * 20) / 20);
  return <section aria-labelledby="seat-heading" className="seat">
    <h2 id="seat-heading">{seat.name}{seat.kind === 'maori' ? ' (Māori electorate)' : ''}</h2>
    {detail && detail.uncertaintyClass !== 'ordinary' && <p className="note">{detail.uncertaintyClass === 'maori-layer' ? 'Māori electorates are modelled separately, with fewer polls, so ranges here are wider.' : 'This seat has unusual local circumstances, so the model allows wider uncertainty.'}</p>}
    <table className="candidates"><caption>Chance of winning and share of the electorate vote</caption>
      <thead><tr><th>Candidate</th><th>Chance of winning</th><th>Share of electorate vote</th></tr></thead>
      <tbody>{rows.map(({ c, cand, share }) => <tr key={c.candidateId}>
        <td><strong>{cand?.name ?? c.candidateId}</strong><br /><small>{partyName(cand?.partyId ?? null) ?? cand?.partyLabel ?? 'Independent'}</small></td>
        <td><span className="odds">{prob(c.winProbability)}</span></td>
        <td>{share ? <><RangeBar colour={(cand?.partyId && COLOURS[cand.partyId]) || '#8b8f94'} set={share.share} axisMax={axisMax} label={`${cand?.name}: median ${pct(share.share[0].median)}, 50% range ${pct(level(share.share, 0.5).lower)} to ${pct(level(share.share, 0.5).upper)}, 80% range ${pct(level(share.share, 0.8).lower)} to ${pct(level(share.share, 0.8).upper)}`} />
          <small>{pct(share.share[0].median)} median · 50%: {pct(level(share.share, 0.5).lower)} – {pct(level(share.share, 0.5).upper)} · 80%: {pct(level(share.share, 0.8).lower)} – {pct(level(share.share, 0.8).upper)}</small></> : <small>Share ranges not available</small>}</td></tr>)}</tbody></table>
    <p className="legend"><span className="key r50" /> 50% range (solid) <span className="key r80" /> 80% range (pale) <span className="key tick" /> median, in each candidate's party colour. Bars run from 0% to {Math.round(axisMax * 100)}% of the vote. The ranges cover half and four-fifths of simulated elections.</p>
    <h3>Polls</h3>
    {!detail?.evidence ? <p>No seat poll information is attached to this forecast.</p> : <>
      <p>{detail.evidence.basis}</p>
      {detail.evidence.polls.length === 0 ? <p>No seat poll has been published for this seat.</p> : <>
        {detail.evidence.polls.map((poll, i) => <SeatPollLine key={i} poll={poll} />)}
        <p><a href={`../polls/#seat-${seatId}`}>See this poll with every other poll</a></p></>}
    </>}
    <p><small>Chance of winning is the share of simulated elections the candidate wins; its simulation error is under one percentage point.</small></p>
  </section>;
}

export function ElectoratesView({ snapshot }: { snapshot: ForecastSnapshot }) {
  const rows = useRows(snapshot);
  const [seatId, setSeatId] = useState<string | null>(seatFromHash);
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<Sort>('name');
  useEffect(() => { const on = () => setSeatId(seatFromHash()); window.addEventListener('hashchange', on); return () => window.removeEventListener('hashchange', on); }, []);
  const choose = (id: string) => { window.location.hash = `seat=${id}`; setSeatId(id); };
  const listed = useMemo(() => {
    const q = query.trim().toLocaleLowerCase('en-NZ');
    const shown = rows.filter(r => !q || r.name.toLocaleLowerCase('en-NZ').includes(q));
    const by: Record<Sort, (a: Row, b: Row) => number> = {
      name: (a, b) => a.name.localeCompare(b.name, 'en-NZ'),
      close: (a, b) => (a.leaderP - a.second) - (b.leaderP - b.second) || a.name.localeCompare(b.name, 'en-NZ'),
      wide: (a, b) => Number(b.wide) - Number(a.wide) || a.name.localeCompare(b.name, 'en-NZ'),
    };
    return [...shown].sort(by[sort]);
  }, [rows, query, sort]);
  const selected = rows.find(r => r.id === seatId);
  const forecasts = useMemo(() => rows.map(r => ({ id: r.id, name: r.name, kind: r.kind, leaderParty: r.leaderParty, leaderPartyName: r.leaderPartyName, leaderName: r.leader, leaderP: r.leaderP, available: r.available })), [rows]);
  const pick = (id: string) => { choose(id); document.getElementById('seat-heading')?.scrollIntoView?.({ block: 'start' }); };
  return <>
    <p className="intro">Pick a seat to see each candidate's chance of winning, their likely share of the vote and the polls behind it.</p>
    <div className="picker">
      <label>Find a seat<input type="search" list="seat-names" value={query} placeholder="Type a seat name" autoComplete="off"
        onChange={e => { setQuery(e.target.value); const hit = rows.find(r => r.name.toLocaleLowerCase('en-NZ') === e.target.value.trim().toLocaleLowerCase('en-NZ')); if (hit) choose(hit.id); }} /></label>
      <datalist id="seat-names">{rows.map(r => <option key={r.id} value={r.name} />)}</datalist>
      <label>Sort by<select value={sort} onChange={e => setSort(e.target.value as Sort)}>
        <option value="name">Name</option><option value="close">Closest contest first</option><option value="wide">Widest uncertainty first</option></select></label>
    </div>
    <ElectorateMap snapshot={snapshot} forecasts={forecasts} onSelect={pick} />
    {selected ? <SeatDetail snapshot={snapshot} seatId={selected.id} /> : <p>Choose a seat from the list or search above.</p>}
    <table className="seatlist"><caption>All {rows.length} electorates ({listed.length} shown)</caption>
      <thead><tr><th>Electorate</th><th>Most likely winner</th><th>Chance</th></tr></thead>
      <tbody>{listed.map(r => <tr key={r.id} aria-selected={r.id === seatId || undefined}><td><a href={`#seat=${r.id}`} onClick={() => setSeatId(r.id)}>{r.name}</a>{r.kind === 'maori' ? ' (Māori)' : ''}{r.wide ? ' · wider' : ''}</td>
        <td>{r.available ? r.leader : '–'}</td><td>{r.available ? prob(r.leaderP) : 'No forecast'}</td></tr>)}</tbody></table>
  </>;
}
