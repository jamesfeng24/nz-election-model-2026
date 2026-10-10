// @vitest-environment node
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import oracle from '../../../data/processed/mmp/oracle-seat-tables.json';
import { MmpAllocationSchema } from '../../types/domain';
import { createRng } from '../simulation/prng';
import type { PipelineInputs } from '../simulation/pipeline';
import {
  allocateDraw, allocateDrawFromVotes, sharesToVotes, SeatSummaryAccumulator, TieAtCutoffError,
  type ElectorateWinnerInput, type SeatDrawOutcome, type SeatLayerConfig, type SeatLayerDraw,
} from './seatLayer';
import { createSeatLayerMmpStage } from './seatLayerStage';

const RULES = { rulesVersion: 'electoral-act-1993-2026-01-01', rulesSourceIds: ['test-rules'] };

// ---------------------------------------------------------------------------------------------------------
// Official reproduction 2008-2023: actual party votes and actual electorate winners through the seat layer.

interface CandidateRecord { year: number; elected: boolean; party: string; electorateId: string; id: string }
const candidates: CandidateRecord[] = JSON.parse(
  readFileSync(new URL('../../../data/processed/historical/2008-2023/candidate-votes.json', import.meta.url), 'utf8')).records;

describe('official reproduction 2008-2023 (actual votes and winners)', () => {
  for (const election of oracle.elections) {
    const listed = election.listedParties.map(p => p.partyName);
    // General electorate winners come from the preserved candidate results.
    const general: ElectorateWinnerInput[] = candidates
      .filter(r => r.year === election.year && r.elected)
      .map(r => ({ electorateId: r.electorateId, partyId: r.party, candidateId: r.id }));
    // The candidate file carries no Māori electorate candidates; allocation needs only seat counts per party, so
    // the Māori winners are the residual between the official constituency seats and the general winners.
    const generalCount = new Map<string, number>();
    for (const w of general) generalCount.set(w.partyId!, (generalCount.get(w.partyId!) ?? 0) + 1);
    const maori: ElectorateWinnerInput[] = [];
    for (const p of election.listedParties) {
      const residual = p.constituencySeats - (generalCount.get(p.partyName) ?? 0);
      expect(residual, `${election.year} ${p.partyName} residual`).toBeGreaterThanOrEqual(0);
      for (let i = 0; i < residual; i++) maori.push({ electorateId: `maori-${election.year}-${p.partyName}-${i}`, partyId: p.partyName });
    }
    const config: SeatLayerConfig = { ...RULES, listedPartyIds: listed, blocs: [] };
    const totalVotes = election.listedParties.reduce((s, p) => s + p.partyVotes, 0);

    const check = (outcome: SeatDrawOutcome) => {
      MmpAllocationSchema.parse(outcome.allocation);
      for (const p of election.listedParties) expect(outcome.parties[p.partyName].listSeats, `${election.year} ${p.partyName}`).toBe(p.officialListSeats);
      expect(outcome.parliamentSize).toBe(election.officialParliamentSize);
      expect(outcome.unfilledSeats).toBe(0);
      expect(outcome.lotsDrawn).toBe(0);
    };

    it(`${election.year}: exact integer votes reproduce every list seat and the Parliament size`, () => {
      expect(maori.length, 'Māori seats').toBe(7);
      expect(general.length + maori.length).toBe(election.listedParties.reduce((s, p) => s + p.constituencySeats, 0));
      check(allocateDrawFromVotes(config, {
        electionId: `nz-${election.year}`, generalWinners: general, maoriWinners: maori,
        partyVotes: Object.fromEntries(election.listedParties.map(p => [p.partyName, p.partyVotes])),
      }));
    });

    it(`${election.year}: the share path reproduces the same result`, () => {
      check(allocateDraw(config, {
        electionId: `nz-${election.year}`, generalWinners: general, maoriWinners: maori,
        partyVoteShares: Object.fromEntries(election.listedParties.map(p => [p.partyName, p.partyVotes / totalVotes])),
      }));
    });
  }

  it('covers the four overhang elections and the three without', () => {
    expect(Object.fromEntries(oracle.elections.map(e => [e.year, e.officialParliamentSize - 120])))
      .toEqual({ 2008: 2, 2011: 1, 2014: 1, 2017: 0, 2020: 0, 2023: 2 });
  });
});

