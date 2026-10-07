import { beforeAll, describe, expect, it } from 'vitest';
import { runSyntheticDryRun } from '../dev/syntheticSnapshot';
import { ElectorateGeometrySchema, ForecastIndexSchema, ForecastSnapshotSchema, type ForecastSnapshot } from './export';
import geometry from '../../data/fixtures/synthetic/dry-run-boundaries.geojson?raw';

const clone = <T,>(x: T): T => structuredClone(x);
let base: ForecastSnapshot;
const reject = (mutate: (s: any) => void, message: RegExp) => {
  const s = clone(base) as any; mutate(s);
  const r = ForecastSnapshotSchema.safeParse(s);
  expect(r.success).toBe(false);
  expect(JSON.stringify(r.error?.issues)).toMatch(message);
};

describe('forecast export contract', () => {
  beforeAll(async () => { base = await runSyntheticDryRun({ draws: 60 }); });
  it('accepts the synthetic dry-run snapshot', () => {
    expect(ForecastSnapshotSchema.safeParse(base).success).toBe(true);
  });
  it('requires the synthetic id prefix exactly when provenance is synthetic', () => {
    reject(s => { s.snapshotId = 'run-1'; }, /synthetic/);
    reject(s => { s.provenance = { kind: 'model', modelVersion: 'm', codeRevision: 'r', configVersion: 'c' }; }, /synthetic/);
  });
  it('refuses placeholder MMP rules in a model snapshot', () => {
    reject(s => { s.snapshotId = 'model-1'; s.provenance = { kind: 'model', modelVersion: 'm', codeRevision: 'r', configVersion: 'c' }; }, /Placeholder MMP rules/);
  });
  it('rejects unknown keys, unknown parties and incomplete electorate coverage', () => {
    reject(s => { s.extra = 1; }, /Unrecognized/);
    reject(s => { s.national.partyVoteShares[0].partyId = 'nope'; }, /Unknown party/);
    reject(s => { s.unavailableElectorates = []; }, /exactly one prediction/);
    reject(s => { s.unavailableElectorates.push({ electorateId: s.simulation.electoratePredictions[0].electorateId, reason: 'dup' }); }, /exactly one prediction/);
  });
  it('rejects partial draws, mismatched elections and out-of-range shares', () => {
    reject(s => { s.simulation.completedDraws = 1; }, /every requested draw/);
    reject(s => { s.electionId = 'other'; }, /election/);
    reject(s => { s.national.partyVoteShares[0].share[0].lower = -0.1; s.national.partyVoteShares[0].share[1].lower = -0.1; s.national.partyVoteShares[0].share[2].lower = -0.1; }, /within 0/);
  });
  it('rejects synthetic party, electorate, candidate and election ids in a model snapshot', () => {
    const asModel = (s: any) => {
      s.snapshotId = 'model-1'; s.provenance = { kind: 'model', modelVersion: 'm', codeRevision: 'r', configVersion: 'c' };
      s.mmp = { status: 'unavailable', reason: 'no allocator' };
      s.electorateDetail = s.simulation.electoratePredictions.map((p: any) => ({
        electorateId: p.electorateId, uncertaintyClass: 'ordinary',
        candidates: p.candidates.map((c: any) => ({
          candidateId: c.candidateId, meanShare: 0.5, winProbability: { p: c.winProbability, mcse: 0, ess: 1 },
          share: [0.5, 0.8, 0.9].map(level => ({ lower: 0.4, median: 0.5, upper: 0.6, level, method: 'm' })),
        })),
      }));
    };
    const model = clone(base) as any; asModel(model);
    // Rename every id so only the remaining synthetic id under test can trigger the rule.
    const clean = JSON.parse(JSON.stringify(model).replace(/"synthetic-([^"]*)"/g, '"real-$1"'));
    expect(ForecastSnapshotSchema.safeParse(clean).success).toBe(true);
    reject(asModel, /Synthetic id/);
    const withId = (edit: (s: any) => void) => { const s = clone(clean); edit(s); return s; };
    for (const edit of [
      (s: any) => { s.directory.parties[0].partyId = 'Synthetic-party-x'; },
      (s: any) => { s.directory.electorates[0].electorateId = 'synthetic-electorate-x'; },
      (s: any) => { s.directory.candidates[0].candidateId = 'synthetic-candidate-x'; },
      (s: any) => { s.electionId = 'synthetic-election'; },
    ]) {
      const r = ForecastSnapshotSchema.safeParse(withId(edit));
      expect(r.success).toBe(false);
      expect(JSON.stringify(r.error?.issues)).toMatch(/Synthetic id/);
    }
  });
  it('requires per-seat detail in a model snapshot and an MMP example with an available seat layer', () => {
    const model = clone(base) as any;
    model.snapshotId = 'model-1'; model.provenance = { kind: 'model', modelVersion: 'm', codeRevision: 'r', configVersion: 'c' };
    model.mmp = { status: 'unavailable', reason: 'no allocator' };
    const r = ForecastSnapshotSchema.safeParse(JSON.parse(JSON.stringify(model).replace(/"synthetic-([^"]*)"/g, '"real-$1"')));
    expect(JSON.stringify(r.error?.issues)).toMatch(/uncertainty class and candidate-share intervals/);
    reject(s => { s.electorateDetail = [{ electorateId: 'nope', uncertaintyClass: 'ordinary', candidates: [] }]; }, /too_small|detail/);
  });
  it('requires a national vote share for every directory party', () => {
    reject(s => { s.national.partyVoteShares.pop(); }, /no national vote share/);
    reject(s => { s.directory.parties.push({ partyId: 'synthetic-party-extra', name: 'Extra', abbreviation: 'X' }); }, /no national vote share/);
  });
  it('carries the nowcast estimand and its dates (D106)', () => {
    reject(s => { s.schemaVersion = 1; }, /schemaVersion|expected/);
    reject(s => { delete s.targetType; }, /targetType/);
    reject(s => { s.targetType = 'forecast'; }, /targetType/);
    reject(s => { delete s.modelStateAsOf; }, /modelStateAsOf/);
    reject(s => { s.modelStateAsOf = '2026-10-07'; }, /cannot postdate the data cutoff/);
    reject(s => { s.dataCutoff = '2026-10-07T00:00:00+00:00'; }, /cannot postdate the snapshot/);
    reject(s => { s.electionDate = '2026-09-01'; }, /cannot postdate the election/);
    reject(s => { s.provenance = { kind: 'model', modelVersion: 'm', codeRevision: 'r' }; s.snapshotId = 'model-1'; }, /configVersion/);
  });
  it('requires nested 50/80/90 central intervals sharing one median', () => {
    reject(s => { s.national.partyVoteShares[0].share.pop(); }, /too_small|>=3|3/);
    reject(s => { s.national.partyVoteShares[0].share[1].level = 0.95; }, /50%, 80% and 90%/);
    reject(s => { s.national.partyVoteShares[0].share[2].median += 0.01; s.national.partyVoteShares[0].share[2].upper += 0.01; }, /one median/);
    reject(s => { const v = s.national.partyVoteShares[0].share; v[2].lower = v[1].lower + 1e-9; }, /contain narrower/);
    reject(s => { s.simulation.partySeatSummaries[0].seats[1].level = 0.9; }, /50%, 80% and 90%/);
  });
  it('requires an explicit unavailable record, never a zero', () => {
    const s = clone(base) as any; s.mmp = { status: 'unavailable', reason: 'no allocator' };
    expect(ForecastSnapshotSchema.safeParse(s).success).toBe(true);
    s.mmp = { status: 'unavailable' };
    expect(ForecastSnapshotSchema.safeParse(s).success).toBe(false);
  });
});

describe('archive index contract', () => {
  const entry = (n: number, over: object = {}) => ({
    snapshotId: `synthetic-${n}`, createdAt: `2026-10-0${n}T00:00:00+00:00`, dataCutoff: `2026-10-0${n}T00:00:00+00:00`,
    provenanceKind: 'synthetic-fixture', path: `synthetic-${n}/snapshot.json`, sha256: 'a'.repeat(64), supersedes: null, status: 'published', withdrawnReason: null, ...over,
  });
  it('accepts an append-only chain and rejects broken ones', () => {
    expect(ForecastIndexSchema.safeParse({ schemaVersion: 1, snapshots: [entry(1), entry(2, { supersedes: 'synthetic-1' })] }).success).toBe(true);
    for (const bad of [
      [entry(1), entry(1)], [entry(2), entry(1)], [entry(1, { supersedes: 'synthetic-9' })], [entry(1, { path: '../x/snapshot.json' })],
      [entry(1, { status: 'withdrawn' })], [entry(1, { provenanceKind: 'model' })], [entry(1, { path: 'synthetic-9/snapshot.json' })],
    ]) expect(ForecastIndexSchema.safeParse({ schemaVersion: 1, snapshots: bad }).success).toBe(false);
  });
});

describe('GeoJSON contract', () => {
  it('validates the synthetic boundary fixture and rejects features without an electorate id', () => {
    const data = JSON.parse(geometry);
    expect(ElectorateGeometrySchema.safeParse(data).success).toBe(true);
    delete data.features[0].properties.electorateId;
    expect(ElectorateGeometrySchema.safeParse(data).success).toBe(false);
  });
});
