import type { ForecastSnapshot } from '../types/export';
import { ElectoratePolls } from './polls/ElectoratePolls';
import { NationalPolls } from './polls/NationalPolls';

/** Every poll behind the forecast: national polls, then polls of single electorates. */
export function PollsView({ snapshot }: { snapshot: ForecastSnapshot }) {
  const national = snapshot.evidence?.nationalPolls;
  return (
    <>
      <h2>National polls</h2>
      {national ? <NationalPolls snapshot={snapshot} polls={national} /> : <p>No national poll list.</p>}
      <h2>Electorate polls</h2>
      <ElectoratePolls snapshot={snapshot} />
    </>
  );
}