// ---------------------------------------------------------------------------------------------------------
// Synthetic draws (labelled synthetic; used only in tests, never in a result).

const SYN: SeatLayerConfig = {
  ...RULES,
  listedPartyIds: ['A', 'B', 'C', 'D', 'E', 'F'],
  unlistedBucketIds: ['OTH'],
  blocs: [{ id: 'synthetic-bloc-1', label: 'Synthetic bloc 1', partyIds: ['A', 'B'] }, { id: 'synthetic-bloc-2', label: 'Synthetic bloc 2', partyIds: ['C', 'D'] }],
};
const GENERAL = Array.from({ length: 64 }, (_, i) => `syn-g${i + 1}`);
const MAORI = Array.from({ length: 7 }, (_, i) => `syn-m${i + 1}`);

function syntheticDraw(seed: string, index: number): SeatLayerDraw {
  const rng = createRng(seed, `draw:${index}`);
  const ids = [...SYN.listedPartyIds, 'OTH'];
  const weight = ids.map((_, i) => -Math.log(1 - rng.uniform()) * [6, 5, 2, 1, 0.4, 0.15, 0.6][i]);
  const total = weight.reduce((a, b) => a + b, 0);
  const winnerParty = () => {
    const u = rng.uniform();
    if (u < 0.04) return null; // independent
    if (u < 0.06) return 'OTH'; // bucket winner: treated as non-listed
    const ws = weight.slice(0, 6), s = ws.reduce((a, b) => a + b, 0);
    let c = 0;
    for (let i = 0; i < 6; i++) { c += ws[i] / s; if (u - 0.06 < c * 0.94) return ids[i]; }
    return ids[0];
  };
  return {
    electionId: 'synthetic-election',
    partyVoteShares: Object.fromEntries(ids.map((id, i) => [id, weight[i] / total])),
    generalWinners: GENERAL.map(electorateId => ({ electorateId, partyId: winnerParty() })),
    maoriWinners: MAORI.map(electorateId => ({ electorateId, partyId: rng.uniform() < 0.7 ? 'B' : 'C' })),
  };
}

