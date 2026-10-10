import { useEffect, useMemo, useState } from 'react';
import { partyLabel } from './partyNames';
import type { ForecastSnapshot } from '../types/export';
import { PRIMARY_INTERVAL_LEVEL, type IntervalSet } from '../types/domain';
import { pct, prob } from './format';
import { SeatPollLine } from './PollTables';
import { ElectorateMap, type IncumbentStatus, type MapCandidate } from './ElectorateMap';
import { COLOURS } from './SeatChart';

type Sort = 'name' | 'close';
interface Filters { winner: string; incumbent: string; kind: 'any' | 'general' | 'maori'; close: boolean; flip: boolean }
const NO_FILTERS: Filters = { winner: 'any', incumbent: 'any', kind: 'any', close: false, flip: false };
/** A seat counts as close when its most likely winner has under 70% chance. */
const CLOSE_BELOW = 0.7;
const level = (set: IntervalSet, l: number) => set.find(v => v.level === l)!;
const seatFromHash = () => new URLSearchParams(window.location.hash.slice(1)).get('seat');

interface Row { id: string; name: string; kind: 'general' | 'maori'; leader: string; leaderParty: string | null; leaderPartyName: string; leaderP: number; second: number; wide: boolean; available: boolean; incumbent: string | null; incumbentParty: string | null; incumbentStatus: IncumbentStatus; candidates: MapCandidate[] }

function useRows(snapshot: ForecastSnapshot): Row[] {
  return useMemo(() => snapshot.directory.electorates.map(e => {
    const prediction = snapshot.simulation.electoratePredictions.find(p => p.electorateId === e.electorateId);
    const sorted = prediction ? [...prediction.candidates].sort((a, b) => b.winProbability - a.winProbability) : [];
    const cls = snapshot.electorateDetail.find(d => d.electorateId === e.electorateId)?.uncertaintyClass;
    const leader = snapshot.directory.candidates.find(c => c.candidateId === sorted[0]?.candidateId);
    const detail = snapshot.electorateDetail.find(d => d.electorateId === e.electorateId);
    const candidates: MapCandidate[] = sorted.flatMap(c => {
      const cand = snapshot.directory.candidates.find(x => x.candidateId === c.candidateId);
      if (!cand) return [];
      return [{ id: cand.candidateId, name: cand.name, partyName: cand.partyId ? partyLabel(snapshot, cand.partyId) : cand.partyLabel ?? 'Independent', colour: (cand.partyId && COLOURS[cand.partyId]) || '#8b8f94',
        winP: c.winProbability, share: detail?.candidates.find(d => d.candidateId === c.candidateId)?.share[0].median ?? null, incumbent: cand.incumbent === true }];
    });
    const sitting = snapshot.incumbency ? snapshot.directory.candidates.find(c => c.electorateId === e.electorateId && c.incumbent) : undefined;
    return { incumbent: sitting?.name ?? null, incumbentParty: sitting ? sitting.partyId ?? 'independent' : null, candidates, incumbentStatus: (!snapshot.incumbency ? 'unknown' : !sitting ? 'open' : !prediction ? 'standing' : sitting.candidateId === leader?.candidateId ? 'leads' : 'trails') as IncumbentStatus,
       id: e.electorateId, name: e.name, kind: e.kind, leader: leader?.name ?? '', leaderParty: leader?.partyId ?? null, leaderPartyName: leader?.partyId ? partyLabel(snapshot, leader.partyId) : leader?.partyLabel ?? 'Independent', leaderP: sorted[0]?.winProbability ?? 0, second: sorted[1]?.winProbability ?? 0, wide: cls === 'exceptional' || cls === 'maori-layer', available: !!prediction };
  }), [snapshot]);
}

/** Tick spacing on the share axis, in vote share. */
const tickStep = (axisMax: number) => (axisMax <= 0.25 ? 0.05 : 0.1);

/**
 * A candidate's share range on the seat's shared axis: the 80% range in a light shade, the 50% range solid, the median as a
 * line. Hovering the solid part says the 50% range, hovering the light part the 80% range; the median is always in the tip.
 */
