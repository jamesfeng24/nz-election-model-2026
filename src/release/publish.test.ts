import { describe, expect, it } from 'vitest';
import pythonBank from '../../data/fixtures/synthetic/nowcast-draw-bank.json';
import { loadLatestSnapshot } from '../data/loader';
import { publish, type ArchiveIO } from './publish';
import { releaseGate } from './releaseGate';

/** In-memory archive; the synthetic fixture never touches disk or public/. */
function memory(): ArchiveIO & { files: Map<string, string> } {
  const files = new Map<string, string>();
  return { files, readText: async p => files.get(p) ?? null, writeText: async (p, c) => { files.set(p, c); } };
}

const options = (snapshotId: string) => ({
  snapshotId, createdAt: '2026-10-07T00:00:00+00:00', dataCutoff: '2026-10-06T00:00:00+00:00', electionId: 'nz-general-2026',
  electionDate: '2026-11-07', boundaryVersionId: 'stats-nz-electorates-final-2025', modelVersion: 'synthetic-model', codeRevision: 'synthetic-revision',
  mmp: { rulesVersion: 'UNVERIFIED-PLACEHOLDER-synthetic-only', rulesSourceIds: ['synthetic-rules'], blocs: [] },
  nationalBasis: 'Synthetic rehearsal', limitations: ['SYNTHETIC FIXTURE: not a nowcast.'],
});
const bankText = JSON.stringify(pythonBank);

describe('release publication', () => {
  it('rehearses into a non-public archive the site loader can read back', async () => {
    const io = memory();
    const result = await publish({ bankText, options: options('synthetic-rehearsal-1'), archiveDir: '.release-build/archive',
      policy: { probabilityMcseMax: 0.5 - 1e-9, allowSynthetic: true } }, io);
    expect(result.status).toBe('published');
    const loaded = await loadLatestSnapshot({ baseUrl: '.release-build/archive', allowSynthetic: true,
      fetchText: async url => { const t = io.files.get(url); if (t === undefined) throw new Error('missing ' + url); return t; } });
    expect(loaded.status).toBe('loaded');
    const again = await publish({ bankText, options: options('synthetic-rehearsal-1'), archiveDir: '.release-build/archive',
      policy: { probabilityMcseMax: 0.49, allowSynthetic: true } }, io);
    expect(again).toMatchObject({ status: 'refused' });
  });

  it('refuses synthetic data under public/, models outside public/forecasts, and imprecise probabilities', async () => {
    const policy = { probabilityMcseMax: 0.49, allowSynthetic: true };
    expect(await publish({ bankText, options: options('synthetic-x'), archiveDir: 'public/forecasts', policy }, memory())).toMatchObject({ status: 'refused' });
    expect(await publish({ bankText, options: options('model-x'), archiveDir: '.release-build/archive', policy: { ...policy, allowSynthetic: false } }, memory()))
      .toMatchObject({ status: 'refused' });
    const strict = await publish({ bankText, options: options('synthetic-y'), archiveDir: '.release-build/archive', policy: { ...policy, probabilityMcseMax: 1e-6 } }, memory());
    expect(strict.status).toBe('refused');
    if (strict.status === 'refused') expect(strict.failures.join(' ')).toMatch(/Monte Carlo SE threshold/);
  });

  it('gates provenance and completeness', async () => {
    const io = memory();
    const result = await publish({ bankText, options: options('synthetic-z'), archiveDir: '.release-build/archive',
      policy: { probabilityMcseMax: 0.49, allowSynthetic: true } }, io);
    if (result.status !== 'published') throw new Error('expected publication');
    expect(releaseGate(result.snapshot, { probabilityMcseMax: 0.49, allowSynthetic: false }).failures).toContain('Only model snapshots may be published');
    const partial = structuredClone(result.snapshot) as any;
    partial.seatLayer = { status: 'unavailable', reason: 'test' };
    expect(releaseGate(partial, { probabilityMcseMax: 0.49, allowSynthetic: true }).passed).toBe(false);
  });

  it('holds the Māori calibration range to the same precision threshold (D127)', async () => {
    const io = memory();
    const result = await publish({ bankText, options: options('synthetic-r'), archiveDir: '.release-build/archive',
      policy: { probabilityMcseMax: 0.49, allowSynthetic: true } }, io);
    if (result.status !== 'published') throw new Error('expected publication');
    const ranged = structuredClone(result.snapshot) as any;
    const seat = ranged.electorateDetail.find((d: any) => d.uncertaintyClass === 'maori-layer');
    for (const c of seat.candidates) c.winProbabilityInflation = { ...c.winProbability };
    expect(releaseGate(ranged, { probabilityMcseMax: 0.49, allowSynthetic: true }).passed).toBe(true);
    seat.candidates[0].winProbabilityInflation.mcse = 0.495;
    const gate = releaseGate(ranged, { probabilityMcseMax: 0.49, allowSynthetic: true });
    expect(gate.passed).toBe(false);
    expect(gate.failures.join(' ')).toMatch(/winProbabilityInflation/);
  });
});
