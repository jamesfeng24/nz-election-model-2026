import bank from '../../data/fixtures/synthetic/nowcast-draw-bank.json';
import config from '../../config/nowcast-2026.json';
import { buildNowcastSnapshot } from '../models/nowcast/fromBank';

/** TEST ONLY. A full synthetic 71-seat snapshot built from the Python synthetic bank (invented parties' numbers, real party ids). */
export async function syntheticBankSnapshot(over: { snapshotId?: string; dataCutoff?: string } = {}) {
  const mmp = (config as unknown as { mmp: { blocs: { id: string; label: string; partyIds: string[] }[]; hungParliament: never } }).mmp;
  const cutoff = over.dataCutoff ?? '2026-10-06T00:00:00+00:00';
  return buildNowcastSnapshot(bank, {
    snapshotId: over.snapshotId ?? 'synthetic-nowcast-1', createdAt: cutoff, dataCutoff: cutoff,
    electionId: 'nz-general-2026', electionDate: '2026-11-07', boundaryVersionId: 'stats-nz-electorates-final-2025',
    modelVersion: 'synthetic-model', codeRevision: 'synthetic-revision', bankSha256: 'a'.repeat(64),
    mmp: { rulesVersion: 'UNVERIFIED-PLACEHOLDER-synthetic-only', rulesSourceIds: ['synthetic-rules'], blocs: mmp.blocs, hungParliament: mmp.hungParliament },
    nationalBasis: 'Synthetic draws', limitations: ['SYNTHETIC FIXTURE: not a nowcast.'],
  });
}