describe('property tests on seeded synthetic draws', () => {
  const outcomes = Array.from({ length: 400 }, (_, i) => {
    const draw = syntheticDraw('stage65-properties', i);
    return { draw, outcome: allocateDraw(SYN, draw, { uniform: () => 0.5 }) };
  });

  it('reconciles seat accounting with the allocation schema in every draw', () => {
    for (const { outcome } of outcomes) MmpAllocationSchema.parse(outcome.allocation);
  });

  it('sets Parliament size to nominal plus overhang, with no unfilled seats when lists are not limited', () => {
    for (const { outcome } of outcomes) {
      expect(outcome.parliamentSize).toBe(120 + outcome.overhangSeats);
      expect(outcome.unfilledSeats).toBe(0);
      const filled = Object.values(outcome.parties).reduce((s, p) => s + p.totalSeats, outcome.independentElectorateSeats);
      expect(filled).toBe(outcome.parliamentSize);
    }
  });

  it('gives entitlements that sum to the seats allocated, so independents reduce the Sainte-Laguë total', () => {
    for (const { outcome } of outcomes) {
      const entitlements = Object.values(outcome.parties).reduce((s, p) => s + p.entitlement, 0);
      expect(entitlements).toBe(120 - outcome.independentElectorateSeats);
    }
    expect(outcomes.some(({ outcome }) => outcome.independentElectorateSeats > 0)).toBe(true);
  });

  it('seats only qualified parties and attributes overhang only to parties with excess electorate seats', () => {
    for (const { outcome } of outcomes) {
      for (const p of Object.values(outcome.parties)) {
        if (!p.qualified) { expect(p.totalSeats).toBe(0); expect(p.entitlement).toBe(0); }
        expect(p.listSeats).toBe(Math.max(0, p.entitlement - p.electorateSeats));
        expect(p.overhang).toBe(Math.max(0, p.electorateSeats - p.entitlement));
        expect(p.totalSeats).toBe(Math.max(p.entitlement, p.electorateSeats));
      }
      expect(Object.values(outcome.parties).reduce((s, p) => s + p.overhang, 0)).toBe(outcome.overhangSeats);
    }
    expect(outcomes.some(({ outcome }) => outcome.overhangSeats > 0)).toBe(true);
    expect(outcomes.some(({ outcome }) => outcome.overhangSeats === 0)).toBe(true);
  });

  it('is deterministic and invariant to the order of parties and winners', () => {
    for (const { draw, outcome } of outcomes.slice(0, 40)) {
      expect(allocateDraw(SYN, draw, { uniform: () => 0.5 })).toEqual(outcome);
      const reorderedConfig: SeatLayerConfig = { ...SYN, listedPartyIds: [...SYN.listedPartyIds].reverse() };
      const reordered = allocateDraw(reorderedConfig, {
        ...draw, generalWinners: [...draw.generalWinners].reverse(), maoriWinners: [...draw.maoriWinners].reverse(),
      }, { uniform: () => 0.5 });
      expect(reordered.parties).toEqual(outcome.parties);
      expect(reordered.parliamentSize).toBe(outcome.parliamentSize);
    }
  });

  it('never lowers a party entitlement when only its own votes rise, and never raises anyone else’s', () => {
    for (const { draw } of outcomes.slice(0, 60)) {
      const votes = sharesToVotes(draw.partyVoteShares, 1_000_000_000);
      const { partyVoteShares: _unused, ...rest } = draw;
      void _unused;
      const before = allocateDrawFromVotes(SYN, { ...rest, partyVotes: votes }, { uniform: () => 0.5 });
      for (const target of SYN.listedPartyIds) {
        const after = allocateDrawFromVotes(SYN, { ...rest, partyVotes: { ...votes, [target]: Math.round(votes[target] * 1.1) + 1 } }, { uniform: () => 0.5 });
        for (const id of SYN.listedPartyIds) {
          if (id === target) expect(after.parties[id].entitlement).toBeGreaterThanOrEqual(before.parties[id].entitlement);
          else expect(after.parties[id].entitlement).toBeLessThanOrEqual(before.parties[id].entitlement);
        }
      }
    }
  });

  it('is invariant to scaling all integer votes', () => {
    for (const { draw } of outcomes.slice(0, 20)) {
      const votes = sharesToVotes(draw.partyVoteShares, 1_000_000);
      const { partyVoteShares: _unused, ...rest } = draw;
      void _unused;
      const a = allocateDrawFromVotes(SYN, { ...rest, partyVotes: votes });
      const b = allocateDrawFromVotes(SYN, { ...rest, partyVotes: Object.fromEntries(Object.entries(votes).map(([k, v]) => [k, v * 7])) });
      expect(b.parties).toEqual(a.parties);
    }
  });
});

