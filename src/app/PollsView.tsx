import { useState } from 'react';
import type { ForecastSnapshot } from '../types/export';
import { partyLabel } from './partyNames';
import { dateRange, longDate } from './format';
import { CODES, pollName } from './PollTables';

/** The list opens on this many of the newest polls; every poll stays in the model and in the page, behind "See more". */
export const INITIAL_POLLS = 10;
const monthOf = (iso: string) => longDate(`${iso.slice(0, 7)}-01`).replace(/^1 /, '');

/** Every poll behind the forecast, cited: national polls with the model's use of each, and seat polls grouped by seat. */
export function PollsView({ snapshot }: { snapshot: ForecastSnapshot }) {
  const evidence = snapshot.evidence;
  const [all, setAll] = useState(false);
  const columns = evidence?.nationalPolls[0]?.shares.map(s => s.partyId) ?? [];
  const party = (id: string) => (id === 'other' ? 'Other' : partyLabel(snapshot, id));
  const columnOf = (code: string | null) => { const label = code ? CODES[code] ?? code : null; return label && label !== 'Independent' ? label : 'Other'; };
  const seatPolls = snapshot.electorateDetail.flatMap(d => {
    const seatName = snapshot.directory.electorates.find(e => e.electorateId === d.electorateId)?.name ?? d.electorateId;
    return (d.evidence?.polls ?? []).map(poll => ({ poll, seatId: d.electorateId, seatName, date: (poll.fieldworkEnd ?? poll.published)!, first: false }));
  }).sort((a, b) => b.date.localeCompare(a.date) || a.seatName.localeCompare(b.seatName, 'en-NZ'));
  seatPolls.forEach((p, i) => { p.first = seatPolls.findIndex(q => q.seatId === p.seatId) === i; });
  const nationalLabels = columns.map(c => party(c));
  const seatLabels = new Set(seatPolls.flatMap(p => p.poll.results.map(r => columnOf(r.party))));
  const seatColumns = [...nationalLabels.filter(l => seatLabels.has(l)), ...[...seatLabels].filter(l => !nationalLabels.includes(l) && l !== 'Other'), ...(seatLabels.has('Other') ? ['Other'] : [])];
  const [allSeat, setAllSeat] = useState(() => typeof window !== 'undefined' && window.location.hash.startsWith('#seat-'));
  return <>
    <h2>National polls</h2>
    {evidence ? <>
      <table className="nationalpolls">
        <thead><tr><th>Poll</th><th>Dates</th><th>Sample</th>{columns.map(c => <th key={c}>{party(c)}</th>)}<th>In model</th></tr></thead>
        <tbody>{(all ? evidence.nationalPolls : evidence.nationalPolls.slice(0, INITIAL_POLLS)).flatMap((p, i, shown) => [
          ...(i === 0 || monthOf(p.fieldworkEnd) !== monthOf(shown[i - 1].fieldworkEnd) ? [<tr key={`m-${p.id}`} className="month"><th colSpan={columns.length + 4} scope="colgroup">{monthOf(p.fieldworkEnd)}</th></tr>] : []),
          <tr key={p.id} className={p.usedInModel ? undefined : 'unused'}>
            <td>{p.publisherUrl ? <a href={p.publisherUrl} rel="noopener noreferrer">{pollName(p)}</a> : pollName(p)}</td>
            <td>{dateRange(p.fieldworkStart, p.fieldworkEnd)}</td><td>{p.sampleSize ?? '–'}</td>
            {p.shares.map(s => <td key={s.partyId}>{s.percent === null ? '–' : `${s.approximate ? '~' : ''}${s.percent}`}</td>)}
            <td>{p.usedInModel ? 'Yes' : <span title={p.note ?? undefined}>No</span>}</td></tr>])}</tbody></table>
      {evidence.nationalPolls.length > INITIAL_POLLS && <p><button type="button" className="more" aria-expanded={all} onClick={() => setAll(v => !v)}>
        {all ? 'Show fewer polls' : `See more (${evidence.nationalPolls.length - INITIAL_POLLS} older polls)`}</button></p>}
    </> : <p>No national poll list.</p>}
    <h2>Electorate polls</h2>
    {seatPolls.length === 0 ? <p>No electorate polls.</p> : <>
      <table className="nationalpolls">
        <thead><tr><th>Poll</th><th>Electorate</th><th>Dates</th><th>Sample</th>{seatColumns.map(c => <th key={c}>{c}</th>)}<th>In model</th></tr></thead>
        <tbody>{(allSeat ? seatPolls : seatPolls.slice(0, INITIAL_POLLS)).flatMap((p, i, shown) => [
          ...(i === 0 || monthOf(p.date) !== monthOf(shown[i - 1].date) ? [<tr key={`m-${i}`} className="month"><th colSpan={seatColumns.length + 5} scope="colgroup">{monthOf(p.date)}</th></tr>] : []),
          <tr key={i} id={p.first ? `seat-${p.seatId}` : undefined} className={p.poll.usedInModel ? undefined : 'unused'}>
            <td>{p.poll.sources.find(s => s.url) ? <a href={p.poll.sources.find(s => s.url)!.url!} rel="noopener noreferrer">{pollName(p.poll)}</a> : pollName(p.poll)}</td>
            <td><a href={`../electorates/#seat=${p.seatId}`}>{p.seatName}</a></td>
            <td>{p.poll.fieldworkEnd ? dateRange(p.poll.fieldworkStart, p.poll.fieldworkEnd) : `published ${longDate(p.poll.published!)}`}</td><td>{p.poll.sampleSize ?? '–'}</td>
            {seatColumns.map(c => { const r = p.poll.results.find(x => columnOf(x.party) === c); return <td key={c}>{r ? <span title={r.name}>{r.approximate ? '~' : ''}{r.percent}<span className="sr-only"> ({r.name})</span></span> : '–'}</td>; })}
            <td>{p.poll.usedInModel ? 'Yes' : <span title={p.poll.note ?? undefined}>No</span>}</td></tr>])}</tbody></table>
      {seatPolls.length > INITIAL_POLLS && <p><button type="button" className="more" aria-expanded={allSeat} onClick={() => setAllSeat(v => !v)}>
        {allSeat ? 'Show fewer polls' : `See more (${seatPolls.length - INITIAL_POLLS} older polls)`}</button></p>}
    </>}
  </>;
}
