import { describe, expect, it } from 'vitest';
import pythonBank from '../../../data/fixtures/synthetic/nowcast-draw-bank.json';
import { ForecastSnapshotSchema } from '../../types/export';
import { batchMeansMcse, chainOrder } from './batchMeans';
import { DrawBankSchema, type DrawBank } from './drawBank';
import { buildNowcastSnapshot, runSeatLayer, seatLayerConfig, type NowcastSnapshotOptions } from './fromBank';

const clone = <T,>(x: T): T => structuredClone(x);

/** SYNTHETIC FIXTURE: a hand-built three-seat bank with invented parties and candidates. */
function smallBank(n = 64): DrawBank {
  const groups = ['synthetic-party-a', 'synthetic-party-b', 'other'];
  const seat = (id: string, scope: 'general' | 'maori', k: number) => {
    const candidates = [`${id}-x`, `${id}-y`];
    const win = Array.from({ length: n }, (_, d) => ((d * 7 + k) % 5 < 2 ? 0 : 1));
    return {
      electorateId: id, scope, status: 'simulated' as const, class: scope === 'general' ? 'ordinary' as const : 'maori-layer' as const,
      candidates, candidateParty: ['synthetic-party-a', 'synthetic-party-b'],
      candidateShares: candidates.map(c => ({ candidateId: c, mean: 0.5, intervals: [0.5, 0.8, 0.9].map(level => ({ level, lower: 0.5 - level / 4, median: 0.5, upper: 0.5 + level / 4 })) })),
      winners: win,
    };
  };
  const seats = [seat('synthetic-electorate-1', 'general', 0), seat('synthetic-electorate-2', 'general', 1), seat('synthetic-electorate-3', 'maori', 2)];
  return DrawBankSchema.parse({
    schemaVersion: 3, stage: 73, electionYear: 2026, provenance: 'synthetic-fixture', configVersion: 'synthetic-config', estimand: 'nowcast',
    modelStateAsOf: '2026-09-27', dataCutoff: '2026-10-06', nationalStateKey: 'lastDataSupport', inputs: {}, draws: n, nationalDraws: n, layerReplicates: 1,
    drawIds: Array.from({ length: n }, (_, d) => `synthetic-chain${1 + (d % 4)}-draw${String(d).padStart(4, '0')}`),
    partyVote: { groups, otherBucket: 'other', ballotPartyIds: ['synthetic-party-a', 'synthetic-party-b', 'synthetic-party-c'], shares: Array.from({ length: n }, (_, d) => [0.45 + 0.002 * (d % 10), 0.45 - 0.002 * (d % 10), 0.1]) },
    seats,
    directory: {
      parties: groups.map(g => ({ partyId: g, name: g, abbreviation: g.slice(-1).toUpperCase() })),
      electorates: seats.map(s => ({ electorateId: s.electorateId, name: s.electorateId, kind: s.scope })),
      candidates: seats.flatMap(s => s.candidates.map((c, i) => ({ candidateId: c, name: c, electorateId: s.electorateId, partyId: s.candidateParty[i], partyLabel: s.candidateParty[i] }))),
    },
    diagnostics: {},
  });
}

const options = (over: Partial<NowcastSnapshotOptions> = {}): NowcastSnapshotOptions => ({
  snapshotId: 'synthetic-nowcast-1', createdAt: '2026-10-07T00:00:00+00:00', dataCutoff: '2026-10-06T00:00:00+00:00',
  electionId: 'synthetic-election-2026', electionDate: '2026-11-07', boundaryVersionId: 'stats-nz-electorates-final-2025',
  modelVersion: 'synthetic-model', codeRevision: 'synthetic-revision', bankSha256: 'a'.repeat(64),
  mmp: { rulesVersion: 'UNVERIFIED-PLACEHOLDER-synthetic-only', rulesSourceIds: ['synthetic-rules'], blocs: [{ id: 'synthetic-bloc', label: 'Synthetic bloc', partyIds: ['synthetic-party-a'] }] },
  nationalBasis: 'Synthetic draws', limitations: ['SYNTHETIC FIXTURE: not a nowcast.'], ...over,
});

