import { addToArchive } from '../models/simulation/exporter';
import { buildNowcastSnapshot, type NowcastSnapshotOptions } from '../models/nowcast/fromBank';
import { ForecastIndexSchema, type ForecastIndex, type ForecastSnapshot } from '../types/export';
import { sha256Hex } from '../utils/hash';
import { releaseGate, type ReleasePolicy } from './releaseGate';

/**
 * Production publication: draw bank → validated v2 snapshot → release gate → append-only archive (snapshot file and
 * the next index). File I/O is injected so the same code runs in tests and in the Node CLI (`src/release/cli.ts`).
 * Nothing is written unless every check passes; earlier archive entries are never rewritten.
 */
export interface ArchiveIO {
  readText(path: string): Promise<string | null>;
  writeText(path: string, content: string): Promise<void>;
}

export interface PublishRequest {
  bankText: string;
  options: Omit<NowcastSnapshotOptions, 'bankSha256' | 'limitations'> & { limitations: string[] };
  policy: ReleasePolicy;
  archiveDir: string;
  supersedes?: string | null;
}

export type PublishResult =
  | { status: 'published'; snapshot: ForecastSnapshot; files: string[] }
  | { status: 'refused'; failures: string[] };

const join = (dir: string, path: string) => `${dir.replace(/\/+$/, '')}/${path}`;

export async function publish(request: PublishRequest, io: ArchiveIO): Promise<PublishResult> {
  const { archiveDir, policy } = request;
  if (!policy.allowSynthetic && !/(^|\/)public\/forecasts\/?$/.test(archiveDir))
    return { status: 'refused', failures: ['A model release is written to the public forecasts archive (public/forecasts) only'] };
  if (policy.allowSynthetic && /(^|\/)public(\/|$)/.test(archiveDir))
    return { status: 'refused', failures: ['Rehearsal (synthetic) output is never written under public/'] };
  const bank = JSON.parse(request.bankText);
  let snapshot: ForecastSnapshot;
  try {
    snapshot = await buildNowcastSnapshot(bank, {
      ...request.options, bankSha256: await sha256Hex(request.bankText),
    });
  } catch (error) {
    return { status: 'refused', failures: [`Snapshot invalid: ${error instanceof Error ? error.message : String(error)}`] };
  }
  const gate = releaseGate(snapshot, policy);
  if (!gate.passed) return { status: 'refused', failures: gate.failures };
  const previousText = await io.readText(join(archiveDir, 'index.json'));
  const previous: ForecastIndex | null = previousText === null ? null : ForecastIndexSchema.parse(JSON.parse(previousText));
  if (previous?.snapshots.some(e => e.snapshotId === snapshot.snapshotId))
    return { status: 'refused', failures: [`Snapshot ${snapshot.snapshotId} is already archived; corrections need a new id`] };
  const { files } = await addToArchive(snapshot, previous, request.supersedes ?? null);
  for (const file of files) await io.writeText(join(archiveDir, file.path), file.content);
  return { status: 'published', snapshot, files: files.map(f => join(archiveDir, f.path)) };
}
