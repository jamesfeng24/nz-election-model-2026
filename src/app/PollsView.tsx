import type { ForecastSnapshot } from '../types/export';
import { longDate } from './format';
import { SeatPollTable } from './PollTables';

const retrieved = (text: string) => { const t = Date.parse(text); return Number.isNaN(t) ? text : longDate(new Date(t).toISOString()); };

/** Every poll behind the forecast, cited: national polls with the model's use of each, and seat polls grouped by seat. */
export function PollsView({ snapshot }: { snapshot: ForecastSnapshot }) {
  const evidence = snapshot.evidence;
  const columns = evidence?.nationalPolls[0]?.shares.map(s => s.partyId) ?? [];
  const party = (id: string) => snapshot.directory.parties.find(p => p.partyId === id)?.abbreviation ?? id;
  const seats = snapshot.electorateDetail.filter(d => (d.evidence?.polls.length ?? 0) > 0)
    .map(d => ({ d, name: snapshot.directory.electorates.find(e => e.electorateId === d.electorateId)?.name ?? d.electorateId }))
    .sort((a, b) => a.name.localeCompare(b.name, 'en-NZ'));
  const used = evidence?.nationalPolls.filter(p => p.usedInModel).length ?? 0;
  return <>
    <p className="intro">Every poll this forecast uses or has found, with who ran it, when, how many people, and where it was published.</p>
    <h2>National polls</h2>
    {evidence ? <>
      <p>{used} of the {evidence.nationalPolls.length} national polls since the 2023 election are in the model; the rest are listed and marked. The figures are copied from <a href={evidence.source.url} rel="noopener noreferrer">{evidence.source.label}</a>, revision {evidence.source.revision}, retrieved {retrieved(evidence.source.retrieved)}. Wikipedia is a volunteer-edited aggregator, so a poll's own publisher is the primary source, and an address is shown only where we hold one. Fieldwork dates are as Wikipedia lists them and can be release dates. A dash means the poll did not report that party; "~" would mark an approximate figure.</p>
      <table className="nationalpolls">
        <caption>National polls, newest first (percent of the party vote)</caption>
        <thead><tr><th>Fieldwork</th><th>Pollster</th><th>Client</th><th>Sample</th>{columns.map(c => <th key={c}>{party(c)}</th>)}<th>In model</th></tr></thead>
        <tbody>{evidence.nationalPolls.map(p => <tr key={p.id} className={p.usedInModel ? undefined : 'unused'}>
          <td>{p.fieldworkStart ? `${longDate(p.fieldworkStart)} to ` : ''}{longDate(p.fieldworkEnd)}</td>
          <td>{p.publisherUrl ? <a href={p.publisherUrl} rel="noopener noreferrer">{p.pollster}</a> : p.pollster}</td>
          <td>{p.commissioner ?? <small>not recorded</small>}</td><td>{p.sampleSize ?? '–'}</td>
          {p.shares.map(s => <td key={s.partyId}>{s.percent === null ? '–' : `${s.approximate ? '~' : ''}${s.percent}`}</td>)}
          <td>{p.usedInModel ? 'Yes' : <span title={p.note ?? undefined}>No*</span>}</td></tr>)}</tbody></table>
      {used < evidence.nationalPolls.length && <p><small>* Listed by Wikipedia but not in the model's data set.</small></p>}
    </> : <p>This release does not include the national poll listing.</p>}
    <h2>Electorate polls</h2>
    {seats.length === 0 ? <p>No electorate polls are attached to this release.</p> : <>
      <p>Seat polls are rare, small and often commissioned. A seat poll appears here whether or not the forecast uses it, and each is marked.</p>
      {seats.map(({ d, name }) => <section key={d.electorateId} id={`seat-${d.electorateId}`}>
        <h3>{name} (<a href={`../electorates/#seat=${d.electorateId}`}>forecast for this seat</a>)</h3>
        {d.evidence!.polls.map((poll, i) => <SeatPollTable key={i} poll={poll} />)}
      </section>)}
    </>}
  </>;
}