describe('draw bank contract', () => {
  it('accepts the hand-built bank and the Python-generated synthetic bank', () => {
    expect(smallBank().seats).toHaveLength(3);
    const parsed = DrawBankSchema.parse(pythonBank);
    expect(parsed.provenance).toBe('synthetic-fixture');
    expect(parsed.seats).toHaveLength(71);
  });
  it('rejects missing winners, duplicate draw ids and class/scope mismatches', () => {
    const reject = (edit: (b: any) => void) => { const b = clone(smallBank()) as any; edit(b); expect(DrawBankSchema.safeParse(b).success).toBe(false); };
    reject(b => { b.seats[0].winners.pop(); });
    reject(b => { b.drawIds[1] = b.drawIds[0]; });
    reject(b => { b.seats[2].class = 'ordinary'; });
    reject(b => { b.partyVote.ballotPartyIds = ['synthetic-party-a']; });  // a party group missing from the ballot
    reject(b => { b.partyVote.ballotPartyIds.push('other'); });
    reject(b => { b.seats[0].winners[0] = 7; });
    reject(b => { b.partyVote.shares[0][0] += 0.1; });
    reject(b => { b.seats[1] = { electorateId: b.seats[1].electorateId, scope: 'general', status: 'unavailable' }; });
  });
  it('accepts the Stage79 seat-poll record on a general seat only and rejects an out-of-range one', () => {
    const poll = { pollIds: ['synthetic-poll'], pollValue: 0.4, pollVariance: 0.2, ageWeeks: 2, rho: 0.8, weight: 0.5, modelCentre: -0.2, modelSD: 0.35,
      shift: 0.1, posteriorSD: 0.3, sharedSD: 0.18 };
    const withPoll = (edit: (b: any) => void) => { const b = clone(smallBank()) as any; edit(b); return DrawBankSchema.safeParse(b).success; };
    expect(withPoll(b => { b.seats[0].seatPoll = poll; })).toBe(true);
    expect(withPoll(b => { b.seats[2].seatPoll = poll; })).toBe(false);
    expect(withPoll(b => { b.seats[0].seatPoll = { ...poll, rho: 1.5 }; })).toBe(false);
    expect(withPoll(b => { b.seats[0].seatPoll = { ...poll, extra: 1 }; })).toBe(false);
  });
});

describe('batch-means Monte Carlo error', () => {
  const ids = Array.from({ length: 400 }, (_, d) => `x-chain${1 + Math.floor(d / 100)}-draw${String(d % 100).padStart(4, '0')}`);
  it('is near the binomial error for independent values and larger for correlated ones', () => {
    let state = 12345;
    const uniform = () => { state = (1103515245 * state + 12345) % 2 ** 31; return state / 2 ** 31; };
    const iid = ids.map(() => (uniform() < 0.3 ? 1 : 0));
    const r = batchMeansMcse(iid, chainOrder(ids));
    const naive = Math.sqrt(r.mean * (1 - r.mean) / 400);
    expect(r.mcse / naive).toBeGreaterThan(0.6);
    expect(r.mcse / naive).toBeLessThan(1.6);
    const sticky = ids.map((_, d) => (Math.floor((d % 100) / 25) % 2 === 0 ? 1 : 0));
    const s = batchMeansMcse(sticky, chainOrder(ids));
    expect(s.mcse).toBeGreaterThan(2 * Math.sqrt(0.25 / 400));
    expect(s.ess).toBeLessThan(400);
    expect(batchMeansMcse(ids.map(() => 1), chainOrder(ids))).toMatchObject({ mean: 1, mcse: 0 });
  });
  it('keeps each national draw\'s layer replicates together and in one batch', () => {
    const national = ['x-chain1-draw0001', 'x-chain1-draw0000', 'x-chain2-draw0000'];
    const layout = chainOrder(national, 2);
    expect(layout.chains).toEqual([[2, 3, 0, 1], [4, 5]]);
    const values = Array.from({ length: 6 }, (_, r) => Math.floor(r / 2) % 2);
    expect(batchMeansMcse(values, layout, 2).batchSize % 2).toBe(0);
  });
  it('orders rows by chain and draw, whatever the bank order', () => {
    const shuffled = [...ids].reverse();
    expect(chainOrder(shuffled).chains[0][0]).toBe(shuffled.indexOf(ids[0]));
    expect(() => chainOrder(['not-a-draw-id'])).toThrow(/chain/);
  });
});