describe('aggregate vote buckets and the threshold', () => {
  const config: SeatLayerConfig = { ...RULES, nominalSeats: 20, listedPartyIds: ['A', 'B', 'C'], unlistedBucketIds: ['OTH'], blocs: [] };
  const run = (votes: Record<string, number>, general: ElectorateWinnerInput[] = []) =>
    allocateDrawFromVotes(config, { electionId: 'synthetic', partyVotes: votes, generalWinners: general, maoriWinners: [] });

  it('counts bucket votes in the total, so exactly 5% of all valid votes qualifies and just under does not', () => {
    const at = run({ A: 50, B: 450, C: 200, OTH: 300 });
    expect(at.parties.A.qualified).toBe(true); // 50/1000 = 5.0%, inclusive
    const under = run({ A: 49, B: 451, C: 200, OTH: 300 });
    expect(under.parties.A).toMatchObject({ qualified: false, totalSeats: 0 });
    // Measured against listed parties only, 49 of 700 would be 7%: the bucket must count in the total.
    expect(under.parties.B.qualified).toBe(true);
  });

  it('never seats a bucket, however large, and still allocates every seat among qualified listed parties', () => {
    const big = run({ A: 120, B: 100, C: 80, OTH: 700 });
    expect(Object.values(big.parties).reduce((s, p) => s + p.entitlement, 0)).toBe(20);
    expect(Object.keys(big.parties)).toEqual(['A', 'B', 'C']);
    expect(MmpAllocationSchema.parse(big.allocation).parties.map(p => p.partyId)).toEqual(['A', 'B', 'C']);
  });

  it('lets an under-5% party qualify through one electorate win, and reports it as the lifeboat', () => {
    const r = run({ A: 30, B: 500, C: 200, OTH: 270 }, [{ electorateId: 'e1', partyId: 'A' }]);
    expect(r.parties.A).toMatchObject({ qualified: true, qualifiedByPartyVote: false, qualifiedByElectorate: true, electorateSeats: 1 });
    expect(r.parties.A.totalSeats).toBeGreaterThanOrEqual(1);
  });

  it('treats a null, unlisted or bucket winner as an independent seat that is not allocated by Sainte-Laguë', () => {
    const r = run({ A: 500, B: 300, C: 200, OTH: 0 }, [
      { electorateId: 'e1', partyId: null }, { electorateId: 'e2', partyId: 'not-on-ballot' }, { electorateId: 'e3', partyId: 'OTH' }]);
    expect(r.independentElectorateSeats).toBe(3);
    expect(Object.values(r.parties).reduce((s, p) => s + p.entitlement, 0)).toBe(17);
    expect(r.parliamentSize).toBe(20);
  });

  // Audit J3 (James, 2026-10-10): a party on the party-list ballot whose vote sits inside the bucket (Te Tai Tokerau Party in 2026) qualifies
  // through its electorate win with zero party votes of its own, so its seat is overhang and Parliament grows, not an independent seat inside 20.
  const zeroConfig: SeatLayerConfig = { ...config, zeroVotePartyIds: ['T'] };
  const zeroRun = (votes: Record<string, number>, general: ElectorateWinnerInput[] = []) =>
    allocateDrawFromVotes(zeroConfig, { electionId: 'synthetic', partyVotes: votes, generalWinners: general, maoriWinners: [] });

  it('seats a bucketed list-party electorate winner as that party\'s overhang seat', () => {
    const votes = { A: 500, B: 300, C: 150, OTH: 50 };
    const r = zeroRun(votes, [{ electorateId: 'e1', partyId: 'T' }, { electorateId: 'e2', partyId: null }]);
    expect(r.independentElectorateSeats).toBe(1);
    expect(r.parties.T).toMatchObject({ qualified: true, qualifiedByPartyVote: false, qualifiedByElectorate: true, electorateSeats: 1, listSeats: 0, entitlement: 0, overhang: 1 });
    expect(r.overhangSeats).toBe(1);
    expect(r.parliamentSize).toBe(21);
    expect(['A', 'B', 'C'].reduce((s, p) => s + r.parties[p].entitlement, 0)).toBe(19);  // 20 less the independent
    MmpAllocationSchema.parse(r.allocation);
    // As an independent (the earlier rule) the same win took a Sainte-Laguë seat from the other parties.
    const before = run(votes, [{ electorateId: 'e1', partyId: 'T' }, { electorateId: 'e2', partyId: null }]);
    expect(before.independentElectorateSeats).toBe(2);
    expect(before.parliamentSize).toBe(20);
    expect(['A', 'B', 'C'].reduce((s, p) => s + before.parties[p].entitlement, 0)).toBe(18);
  });

  it('leaves a draw without such a winner unchanged and keeps the party out of the allocation', () => {
    const votes = { A: 500, B: 300, C: 150, OTH: 50 }, winners = [{ electorateId: 'e1', partyId: 'A' }];
    const r = zeroRun(votes, winners);
    expect(r).toEqual(run(votes, winners));
    expect(r.parties.T).toBeUndefined();
  });

  it('rejects a zero-vote party that is also listed, a bucket or repeated', () => {
    const draw = { electionId: 'synthetic', partyVotes: { A: 500, B: 300, C: 150, OTH: 50 }, generalWinners: [], maoriWinners: [] };
    for (const zeroVotePartyIds of [['A'], ['OTH'], ['T', 'T'], ['']])
      expect(() => allocateDrawFromVotes({ ...config, zeroVotePartyIds }, draw)).toThrow(/zeroVotePartyIds/);
  });
});

