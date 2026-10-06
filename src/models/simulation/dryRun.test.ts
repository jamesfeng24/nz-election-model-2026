import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { beforeAll, describe, expect, it } from 'vitest';
import { runSyntheticDryRun } from '../../dev/syntheticSnapshot';
import { fetchText as makeFetch, loadLatestSnapshot } from '../../data/loader';
import fixture from '../../../data/fixtures/synthetic/dry-run-inputs.json';
import { SimulationConfigSchema, type SimulationWorkerResponse } from '../../types/domain';
import { ForecastIndexSchema, type ForecastSnapshot } from '../../types/export';
import { canonicalJson, sha256Hex } from '../../utils/hash';
import { addToArchive } from './exporter';
import { PipelineInputsSchema, type PipelineRunRequest } from './pipeline';
import { createRunTracker, handleRequest } from './worker';
import { syntheticStages } from './syntheticStages';

let snapshot: ForecastSnapshot;
beforeAll(async () => { snapshot = await runSyntheticDryRun({ draws: 200 }); });

describe('end-to-end dry run on synthetic fixtures', () => {
  it('is deterministic for a seed and changes with the seed', async () => {
    expect(canonicalJson(await runSyntheticDryRun({ draws: 200 }))).toBe(canonicalJson(snapshot));
    expect(canonicalJson(await runSyntheticDryRun({ draws: 200, seed: 'other' }))).not.toBe(canonicalJson(snapshot));
  });
  it('is labelled synthetic and records reproducibility metadata', () => {
    expect(snapshot.provenance.kind).toBe('synthetic-fixture');
    expect(snapshot.snapshotId.startsWith('synthetic-')).toBe(true);
    expect(snapshot.simulation.config).toMatchObject({ seed: 'synthetic-dry-run-seed-1', prng: 'sfc32-xmur3', prngVersion: '1', draws: 200 });
    expect(snapshot.simulation.config.inputs[0].sha256).toMatch(/^[a-f0-9]{64}$/);
  });
  it('keeps probabilities and seat accounting coherent', () => {
    for (const p of snapshot.simulation.electoratePredictions) expect(p.candidates.reduce((s, c) => s + c.winProbability, 0)).toBeCloseTo(1, 12);
    expect(snapshot.mmp.status).toBe('available');
    if (snapshot.mmp.status === 'available') {
      const a = snapshot.mmp.exampleDrawAllocation;
      expect(a.parties.reduce((s, p) => s + p.totalSeats, a.independentElectorateSeats)).toBe(a.parliamentSize);
    }
    for (const s of snapshot.simulation.partySeatSummaries) expect(s.seats.lower).toBeLessThanOrEqual(s.seats.upper);
  });
  it('reports the electorate without a candidate model as unavailable rather than zero', () => {
    expect(snapshot.unavailableElectorates.map(e => e.electorateId)).toEqual(['synthetic-electorate-m1']);
    expect(snapshot.simulation.electoratePredictions.some(p => p.electorateId === 'synthetic-electorate-m1')).toBe(false);
  });
});

describe('worker protocol', () => {
  const inputs = PipelineInputsSchema.parse(fixture);
  const config = SimulationConfigSchema.parse({ ...snapshot0Config(), draws: 250 });
  function snapshot0Config() {
    return { schemaVersion: 1, electionId: 'synthetic-election', modelVersion: 'm', codeRevision: 'r', seed: 'w', prng: 'sfc32-xmur3', prngVersion: '1', draws: 250,
      inputs: [{ artifactId: 'i', sha256: 'a'.repeat(64) }], governmentCombinations: [] };
  }
  const run = (request: PipelineRunRequest) => {
    const out: SimulationWorkerResponse[] = [];
    handleRequest(request, syntheticStages, m => out.push(m), { asOf: '2026-10-06T00:00:00+00:00', limitations: ['synthetic'], progressEvery: 100 });
    return out;
  };
  it('posts progress then exactly one result, all tagged with the request id', () => {
    const out = run({ type: 'run', requestId: 'r1', config, inputs });
    expect(out.map(m => m.type)).toEqual(['progress', 'progress', 'result']);
    expect(out.every(m => m.requestId === 'r1')).toBe(true);
  });
  it('returns the same result whenever and however often it runs (no clock, order-free draws)', () => {
    const a = run({ type: 'run', requestId: 'r1', config, inputs }).at(-1), b = run({ type: 'run', requestId: 'r1', config, inputs }).at(-1);
    expect(JSON.stringify(a)).toBe(JSON.stringify(b));
  });
  it('turns failures into error messages and the tracker drops stale ids', () => {
    const bad = run({ type: 'run', requestId: 'r2', config, inputs: { ...inputs, stageParameters: {} } });
    expect(bad).toHaveLength(1);
    expect(bad[0]).toMatchObject({ type: 'error', requestId: 'r2' });
    const tracker = createRunTracker();
    tracker.start('r1'); tracker.start('r2');
    expect(tracker.accepts({ type: 'progress', requestId: 'r1', completedDraws: 1 })).toBe(false);
    expect(tracker.accepts({ type: 'progress', requestId: 'r2', completedDraws: 1 })).toBe(true);
  });
});

