import type { ForecastSnapshot } from '../types/export';
import { partyLabel } from './partyNames';
import { dateRange, longDate } from './format';
import { SeatPollLine, pollName } from './PollTables';

const retrieved = (text: string) => { const t = Date.parse(text); return Number.isNaN(t) ? text : longDate(new Date(t).toISOString()); };

/** Every poll behind the forecast, cited: national polls with the model's use of each, and seat polls grouped by seat. */
export function PollsView({ snapshot }: { snapshot: ForecastSnapshot }) {
  const evidence = snapshot.evidence;
  const columns = evidence?.nationalPolls[0]?.shares.map(s => s.partyId) ?? [];
  const party = (id: string) => (id === 'other' ? 'Other' : partyLabel(snapshot, id));
  const seats = snapshot.electorateDetail.filter(d => (d.evidence?.polls.length ?? 0) > 0)
    .map(d => ({ d, name: snapshot.directory.electorates.find(e => e.electorateId === d.electorateId)?.name ?? d.electorateId }))
    .sort((a, b) => a.name.localeCompare(b.name, 'en-NZ'));
  const used = evidence?.nationalPolls.filter(p => p.usedInModel).length ?? 0;
  return <>
    <h2>National polls</h2>
    {evidence ? <>
      <p>{used} of {evidence.nationalPolls.length} polls since the 2023 election are in the model; the rest are greyed. Figures are percent of the party vote, copied from <a href={evidence.source.url} rel="noopener noreferrer">{evidence.source.label}</a>, revision {evidence.source.revision}, retrieved {retrieved(evidence.source.retrieved)}. A dash means the party was not reported.</p>
      <table className="nationalpolls">
        <thead><tr><th>Poll</th><th>Dates</th><th>Sample</th>{columns.map(c => <th key={c}>{party(c)}</th>)}<th>In model</th></tr></thead>
        <tbody>{evidence.nationalPolls.map(p => <tr key={p.id} className={p.usedInModel ? undefined : 'unused'}>
          <td>{p.publisherUrl ? <a href={p.publisherUrl} rel="noopener noreferrer">{pollName(p)}</a> : pollName(p)}</td>
          <td>{dateRange(p.fieldworkStart, p.fieldworkEnd)}</td><td>{p.sampleSize ?? '–'}</td>
          {p.shares.map(s => <td key={s.partyId}>{s.percent === null ? '–' : `${s.approximate ? '~' : ''}${s.percent}`}</td>)}
          <td>{p.usedInModel ? 'Yes' : <span title={p.note ?? undefined}>No</span>}</td></tr>)}</tbody></table>
    </> : <p>This release does not include the national poll listing.</p>}
    <h2>Electorate polls</h2>
    {seats.length === 0 ? <p>No electorate polls are attached to this release.</p> : <>
      <p>Seat polls are rare and small. Each is listed whether or not the forecast uses it.</p>
      {seats.map(({ d, name }) => <section key={d.electorateId} id={`seat-${d.electorateId}`}>
        <h3>{name} (<a href={`../electorates/#seat=${d.electorateId}`}>forecast for this seat</a>)</h3>
        {d.evidence!.polls.map((poll, i) => <SeatPollLine key={i} poll={poll} />)}
      </section>)}
    </>}
  </>;
}