describe('nowcast snapshot from a draw bank', () => {
  it('runs the seat layer on every row and exports nested intervals with effective-sample errors', async () => {
    const s = await buildNowcastSnapshot(smallBank(), options());
    expect(ForecastSnapshotSchema.safeParse(s).success).toBe(true);
    expect(s.targetType).toBe('nowcast');
    expect(s.seatLayer.status).toBe('available');
    if (s.seatLayer.status !== 'available') return;
    const a = s.seatLayer.summary.parties.find(p => p.partyId === 'synthetic-party-a')!;
    expect(a.seats.map(v => v.level)).toEqual([0.5, 0.8, 0.9]);
    expect(a.probQualified.p).toBe(1);
    expect(s.seatLayer.summary.draws).toBe(64);
    expect(s.seatLayer.summary.blocs[0].probMajority.mcse).toBeGreaterThanOrEqual(0);
    expect(s.electorateDetail).toHaveLength(3);
    expect(s.electorateDetail[2].uncertaintyClass).toBe('maori-layer');
    const sum = s.simulation.electoratePredictions[0].candidates.reduce((x, c) => x + c.winProbability, 0);
    expect(sum).toBeCloseTo(1, 12);
    expect(JSON.stringify(await buildNowcastSnapshot(smallBank(), options()))).toBe(JSON.stringify(s));
  });

  it('seats a ballot party simulated inside the other bucket as overhang, not as an independent (audit J3)', () => {
    const bank = clone(smallBank());
    const maori = bank.seats[2] as any;
    maori.candidateParty = ['synthetic-party-a', 'synthetic-party-c'];  // party c is on the ballot but not a simulated party group
    const mmp = options().mmp!;
    const config = seatLayerConfig(bank, mmp);
    expect(config.zeroVotePartyIds).toEqual(['synthetic-party-c']);
    const { outcomes } = runSeatLayer(bank, config, 'synthetic-election-2026');
    const wins = maori.winners.map((w: number) => w === 1);
    expect(wins.some(Boolean)).toBe(true);
    outcomes.forEach((o, row) => {
      expect(o.independentElectorateSeats).toBe(0);
      expect(o.parliamentSize).toBe(wins[row] ? 121 : 120);
      expect(o.parties['synthetic-party-c']?.overhang ?? 0).toBe(wins[row] ? 1 : 0);
    });
  });

  it('exports the Māori C–P range from the inflation winners and keeps the seat totals on the control (D127)', async () => {
    const plain = await buildNowcastSnapshot(smallBank(), options());
    const bank = clone(smallBank()) as any;
    bank.seats[2].inflationWinners = bank.seats[2].winners.map((_: number, d: number) => (d % 2));
    const parsed = DrawBankSchema.parse(bank);
    const s = await buildNowcastSnapshot(parsed, options());
    const maori = s.electorateDetail[2];
    expect(maori.candidates.map(c => c.winProbabilityInflation?.p)).toEqual([0.5, 0.5]);
    expect(maori.candidates.map(c => c.winProbability)).toEqual(plain.electorateDetail[2].candidates.map(c => c.winProbability));
    expect(s.electorateDetail[0].candidates.every(c => c.winProbabilityInflation === undefined)).toBe(true);
    expect(s.seatLayer).toEqual(plain.seatLayer);
    expect(s.simulation.electoratePredictions).toEqual(plain.simulation.electoratePredictions);
    const reject = (edit: (b: any) => void) => { const b = clone(bank); edit(b); expect(DrawBankSchema.safeParse(b).success).toBe(false); };
    reject(b => { b.seats[0].inflationWinners = b.seats[0].winners; });  // general seats have no calibration range
    reject(b => { b.seats[2].inflationWinners.pop(); });
    reject(b => { b.seats[2].inflationWinners[0] = 5; });
  });

  it('withholds the seat layer and MMP when any seat is unavailable, never zero-filling', async () => {
    const bank = clone(smallBank()) as any;
    bank.seats[1] = { electorateId: bank.seats[1].electorateId, scope: 'general', status: 'unavailable', reason: 'roster pending' };
    const s = await buildNowcastSnapshot(bank, options());
    expect(s.seatLayer.status).toBe('unavailable');
    expect(s.mmp.status).toBe('unavailable');
    expect(s.unavailableElectorates).toEqual([{ electorateId: 'synthetic-electorate-2', reason: 'roster pending' }]);
    expect(s.simulation.partySeatSummaries).toEqual([]);
    const withoutRules = await buildNowcastSnapshot(smallBank(), options({ mmp: null }));
    expect(withoutRules.seatLayer.status).toBe('unavailable');
  });

  it('cannot present a synthetic bank as a model snapshot', async () => {
    await expect(buildNowcastSnapshot(smallBank(), options({ snapshotId: 'model-1' }))).rejects.toThrow();
    const live = clone(smallBank()) as any; live.provenance = 'live';
    await expect(buildNowcastSnapshot(live, options({ snapshotId: 'model-1', mmp: null }))).rejects.toThrow(/Synthetic id/);
  });

  it('reports James\'s blocs and the hung-parliament outcomes with TOP as kingmaker', async () => {
    const config = (await import('../../../config/nowcast-2026.json')).default as any;
    const s = await buildNowcastSnapshot(pythonBank, options({ electionId: 'nz-general-2026',
      mmp: { rulesVersion: 'UNVERIFIED-PLACEHOLDER-synthetic-only', rulesSourceIds: ['synthetic-rules'],
        blocs: config.mmp.blocs, hungParliament: config.mmp.hungParliament } }));
    if (s.seatLayer.status !== 'available') throw new Error('seat layer expected');
    expect(s.seatLayer.summary.blocs.map(b => b.label)).toEqual(['NAT+ACT', 'NAT+ACT+NZF', 'LAB+GRN', 'LAB+GRN+TPM']);
    const [hung, either, rightOnly, leftOnly] = s.seatLayer.summary.scenarios.map(x => x.probability.p);
    expect(s.seatLayer.summary.scenarios.map(x => x.id)).toEqual(['hung', 'hung-opportunity-kingmaker',
      'hung-opportunity-nat-act-nzf-only', 'hung-opportunity-lab-grn-tpm-only']);
    expect(either + rightOnly + leftOnly).toBeLessThanOrEqual(hung + 1e-12);
    const right = s.seatLayer.summary.blocs[1].probMajority.p, left = s.seatLayer.summary.blocs[3].probMajority.p;
    expect(hung).toBeGreaterThanOrEqual(1 - right - left - 1e-12);
    await expect(buildNowcastSnapshot(pythonBank, options({ electionId: 'nz-general-2026',
      mmp: { rulesVersion: 'x', rulesSourceIds: ['x'], blocs: config.mmp.blocs, hungParliament: { blocs: ['nat-act', 'nope'] } } }))).rejects.toThrow();
  });

  it('builds a full 71-seat synthetic snapshot from the Python bank', async () => {
    const s = await buildNowcastSnapshot(pythonBank, options({
      electionId: 'nz-general-2026',
      mmp: { rulesVersion: 'UNVERIFIED-PLACEHOLDER-synthetic-only', rulesSourceIds: ['synthetic-rules'], blocs: [] },
    }));
    expect(s.directory.electorates).toHaveLength(71);
    expect(s.unavailableElectorates).toEqual([]);
    expect(s.seatLayer.status).toBe('available');
    if (s.seatLayer.status === 'available') {
      const total = s.seatLayer.summary.parties.reduce((x, p) => x + p.meanSeats, 0);
      expect(total).toBeGreaterThanOrEqual(120 - 71); // list plus electorate seats of listed parties, independents aside
      expect(s.seatLayer.summary.parliament.size.map(v => v.level)).toEqual([0.5, 0.8, 0.9]);
    }
    const classes = new Set(s.electorateDetail.map(d => d.uncertaintyClass));
    expect(classes).toEqual(new Set(['ordinary', 'exceptional', 'maori-layer']));
  });
});