describe('archive and loader', () => {
  async function archive(extra: { tamper?: boolean } = {}) {
    const first = await addToArchive(snapshot, null);
    const files = new Map(first.files.map(f => [f.path, f.content]));
    if (extra.tamper) files.set(first.files[0].path, files.get(first.files[0].path)!.replace('Synthetic Alpha', 'Synthetic Alpho'));
    return { files, index: first.index, fetchText: async (url: string) => { const k = url.replace('/f/', ''); if (!files.has(k)) throw new Error(`404 ${k}`); return files.get(k)!; } };
  }
  it('round-trips through the archive when synthetic data is explicitly allowed', async () => {
    const a = await archive();
    const r = await loadLatestSnapshot({ fetchText: a.fetchText, baseUrl: '/f', allowSynthetic: true });
    expect(r.status).toBe('loaded');
    expect(r.status === 'loaded' && canonicalJson(r.snapshot)).toBe(canonicalJson(snapshot));
  });
  it('refuses synthetic snapshots when not allowed (production)', async () => {
    const a = await archive();
    expect(await loadLatestSnapshot({ fetchText: a.fetchText, baseUrl: '/f', allowSynthetic: false })).toEqual({ status: 'unavailable', reason: 'No published forecast snapshot' });
  });
  it('detects a changed snapshot file by hash', async () => {
    const a = await archive({ tamper: true });
    expect(await loadLatestSnapshot({ fetchText: a.fetchText, baseUrl: '/f', allowSynthetic: true })).toMatchObject({ status: 'unavailable', reason: expect.stringContaining('hash') });
  });
  it('reports missing or malformed archives as unavailable', async () => {
    expect(await loadLatestSnapshot({ fetchText: async () => { throw new Error('404'); }, baseUrl: '/f', allowSynthetic: true })).toMatchObject({ status: 'unavailable' });
    expect(await loadLatestSnapshot({ fetchText: async () => '{"schemaVersion":2}', baseUrl: '/f', allowSynthetic: true })).toMatchObject({ status: 'unavailable' });
    const notOk = makeFetch((async () => new Response('x', { status: 500 })) as typeof fetch);
    await expect(notOk('/x')).rejects.toThrow('HTTP 500');
  });
  it('skips withdrawn and superseded entries and loads the latest published one', async () => {
    const a = await archive();
    const second = { ...snapshot, snapshotId: 'synthetic-dry-run-2', createdAt: '2026-10-07T00:00:00+00:00' };
    const next = await addToArchive(second, a.index, 'synthetic-dry-run-1');
    const files = new Map(next.files.map(f => [f.path, f.content]));
    for (const [k, v] of a.files) if (!files.has(k)) files.set(k, v);
    const fetchText = async (url: string) => files.get(url.replace('/f/', ''))!;
    const r = await loadLatestSnapshot({ fetchText, baseUrl: '/f', allowSynthetic: true });
    expect(r.status === 'loaded' && r.snapshot.snapshotId).toBe('synthetic-dry-run-2');
    const withdrawn = ForecastIndexSchema.parse({ ...next.index, snapshots: next.index.snapshots.map(e => e.snapshotId === 'synthetic-dry-run-2' ? { ...e, status: 'withdrawn', withdrawnReason: 'test' } : e) });
    files.set('index.json', canonicalJson(withdrawn));
    expect(await loadLatestSnapshot({ fetchText, baseUrl: '/f', allowSynthetic: true })).toMatchObject({ status: 'unavailable' });
    expect(await sha256Hex('x')).toHaveLength(64);
  });
});

describe('synthetic-leak guard', () => {
  const walk = (dir: string): string[] => readdirSync(dir).flatMap(n => { const p = join(dir, n); return statSync(p).isDirectory() ? walk(p) : [p]; });
  it('keeps synthetic data out of public/ (what Vite copies into dist)', () => {
    for (const file of walk('public')) {
      expect(file, 'synthetic files must not be published').not.toMatch(/synthetic/i);
      if (!/\.(md|png|ico|svg|woff2?)$/i.test(file)) expect(readFileSync(file, 'utf8'), file).not.toMatch(/synthetic-(fixture|election|party)/);
    }
  });
  it('allows fixture imports only from src/dev and tests', () => {
    for (const file of walk('src').filter(f => /\.(ts|tsx)$/.test(f) && !/\.test\.tsx?$/.test(f) && !f.startsWith(join('src', 'dev')))) {
      expect(readFileSync(file, 'utf8'), file).not.toMatch(/data\/fixtures/);
    }
  });
  it('imports the dev-only module only behind import.meta.env.DEV', () => {
    const app = readFileSync('src/app/App.tsx', 'utf8');
    expect(app).toMatch(/if \(import\.meta\.env\.DEV && [^)]*\) \{\s*const \{ runSyntheticDryRun \} = await import\('\.\.\/dev\/syntheticSnapshot'\)/);
    expect(app.match(/dev\/syntheticSnapshot/g)).toHaveLength(1);
  });
});