describe('exact ties (s 191(9))', () => {
  const config: SeatLayerConfig = { ...RULES, nominalSeats: 1, listedPartyIds: ['A', 'B'], blocs: [] };
  const draw = { electionId: 'synthetic', partyVotes: { A: 100, B: 100 }, generalWinners: [], maoriWinners: [] };

  it('refuses to choose silently without a stream', () => {
    expect(() => allocateDrawFromVotes(config, draw)).toThrow(TieAtCutoffError);
  });
  it('draws a lot from the supplied stream, records it, and both outcomes are reachable', () => {
    const a = allocateDrawFromVotes(config, draw, { uniform: () => 0.1 });
    const b = allocateDrawFromVotes(config, draw, { uniform: () => 0.9 });
    expect([a.parties.A.totalSeats, a.parties.B.totalSeats]).toEqual([1, 0]);
    expect([b.parties.A.totalSeats, b.parties.B.totalSeats]).toEqual([0, 1]);
    expect(a.lotsDrawn).toBe(1);
    expect(allocateDrawFromVotes({ ...config, nominalSeats: 2 }, draw).lotsDrawn).toBe(0);
  });
});

describe('input validation', () => {
  const base = syntheticDraw('stage65-validation', 0);
  const strict: SeatLayerConfig = { ...SYN, expectedElectorateIds: { general: GENERAL, maori: MAORI } };

  it('accepts a complete draw with Māori winners as a separate input', () => {
    const r = allocateDraw(strict, base, { uniform: () => 0.5 });
    MmpAllocationSchema.parse(r.allocation);
    const maoriSeats = base.maoriWinners.length;
    const electorate = Object.values(r.parties).reduce((s, p) => s + p.electorateSeats, r.independentElectorateSeats);
    expect(electorate).toBe(GENERAL.length + maoriSeats);
  });
  it('rejects a missing electorate rather than treating it as zero', () => {
    expect(() => allocateDraw(strict, { ...base, maoriWinners: base.maoriWinners.slice(1) })).toThrow(/Māori winners must cover/);
    expect(() => allocateDraw(strict, { ...base, generalWinners: base.generalWinners.slice(1) })).toThrow(/General winners must cover/);
  });
  it('rejects an electorate that appears twice or in both inputs', () => {
    expect(() => allocateDraw(SYN, { ...base, maoriWinners: [{ electorateId: GENERAL[0], partyId: 'B' }] })).toThrow(/more than one winner|both/);
    expect(() => allocateDraw(SYN, { ...base, generalWinners: [...base.generalWinners, base.generalWinners[0]] })).toThrow(/more than one winner/);
  });
  it('rejects shares that do not sum to one, are missing or are unknown, and never renormalises', () => {
    const shares = { ...base.partyVoteShares };
    expect(() => allocateDraw(SYN, { ...base, partyVoteShares: { ...shares, A: shares.A + 0.01 } })).toThrow(/sum/);
    const { A: _a, ...withoutA } = shares;
    void _a;
    expect(() => allocateDraw(SYN, { ...base, partyVoteShares: withoutA })).toThrow(/never treated as zero/);
    expect(() => allocateDraw(SYN, { ...base, partyVoteShares: { ...shares, ZZZ: 0 } })).toThrow(/Unknown party/);
    expect(() => allocateDraw(SYN, { ...base, partyVoteShares: { ...shares, A: -0.1, B: shares.B + shares.A + 0.1 } })).toThrow(/non-negative/);
  });
  it('rejects bad configuration', () => {
    expect(() => allocateDraw({ ...SYN, blocs: [{ id: 'x', label: 'x', partyIds: ['A', 'NOPE'] }] }, base)).toThrow(/Bloc x/);
    expect(() => allocateDraw({ ...SYN, unlistedBucketIds: ['A'] }, base)).toThrow(/disjoint/);
    expect(() => allocateDraw({ ...SYN, voteScale: 1e15 }, base)).toThrow(/voteScale/);
  });
  it('converts shares to integer votes summing exactly to the scale', () => {
    const votes = sharesToVotes({ a: 1 / 3, b: 1 / 3, c: 1 / 3 }, 100);
    expect(Object.values(votes).reduce((x, y) => x + y, 0)).toBe(100);
    expect(Object.values(votes).sort()).toEqual([33, 33, 34]);
  });
});