describe('per-seat evidence (Stage85)', () => {
  const build = (bank: unknown) => buildNowcastSnapshot(bank, options({
    electionId: 'nz-general-2026', mmp: { rulesVersion: 'UNVERIFIED-PLACEHOLDER-synthetic-only', rulesSourceIds: ['synthetic-rules'], blocs: [] },
  }));
  const withPoll = () => {
    const bank = clone(pythonBank) as any;
    const seat = bank.seatEvidence.find((e: any) => e.pollUpdate);
    return { bank, seat };
  };

  it('is carried from the bank into the snapshot unchanged, one record per predicted seat', async () => {
    const s = await build(pythonBank);
    expect(s.seatEvidence).toHaveLength(71);
    expect(s.seatEvidence).toEqual((pythonBank as any).seatEvidence);
    expect(s.seatEvidence!.map(e => e.uncertaintyClass)).toEqual(s.electorateDetail.map(d => d.uncertaintyClass));
    const polled = s.seatEvidence!.filter(e => e.pollUpdate);
    expect(polled.length).toBeGreaterThan(0);
    polled.forEach(e => {
      const used = e.polls.filter(p => p.status === 'used');
      expect(used.reduce((a, p) => a + p.weight!, 0)).toBeCloseTo(e.pollUpdate!.effectiveWeight, 9);
      expect(used.reduce((a, p) => a + p.shareOfPoll!, 0)).toBeCloseTo(1, 9);
    });
  });
  it('is optional: a bank without it gives a snapshot without it', async () => {
    const bank = clone(pythonBank) as any;
    delete bank.seatEvidence;
    expect((await build(bank)).seatEvidence).toBeUndefined();
  });
  it('rejects evidence that is incomplete, inconsistent or mislabelled', async () => {
    const reject = async (edit: (b: any, seat: any) => void) => {
      const { bank, seat } = withPoll();
      edit(bank, seat);
      await expect(build(bank)).rejects.toThrow();
    };
    await reject(b => { b.seatEvidence.pop(); });
    await reject(b => { b.seatEvidence[1] = b.seatEvidence[0]; });
    await reject(b => { b.seatEvidence[0].uncertaintyClass = b.seatEvidence[0].uncertaintyClass === 'ordinary' ? 'exceptional' : 'ordinary'; });
    await reject((_, s) => { s.polls.find((p: any) => p.status === 'used').weight += 0.1; });
    await reject((_, s) => { s.polls.find((p: any) => p.status === 'used').shareOfPoll = 0.5; });
    await reject((_, s) => { s.pollUpdate.modelWeight += 0.1; });
    await reject((_, s) => { s.pollUpdate = null; });
    await reject((_, s) => { s.baseline.partyVote[0].share += 0.1; });
    await reject((_, s) => { s.baseline.partyVote[0].partyId = 'not-a-party'; });
    await reject((_, s) => { s.polls[0].status = 'not-used'; s.polls[0].reason = null; });
    await reject((_, s) => { s.polls[0].extra = 1; });
    await reject(b => { const m = b.seatEvidence.find((e: any) => e.uncertaintyClass === 'maori-layer'); m.multipliers = { balance: 1, within: 1, mass: 1 }; });
  });
});
