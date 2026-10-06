import { ForecastSnapshotSchema, ForecastIndexSchema, type ForecastIndex, type ForecastSnapshot } from '../../types/export';
import type { SimulationConfig } from '../../types/domain';
import { canonicalJson, sha256Hex } from '../../utils/hash';
import type { PipelineInputs, PipelineOutput } from './pipeline';

export interface SnapshotMeta {
  snapshotId: string;
  targetType: ForecastSnapshot['targetType'];
  createdAt: string;
  dataCutoff: string;
  modelStateAsOf: string;
  electionDate: string;
  provenance: ForecastSnapshot['provenance'];
  calibrationStatus: ForecastSnapshot['calibrationStatus'];
  nationalBasis: string;
  limitations: string[];
  boundaries: ForecastSnapshot['boundaries'];
}

/** Assemble and validate a snapshot. Throws if the contract is violated, so nothing invalid is ever written. */
export function buildSnapshot(config: SimulationConfig, inputs: PipelineInputs, output: PipelineOutput, meta: SnapshotMeta): ForecastSnapshot {
  const predicted = new Set(output.result.electoratePredictions.map(p => p.electorateId));
  return ForecastSnapshotSchema.parse({
    schemaVersion: 2, snapshotId: meta.snapshotId, targetType: meta.targetType, createdAt: meta.createdAt, dataCutoff: meta.dataCutoff,
    modelStateAsOf: meta.modelStateAsOf, electionId: config.electionId, electionDate: meta.electionDate, provenance: meta.provenance, calibrationStatus: meta.calibrationStatus,
    directory: {
      parties: inputs.parties.map(p => ({ partyId: p.id, name: p.name, abbreviation: p.abbreviation })),
      electorates: inputs.electorates.map(e => ({ electorateId: e.id, name: e.name, kind: e.kind })),
      candidates: inputs.candidates.map(c => ({ candidateId: c.id, name: c.name, electorateId: c.electorateId, partyId: c.partyId })),
    },
    national: {
      partyVoteShares: inputs.parties.map(p => ({ partyId: p.id, share: output.nationalShares[p.id] })),
      basis: meta.nationalBasis,
    },
    simulation: output.result,
    unavailableElectorates: inputs.electorates.filter(e => !predicted.has(e.id)).map(e => ({ electorateId: e.id, reason: 'No candidate model for this electorate in this run' })),
    mmp: output.exampleDrawAllocation ? { status: 'available', exampleDrawAllocation: output.exampleDrawAllocation } : { status: 'unavailable', reason: 'No MMP allocator supplied' },
    boundaries: meta.boundaries, limitations: meta.limitations,
  });
}

export interface ArchiveFile { path: string; content: string }

/**
 * Snapshot file plus the next append-only index. Never rewrites earlier entries; a correction is a new
 * entry that names what it supersedes. Returns files relative to the archive root.
 */
export async function addToArchive(snapshot: ForecastSnapshot, previous: ForecastIndex | null, supersedes: string | null = null): Promise<{ files: ArchiveFile[]; index: ForecastIndex }> {
  const content = canonicalJson(snapshot);
  const path = `${snapshot.snapshotId}/snapshot.json`;
  const index = ForecastIndexSchema.parse({
    schemaVersion: 1,
    snapshots: [...(previous?.snapshots ?? []), {
      snapshotId: snapshot.snapshotId, createdAt: snapshot.createdAt, dataCutoff: snapshot.dataCutoff,
      provenanceKind: snapshot.provenance.kind, path, sha256: await sha256Hex(content), supersedes, status: 'published', withdrawnReason: null,
    }],
  });
  return { files: [{ path, content }, { path: 'index.json', content: canonicalJson(index) }], index };
}
