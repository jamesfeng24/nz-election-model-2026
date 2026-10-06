import { ForecastIndexSchema, ForecastSnapshotSchema, type ForecastSnapshot } from '../types/export';
import { sha256Hex } from '../utils/hash';

export type LoadResult =
  | { status: 'loaded'; snapshot: ForecastSnapshot }
  | { status: 'unavailable'; reason: string };

export interface LoaderOptions {
  fetchText: (url: string) => Promise<string>;
  baseUrl: string;
  /** Development only. Production builds must pass false so synthetic fixtures can never display. */
  allowSynthetic: boolean;
}

/** Fetch with `fetch`, rejecting non-OK responses. */
export const fetchText = (fetchImpl: typeof fetch = fetch) => async (url: string) => {
  const response = await fetchImpl(url);
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return response.text();
};

/**
 * Load the latest published snapshot: validate index → validate content hash → validate snapshot.
 * Anything wrong yields an explicit "unavailable" result; the site never renders partial or unverified data.
 */
export async function loadLatestSnapshot(options: LoaderOptions): Promise<LoadResult> {
  const { fetchText: get, baseUrl, allowSynthetic } = options;
  const root = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
  try {
    const index = ForecastIndexSchema.parse(JSON.parse(await get(`${root}index.json`)));
    const withdrawn = new Set(index.snapshots.filter(e => e.status === 'withdrawn').map(e => e.snapshotId));
    // Supersession is permanent even if the newer entry is later withdrawn: a withdrawn correction never
    // silently reinstates the snapshot it corrected. Publish a new entry to restore anything.
    const superseded = new Set(index.snapshots.flatMap(e => (e.supersedes !== null ? [e.supersedes] : [])));
    const eligible = index.snapshots.filter(e => e.status === 'published' && !withdrawn.has(e.snapshotId) && !superseded.has(e.snapshotId) &&
      (allowSynthetic || e.provenanceKind !== 'synthetic-fixture'));
    const entry = eligible[eligible.length - 1];
    if (!entry) return { status: 'unavailable', reason: 'No published forecast snapshot' };
    const text = await get(`${root}${entry.path}`);
    if (await sha256Hex(text) !== entry.sha256) return { status: 'unavailable', reason: 'Snapshot hash does not match the archive index' };
    const snapshot = ForecastSnapshotSchema.parse(JSON.parse(text));
    if (snapshot.snapshotId !== entry.snapshotId || snapshot.provenance.kind !== entry.provenanceKind)
      return { status: 'unavailable', reason: 'Snapshot disagrees with its index entry' };
    if (!allowSynthetic && snapshot.provenance.kind === 'synthetic-fixture') return { status: 'unavailable', reason: 'Synthetic data refused' };
    return { status: 'loaded', snapshot };
  } catch (error) {
    return { status: 'unavailable', reason: error instanceof Error ? error.message : 'Unknown loading error' };
  }
}
