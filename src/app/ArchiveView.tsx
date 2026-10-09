import type { IndexResult } from '../data/loader';
import { longDate } from './format';

/** Newest first. A withdrawn or superseded entry stays listed and says so; corrections never rewrite an earlier file. */
export function ArchiveView({ result }: { result: IndexResult | { status: 'loading' } }) {
  if (result.status === 'loading') return <p role="status">Loading the archive…</p>;
  if (result.status === 'unavailable' || result.index.snapshots.length === 0) return <p>No forecasts have been published yet.</p>;
  const { snapshots } = result.index;
  const superseded = new Set(snapshots.flatMap(e => (e.supersedes ? [e.supersedes] : [])));
  return <>
    <p className="intro">Each forecast is saved as it was published and never edited. A correction is published as a new entry that replaces the old one, and the old file stays here.</p>
    <table><caption>Published forecasts, newest first</caption>
      <thead><tr><th>As of</th><th>Published</th><th>Status</th><th>File</th></tr></thead>
      <tbody>{[...snapshots].reverse().map(e => <tr key={e.snapshotId}>
        <td>{longDate(e.dataCutoff)}</td><td>{longDate(e.createdAt)}</td>
        <td>{e.status === 'withdrawn' ? `Withdrawn: ${e.withdrawnReason}` : superseded.has(e.snapshotId) ? 'Replaced by a correction' : e.supersedes ? `Correction of ${e.supersedes}` : 'Published'}</td>
        <td><a href={`../forecasts/${e.path}`}>JSON</a></td></tr>)}</tbody></table>
  </>;
}
