import type { IndexResult } from '../data/loader';
import { longDate } from './format';

type Entry = Extract<IndexResult, { status: 'loaded' }>['index']['snapshots'][number];

/** Every forecast ever published, newest first. Withdrawn and replaced entries stay listed and say so. */
export function ArchiveView({
  result,
  archived = false,
}: {
  result: IndexResult | { status: 'loading' };
  /** In a frozen copy the live site's archive is three levels up. */
  archived?: boolean;
}) {
  if (result.status === 'loading') return <p role="status">Loading the archive…</p>;
  if (result.status === 'unavailable' || result.index.snapshots.length === 0) return <p>No forecasts yet.</p>;
  const { snapshots } = result.index;
  const replaced = new Set(snapshots.flatMap((e) => (e.supersedes ? [e.supersedes] : [])));
  const statusOf = (entry: Entry) => {
    if (entry.status === 'withdrawn') return `Withdrawn: ${entry.withdrawnReason}`;
    if (replaced.has(entry.snapshotId)) return 'Replaced by a correction';
    return entry.supersedes ? `Correction of ${entry.supersedes}` : 'Published';
  };
  const liveRoot = archived ? '../../../' : '../';
  const isOpenable = (entry: Entry) => entry.status !== 'withdrawn' && !replaced.has(entry.snapshotId);
  return (
    <>
      <p className="intro">
        Every forecast is kept as published. Open one to see the whole site as it was that week. A correction is a new
        entry; the old file stays.
      </p>
      <table>
        <caption>Published forecasts, newest first</caption>
        <thead>
          <tr>
            <th>Refreshed</th>
            <th>Published</th>
            <th>Status</th>
            <th>Open</th>
          </tr>
        </thead>
        <tbody>
          {[...snapshots].reverse().map((entry) => (
            <tr key={entry.snapshotId}>
              <td>{longDate(entry.dataCutoff)}</td>
              <td>{longDate(entry.createdAt)}</td>
              <td>{statusOf(entry)}</td>
              <td>
                {isOpenable(entry) && (
                  <>
                    <a href={`${liveRoot}archive/${entry.dataCutoff.slice(0, 10)}/`}>Site</a>
                    {' · '}
                  </>
                )}
                <a href={`../forecasts/${entry.path}`}>JSON</a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