describe('summaries', () => {
  const config: SeatLayerConfig = {
    ...RULES, nominalSeats: 4, listedPartyIds: ['A', 'B'],
    blocs: [{ id: 'synthetic-A', label: 'Synthetic A bloc', partyIds: ['A'] }],
  };
  const draw = (a: number, b: number) => allocateDrawFromVotes(config, { electionId: 'synthetic', partyVotes: { A: a, B: b }, generalWinners: [], maoriWinners: [] });

  it('reports majority, exact half and the distribution on a hand-worked three-draw case', () => {
    // 700/300 -> A 3, B 1 (majority); 500/500 -> 2/2 (exactly half); 100/900 -> A 0, B 4.
    const acc = new SeatSummaryAccumulator(config);
    for (const d of [draw(700, 300), draw(500, 500), draw(100, 900)]) acc.add(d);
    const s = acc.summarise();
    const bloc = s.blocs[0];
    expect(bloc.probMajority.p).toBeCloseTo(1 / 3, 12);
    expect(bloc.probExactHalf.p).toBeCloseTo(1 / 3, 12);
    expect(bloc.probMajority.mcse).toBeCloseTo(Math.sqrt((1 / 3) * (2 / 3) / 3), 12);
    expect(bloc.seatDistribution).toEqual({ 0: 1 / 3, 2: 1 / 3, 3: 1 / 3 });
    const a = s.parties.find(p => p.partyId === 'A')!;
    expect(a.meanSeats).toBeCloseTo(5 / 3, 12);
    expect(a.probAnySeat.p).toBeCloseTo(2 / 3, 12);
    expect(a.probQualified.p).toBe(1);
    expect(a.probQualifiedByLifeboatOnly.p).toBe(0);
    expect(a.seats).toEqual({ q05: 0, q10: 0, q25: 0, q50: 2, q75: 3, q90: 3, q95: 3 });
    expect(s.parliament).toMatchObject({ meanSize: 4, meanOverhang: 0 });
    expect(s.parliament.probAnyOverhang.p).toBe(0);
  });

  it('reports overhang probability and the lifeboat split', () => {
    const acc = new SeatSummaryAccumulator(config);
    // A is under 5% of votes but wins two electorates: lifeboat, and 2 seats against entitlement 0 or 1 -> overhang.
    const lifeboat = allocateDrawFromVotes(config, {
      electionId: 'synthetic', partyVotes: { A: 40, B: 960 },
      generalWinners: [{ electorateId: 'e1', partyId: 'A' }, { electorateId: 'e2', partyId: 'A' }], maoriWinners: [],
    });
    acc.add(lifeboat);
    acc.add(draw(700, 300));
    const s = acc.summarise();
    expect(lifeboat.overhangSeats).toBeGreaterThan(0);
    expect(s.parliament.probAnyOverhang.p).toBeCloseTo(0.5, 12);
    expect(s.parties[0].probQualifiedByLifeboatOnly.p).toBeCloseTo(0.5, 12);
    expect(s.parties[0].probOverhang.p).toBeCloseTo(0.5, 12);
    expect(s.parties[0].probQualifiedByPartyVote.p).toBeCloseTo(0.5, 12);
  });

  it('merges chunk summaries exactly and round-trips through JSON', () => {
    const outcomes = Array.from({ length: 200 }, (_, i) => allocateDraw(SYN, syntheticDraw('stage65-chunks', i), { uniform: () => 0.5 }));
    const whole = new SeatSummaryAccumulator(SYN);
    outcomes.forEach(o => whole.add(o));
    const first = new SeatSummaryAccumulator(SYN), second = new SeatSummaryAccumulator(SYN);
    outcomes.slice(0, 77).forEach(o => first.add(o));
    outcomes.slice(77).forEach(o => second.add(o));
    first.merge(JSON.parse(JSON.stringify(second.state)));
    expect(JSON.stringify(first.state)).toBe(JSON.stringify(whole.state));
    expect(JSON.stringify(first.summarise())).toBe(JSON.stringify(whole.summarise()));
    const restored = new SeatSummaryAccumulator(SYN, JSON.parse(JSON.stringify(whole.state)));
    expect(restored.summarise()).toEqual(whole.summarise());
    const s = whole.summarise();
    for (const p of s.parties) expect(Object.values(p.seatDistribution).reduce((x, y) => x + y, 0)).toBeCloseTo(1, 12);
    expect(Object.values(s.parliament.sizeDistribution).reduce((x, y) => x + y, 0)).toBeCloseTo(1, 12);
    expect(s.draws).toBe(200);
  });

  it('refuses to summarise nothing or to restore a mismatched state', () => {
    expect(() => new SeatSummaryAccumulator(config).summarise()).toThrow(/No draws/);
    const other = new SeatSummaryAccumulator(SYN).state;
    expect(() => new SeatSummaryAccumulator(config, other)).toThrow(/does not match/);
  });
});

describe('pipeline adapter (Stage53 MmpStage interface)', () => {
  const config: SeatLayerConfig = { ...SYN, expectedElectorateIds: { general: GENERAL, maori: MAORI } };
  const draw = syntheticDraw('stage65-adapter', 3);
  const inputs = { electionId: 'synthetic-election' } as PipelineInputs;

  it('returns a schema-valid allocation, deterministically, splitting Māori winners by electorate', () => {
    const stage = createSeatLayerMmpStage(config);
    expect(stage.rulesVersion).toBe(RULES.rulesVersion);
    const winners = [...draw.generalWinners, ...draw.maoriWinners].map(w => ({ electorateId: w.electorateId, partyId: w.partyId, candidateId: `c-${w.electorateId}` }));
    const a = stage.allocate(inputs, draw.partyVoteShares, winners);
    expect(MmpAllocationSchema.parse(a).electionId).toBe('synthetic-election');
    expect(stage.allocate(inputs, draw.partyVoteShares, winners)).toEqual(a);
    expect(a).toEqual(allocateDraw(config, draw, { uniform: () => 0.5 }).allocation);
  });
});
