import fixture from '../../data/fixtures/synthetic/dry-run-inputs.json';
import { buildSnapshot } from '../models/simulation/exporter';
import { PipelineInputsSchema, runPipeline } from '../models/simulation/pipeline';
import { PRNG_NAME, PRNG_VERSION } from '../models/simulation/prng';
import { syntheticStages } from '../models/simulation/syntheticStages';
import { SimulationConfigSchema } from '../types/domain';
import type { ForecastSnapshot } from '../types/export';
import { canonicalJson, sha256Hex } from '../utils/hash';

/**
 * DEVELOPMENT AND TESTS ONLY. Runs the whole labelled-synthetic chain in memory and returns a validated
 * snapshot. Imported only behind `import.meta.env.DEV`; the production bundle must not contain it.
 */
export async function runSyntheticDryRun(options: { draws?: number; seed?: string } = {}): Promise<ForecastSnapshot> {
  const inputs = PipelineInputsSchema.parse(fixture);
  const seed = options.seed ?? 'synthetic-dry-run-seed-1';
  const draws = options.draws ?? 400;
  const config = SimulationConfigSchema.parse({
    schemaVersion: 1, electionId: inputs.electionId, modelVersion: 'synthetic-placeholder-v1', codeRevision: 'synthetic-dry-run',
    seed, prng: PRNG_NAME, prngVersion: PRNG_VERSION, draws,
    inputs: [{ artifactId: 'synthetic-dry-run-inputs', sha256: await sha256Hex(canonicalJson(fixture)) }],
    governmentCombinations: [
      { id: 'synthetic-bloc-ac', partyIds: ['synthetic-party-a', 'synthetic-party-c'], requiredSeats: 11 },
      { id: 'synthetic-bloc-bd', partyIds: ['synthetic-party-b', 'synthetic-party-d'], requiredSeats: 11 },
    ],
  });
  const limitations = ['SYNTHETIC FIXTURE: invented parties, polls and electorates; placeholder stages; not a forecast.'];
  const asOf = '2026-10-06T00:00:00+00:00';
  const output = runPipeline(config, inputs, syntheticStages, { runId: 'synthetic-dry-run', asOf, limitations });
  return buildSnapshot(config, inputs, output, {
    snapshotId: 'synthetic-dry-run-1', createdAt: asOf, dataCutoff: asOf,
    provenance: { kind: 'synthetic-fixture', label: 'End-to-end dry run on invented fixtures. Not a forecast.' },
    calibrationStatus: 'uncalibrated', nationalBasis: 'Synthetic poll average with invented noise',
    limitations, boundaries: null,
  });
}
