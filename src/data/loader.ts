import {
  ForecastIndexSchema,
  ForecastSnapshotSchema,
  type ForecastIndex,
  type ForecastSnapshot,
} from '../types/export';
import { sha256Hex } from '../utils/hash';

export type LoadResult =
  | { status: 'loaded'; snapshot: ForecastSnapshot }
  /** `none-published`: the archive has no forecast yet. `failed`: one exists but could not be loaded or verified. */
  | { status: 'unavailable'; reason: string; cause?: 'none-published' | 'failed' };

export interface LoaderOptions {
  fetchText: (url: string) => Promise<string>;
  baseUrl: string;
  /** Production builds must pass false so synthetic fixtures can never display. */
  allowSynthetic: boolean;
}

/** An HTTP error response; a 404 for the archive index means nothing has been published yet. */
export class HttpError extends Error {
  constructor(
    url: string,
    readonly status: number,
  ) {
    super(`${url}: HTTP ${status}`);
  }
}

export const fetchText =
  (fetchImpl: typeof fetch = fetch) =>
  async (url: string) => {
    const response = await fetchImpl(url);
    if (!response.ok) throw new HttpError(url, response.status);
    return response.text();
  };

const archiveRoot = (baseUrl: string) => (baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`);
const errorReason = (error: unknown) => (error instanceof Error ? error.message : 'Unknown loading error');

type IndexEntry = ForecastIndex['snapshots'][number];

/**
 * The entries that are currently published, oldest first: not withdrawn, not superseded by a correction, and
 * not synthetic unless allowed. Supersession is permanent even if the correction is later withdrawn, so a
 * withdrawn correction never silently reinstates the snapshot it corrected; publish a new entry to restore it.
 */
function currentEntries(index: ForecastIndex, allowSynthetic: boolean): IndexEntry[] {
  const withdrawn = new Set(index.snapshots.filter((e) => e.status === 'withdrawn').map((e) => e.snapshotId));
  const superseded = new Set(index.snapshots.flatMap((e) => (e.supersedes !== null ? [e.supersedes] : [])));
  return index.snapshots.filter(
    (e) =>
      e.status === 'published' &&
      !withdrawn.has(e.snapshotId) &&
      !superseded.has(e.snapshotId) &&
      (allowSynthetic || e.provenanceKind !== 'synthetic-fixture'),
  );
}

const readIndex = async (options: LoaderOptions) =>
  ForecastIndexSchema.parse(JSON.parse(await options.fetchText(`${archiveRoot(options.baseUrl)}index.json`)));

/**
 * Load the latest published snapshot: validate index, then content hash, then snapshot.
 * Anything wrong gives an "unavailable" result; the site never shows partial or unverified data.
 */
export async function loadLatestSnapshot(options: LoaderOptions): Promise<LoadResult> {
  const { fetchText: get, baseUrl, allowSynthetic } = options;
  const failed = (reason: string): LoadResult => ({ status: 'unavailable', reason, cause: 'failed' });
  try {
    const index = await readIndex(options);
    const entries = currentEntries(index, allowSynthetic);
    const entry = entries[entries.length - 1];
    if (!entry) return { status: 'unavailable', reason: 'No published forecast snapshot', cause: 'none-published' };
    const text = await get(`${archiveRoot(baseUrl)}${entry.path}`);
    if ((await sha256Hex(text)) !== entry.sha256) return failed('Snapshot hash does not match the archive index');
    const snapshot = ForecastSnapshotSchema.parse(JSON.parse(text));
    if (snapshot.snapshotId !== entry.snapshotId || snapshot.provenance.kind !== entry.provenanceKind)
      return failed('Snapshot disagrees with its index entry');
    if (!allowSynthetic && snapshot.provenance.kind === 'synthetic-fixture') return failed('Synthetic data refused');
    return { status: 'loaded', snapshot };
  } catch (error) {
    const notPublished = error instanceof HttpError && error.status === 404;
    return { status: 'unavailable', reason: errorReason(error), cause: notPublished ? 'none-published' : 'failed' };
  }
}

export type IndexResult = { status: 'loaded'; index: ForecastIndex } | { status: 'unavailable'; reason: string };

/** The archive index for the archive page, validated, without synthetic entries unless allowed. */
export async function loadArchiveIndex(options: LoaderOptions): Promise<IndexResult> {
  try {
    const index = await readIndex(options);
    const snapshots = index.snapshots.filter((e) => options.allowSynthetic || e.provenanceKind !== 'synthetic-fixture');
    return { status: 'loaded', index: { ...index, snapshots } };
  } catch (error) {
    return { status: 'unavailable', reason: errorReason(error) };
  }
}

export interface ReleasePoint {
  snapshotId: string;
  dataCutoff: string;
  /** Chance each bloc wins a majority, by bloc id. */
  blocMajority: Record<string, { label: string; p: number }>;
  /** Chance of each named scenario, by scenario id. */
  scenarios: Record<string, { label: string; p: number }>;
}

/**
 * Every current release, oldest first, each verified against its index hash and the schema. A failure for any one
 * release drops the whole history: a chart is never drawn from unverified or partial data.
 */
export async function loadReleaseHistory(options: LoaderOptions): Promise<ReleasePoint[]> {
  try {
    const index = await readIndex(options);
    const points: ReleasePoint[] = [];
    for (const entry of currentEntries(index, options.allowSynthetic)) {
      const text = await options.fetchText(`${archiveRoot(options.baseUrl)}${entry.path}`);
      if ((await sha256Hex(text)) !== entry.sha256) return [];
      const snapshot = ForecastSnapshotSchema.parse(JSON.parse(text));
      if (snapshot.targetType !== 'nowcast' || snapshot.seatLayer.status !== 'available') continue;
      const { blocs, scenarios } = snapshot.seatLayer.summary;
      points.push({
        snapshotId: snapshot.snapshotId,
        dataCutoff: snapshot.dataCutoff,
        blocMajority: Object.fromEntries(blocs.map((b) => [b.id, { label: b.label, p: b.probMajority.p }])),
        scenarios: Object.fromEntries(scenarios.map((s) => [s.id, { label: s.label, p: s.probability.p }])),
      });
    }
    return points.sort((a, b) => a.dataCutoff.localeCompare(b.dataCutoff));
  } catch {
    return [];
  }
}