function RangeBar({ set, axisMax, label, colour }: { set: IntervalSet; axisMax: number; label: string; colour: string }) {
  const [tip, setTip] = useState<{ text: string; x: number } | null>(null);
  const x = (v: number) => `${(v / axisMax) * 100}%`;
  const r80 = level(set, PRIMARY_INTERVAL_LEVEL), r50 = level(set, 0.5);
  const text = (name: string, r: { lower: number; upper: number }) => `${name} range ${pct(r.lower)} – ${pct(r.upper)} · median ${pct(r50.median)}`;
  const show = (name: string, r: { lower: number; upper: number }) => (e: React.MouseEvent) => {
    const box = (e.currentTarget.parentElement as HTMLElement).getBoundingClientRect();
    setTip({ text: text(name, r), x: e.clientX - box.left });
  };
  return <div className="rangebar" role="img" aria-label={label} style={{ '--step': `${(tickStep(axisMax) / axisMax) * 100}%` } as React.CSSProperties} onMouseLeave={() => setTip(null)}>
    <span className="r80" style={{ background: colour, left: x(r80.lower), width: `calc(${x(r80.upper)} - ${x(r80.lower)})` }} onMouseMove={show('80%', r80)} onMouseEnter={show('80%', r80)} />
    <span className="r50" style={{ background: colour, left: x(r50.lower), width: `calc(${x(r50.upper)} - ${x(r50.lower)})` }} onMouseMove={show('50%', r50)} onMouseEnter={show('50%', r50)} />
    <span className="median" style={{ left: x(r50.median) }} />
    {tip && <span className="rangetip" style={{ left: tip.x }}>{tip.text}</span>}
  </div>;
}

/** One shared percentage scale for every bar in the table, drawn as a line with ticks. */
function ShareAxis({ axisMax }: { axisMax: number }) {
  const step = tickStep(axisMax);
  const ticks = Array.from({ length: Math.round(axisMax / step) + 1 }, (_, i) => i * step);
  return <div className="shareaxis" aria-hidden="true">{ticks.map(t => <span key={t} style={{ left: `${(t / axisMax) * 100}%` }}>{Math.round(t * 100)}%</span>)}</div>;
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
    {snapshot.incumbency && !rows.some(r => r.cand?.incumbent) && <p className="note">No sitting MP for this seat is standing here.</p>}
    {detail && detail.uncertaintyClass !== 'ordinary' && <p className="note">{detail.uncertaintyClass === 'maori-layer' ? 'Māori electorates are modelled separately, with fewer polls, so ranges here are wider.' : 'This seat has unusual local circumstances, so the model allows wider uncertainty.'}</p>}
    <table className="candidates"><caption>Chance of winning and share of the electorate vote</caption>
      <thead><tr><th>Candidate</th><th>Chance of winning</th><th>Median share</th><th>Share of electorate vote</th></tr></thead>
      <tbody>{rows.map(({ c, cand, share }) => <tr key={c.candidateId}>
        <td><strong>{cand?.name ?? c.candidateId}</strong>{cand?.incumbent && <> <span className="incumbent" title="The sitting MP for this seat">Incumbent</span></>}<br /><small>{partyName(cand?.partyId ?? null) ?? cand?.partyLabel ?? 'Independent'}</small></td>
        <td><span className="odds">{prob(c.winProbability)}</span></td>
        <td className="num"><strong>{share ? pct(share.share[0].median) : '–'}</strong></td>
        <td className="barcell">{share ? <RangeBar colour={(cand?.partyId && COLOURS[cand.partyId]) || '#8b8f94'} set={share.share} axisMax={axisMax} label={`${cand?.name}: median ${pct(share.share[0].median)}, 50% range ${pct(level(share.share, 0.5).lower)} to ${pct(level(share.share, 0.5).upper)}, 80% range ${pct(level(share.share, 0.8).lower)} to ${pct(level(share.share, 0.8).upper)}`} /> : <small>Not available</small>}</td></tr>)}</tbody>
      <tfoot><tr><td colSpan={3} /><td className="axiscell"><ShareAxis axisMax={axisMax} /></td></tr></tfoot></table>
    <p className="legend">Bars show each candidate's share of the electorate vote on the scale below. Hover the solid part for the 50% range and the light part for the 80% range; the median is the line and the number. Ranges cover half and four-fifths of simulated elections.</p>
    <h3>Polls</h3>
    {!detail?.evidence ? <p>No seat poll information for this forecast.</p> : <>
      <p>{detail.evidence.basis}</p>
      {detail.evidence.polls.length === 0 ? <p>No poll of this seat.</p> : <>
        {detail.evidence.polls.map((poll, i) => <SeatPollLine key={i} poll={poll} />)}
        <p><a href={`../polls/#seat-${seatId}`}>See all polls</a></p></>}
    </>}
    <p><small>Chance of winning is the share of simulated elections the candidate wins. Simulation error is under one percentage point.</small></p>
  </section>;
}

export function ElectoratesView({ snapshot }: { snapshot: ForecastSnapshot }) {
  const rows = useRows(snapshot);
  const [seatId, setSeatId] = useState<string | null>(seatFromHash);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [sort, setSort] = useState<Sort>('name');
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const set = <K extends keyof Filters>(k: K, v: Filters[K]) => setFilters(f => ({ ...f, [k]: v }));
  const filtered = JSON.stringify(filters) !== JSON.stringify(NO_FILTERS);
  const passes = (r: Row) => (filters.winner === 'any' || (r.available && (r.leaderParty ?? 'independent') === filters.winner))
    && (filters.incumbent === 'any' || r.incumbentParty === filters.incumbent) && (!filters.flip || r.incumbentStatus === 'trails')
    && (filters.kind === 'any' || r.kind === filters.kind) && (!filters.close || (r.available && r.leaderP < CLOSE_BELOW));
  const sortedNames = (pairs: [string, string][]) => [...new Map(pairs).entries()].sort((a, b) => a[1].localeCompare(b[1], 'en-NZ'));
  const winnerParties = useMemo(() => sortedNames(rows.filter(r => r.available).map(r => [r.leaderParty ?? 'independent', r.leaderPartyName])), [rows]);
  const incumbentParties = useMemo(() => sortedNames(rows.filter(r => r.incumbentParty).map(r => [r.incumbentParty!, r.incumbentParty === 'independent' ? 'Independent' : partyLabel(snapshot, r.incumbentParty!)])), [rows, snapshot]);
  const matching = useMemo(() => (filtered ? new Set(rows.filter(passes).map(r => r.id)) : null), [rows, filters]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const on = () => setSeatId(seatFromHash()); window.addEventListener('hashchange', on); return () => window.removeEventListener('hashchange', on); }, []);
  const choose = (id: string) => { window.location.hash = `seat=${id}`; setSeatId(id); };
  const listed = useMemo(() => {
    const q = query.trim().toLocaleLowerCase('en-NZ');
    const shown = rows.filter(r => (!q || r.name.toLocaleLowerCase('en-NZ').includes(q)) && passes(r));
    const by: Record<Sort, (a: Row, b: Row) => number> = {
      name: (a, b) => a.name.localeCompare(b.name, 'en-NZ'),
      close: (a, b) => (a.leaderP - a.second) - (b.leaderP - b.second) || a.name.localeCompare(b.name, 'en-NZ'),
    };
    return [...shown].sort(by[sort]);
  }, [rows, query, sort, filters]); // eslint-disable-line react-hooks/exhaustive-deps
  const suggestions = useMemo(() => { const q = query.trim().toLocaleLowerCase('en-NZ'); return q ? rows.filter(r => r.name.toLocaleLowerCase('en-NZ').includes(q)).sort((a, b) => a.name.localeCompare(b.name, 'en-NZ')).slice(0, 8) : []; }, [rows, query]);
  const selected = rows.find(r => r.id === seatId);
  const forecasts = useMemo(() => rows.map(r => ({ id: r.id, name: r.name, kind: r.kind, leaderParty: r.leaderParty, leaderPartyName: r.leaderPartyName, leaderName: r.leader, leaderP: r.leaderP, available: r.available, incumbent: r.incumbent, incumbentStatus: r.incumbentStatus, candidates: r.candidates })), [rows]);
  const pick = (id: string) => { choose(id); document.getElementById('seat-heading')?.scrollIntoView?.({ block: 'start' }); };
  return <>
    <p className="intro">Pick a seat for each candidate's chance of winning, vote share and polls.</p>
    <div className="picker">
      <div className="find" onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOpen(false); }}>
        <label>Find a seat<input type="search" value={query} placeholder="Type a seat name" autoComplete="off" role="combobox" aria-expanded={open && suggestions.length > 0} aria-controls="seat-suggestions"
          onFocus={() => setOpen(true)} onKeyDown={e => { if (e.key === 'Escape') setOpen(false); if (e.key === 'Enter' && suggestions[0]) { setQuery(suggestions[0].name); setOpen(false); pick(suggestions[0].id); } }}
          onChange={e => { setQuery(e.target.value); setOpen(true); const hit = rows.find(r => r.name.toLocaleLowerCase('en-NZ') === e.target.value.trim().toLocaleLowerCase('en-NZ')); if (hit) choose(hit.id); }} /></label>
        {open && suggestions.length > 0 && <ul className="suggest" id="seat-suggestions" role="listbox">{suggestions.map(r => <li key={r.id} role="option" aria-selected={false}>
          <button type="button" tabIndex={-1} onMouseDown={e => e.preventDefault()} onClick={() => { setQuery(r.name); setOpen(false); pick(r.id); }}>{r.name}{r.kind === 'maori' ? ' (Māori)' : ''}</button></li>)}</ul>}
      </div>
      <label>Sort by<select value={sort} onChange={e => setSort(e.target.value as Sort)}>
        <option value="name">Alphabetical</option><option value="close">Closest contest first</option></select></label>
    </div>
    <div className="picker filters" role="group" aria-label="Filter seats">
      <label>Projected winner's party<select value={filters.winner} onChange={e => set('winner', e.target.value)}>
        <option value="any">Any party</option>{winnerParties.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
      {snapshot.incumbency && <label>Incumbent's party<select value={filters.incumbent} onChange={e => set('incumbent', e.target.value)}>
        <option value="any">Any party</option>{incumbentParties.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>}
      <label>Type<select value={filters.kind} onChange={e => set('kind', e.target.value as Filters['kind'])}>
        <option value="any">General and Māori</option><option value="general">General</option><option value="maori">Māori</option></select></label>
      <label className="check"><input type="checkbox" checked={filters.close} onChange={e => set('close', e.target.checked)} /> Close contests (winner under 70%)</label>
      {snapshot.incumbency && <label className="check"><input type="checkbox" checked={filters.flip} onChange={e => set('flip', e.target.checked)} /> Projected flips (sitting MP trails)</label>}
      {filtered && <button type="button" className="more" onClick={() => setFilters(NO_FILTERS)}>Clear filters</button>}
    </div>
    <ElectorateMap snapshot={snapshot} forecasts={forecasts} onSelect={pick} highlight={matching} />
    {selected ? <SeatDetail snapshot={snapshot} seatId={selected.id} /> : <p>Pick a seat on the map, in the list or in the search box.</p>}
    <table className="seatlist"><caption>{filtered ? 'Electorates matching the filters' : `All ${rows.length} electorates`} ({listed.length} shown)</caption>
      <thead><tr><th>Electorate</th><th>Most likely winner</th><th>Chance</th>{snapshot.incumbency && <th>Incumbent</th>}</tr></thead>
      <tbody>{listed.map(r => <tr key={r.id} aria-selected={r.id === seatId || undefined}><td><a href={`#seat=${r.id}`} onClick={() => setSeatId(r.id)}>{r.name}</a>{r.kind === 'maori' ? ' (Māori)' : ''}{r.wide ? ' · wider' : ''}</td>
        <td>{r.available ? r.leader : '–'}{r.incumbentStatus === 'trails' && <> <span className="flip-tag">Flip</span></>}</td><td>{r.available ? prob(r.leaderP) : 'No forecast'}</td>{snapshot.incumbency && <td>{r.incumbent ?? 'None standing'}</td>}</tr>)}</tbody></table>
  </>;
}
