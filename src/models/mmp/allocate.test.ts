// @vitest-environment node
import { describe, expect, it } from 'vitest';
import oracle from '../../../data/processed/mmp/oracle-seat-tables.json';
import { MmpAllocationSchema } from '../../types/domain';
import { allocateSeats, type MmpAllocationInput, type MmpPartyInput } from './allocate';

// Hand-worked and property fixtures are synthetic and labelled so; the oracle replay uses official results.
const base = { electionId: 'synthetic-test', rulesVersion: 'electoral-act-1993-2026-01-01', rulesSourceIds: ['test-rules'] };
const run = (parties: MmpPartyInput[], extra: Partial<MmpAllocationInput> = {}) => {
  const result = allocateSeats({ ...base, parties, ...extra });
  if (result.kind !== 'allocated') throw new Error('unexpected tie');
  MmpAllocationSchema.parse(result.allocation);
  return result;
};
const seats = (r: ReturnType<typeof run>, id: string) => r.allocation.parties.find(p => p.partyId === id)!;

describe('Sainte-Laguë allocation (synthetic, hand-worked)', () => {
  // 620/300/80 over 10 seats: top-10 quotients 620,300,206.7,124,100,88.6,80,68.9,60,56.4 → 6/3/1.
  const votes = [['A', 620], ['B', 300], ['C', 80]] as const;
  const parties = (c: [number, number, number]) => votes.map(([partyId, partyVotes], i) => ({ partyId, partyVotes, constituencySeats: c[i] }));

  it('allocates entitlements and list seats by exact quotients', () => {
    const r = run(parties([2, 0, 0]), { nominalSeats: 10 });
    expect(r.audit.entitlements).toEqual({ A: 6, B: 3, C: 1 });
    expect(seats(r, 'A')).toMatchObject({ electorateSeats: 2, listSeats: 4, totalSeats: 6 });
    expect(r.allocation.parliamentSize).toBe(10);
    expect(r.allocation.overhangSeats).toBe(0);
  });

  it('records the quotient order used', () => {
    const r = run(parties([0, 0, 0]), { nominalSeats: 10 });
    expect(r.audit.steps.slice(0, 4)).toEqual([
      { step: 1, partyId: 'A', divisor: 1 }, { step: 2, partyId: 'B', divisor: 1 },
      { step: 3, partyId: 'A', divisor: 3 }, { step: 4, partyId: 'A', divisor: 5 }]);
  });

  it('grows Parliament by the overhang and leaves other entitlements unchanged', () => {
    const r = run(parties([0, 0, 3]), { nominalSeats: 10 });
    expect(r.audit.entitlements).toEqual({ A: 6, B: 3, C: 1 });
    expect(seats(r, 'C')).toMatchObject({ electorateSeats: 3, listSeats: 0, totalSeats: 3 });
    expect(r.allocation).toMatchObject({ overhangSeats: 2, parliamentSize: 12, unfilledSeats: 0 });
    expect(seats(r, 'A').totalSeats).toBe(6);
  });

  it('gives equal electorate and entitlement seats zero list seats and no overhang (s 192(5))', () => {
    const r = run(parties([0, 0, 1]), { nominalSeats: 10 });
    expect(seats(r, 'C')).toMatchObject({ listSeats: 0, totalSeats: 1 });
    expect(r.allocation.overhangSeats).toBe(0);
  });

  it('is invariant to scaling every vote total', () => {
    const a = run(parties([1, 1, 0]), { nominalSeats: 10 });
    const scaled = run(parties([1, 1, 0]).map(p => ({ ...p, partyVotes: p.partyVotes * 7 })), { nominalSeats: 10 });
    expect(scaled.allocation.parties).toEqual(a.allocation.parties);
  });
});

describe('qualification (s 191(4))', () => {
  const three = (c: number, d: number) => [
    { partyId: 'A', partyVotes: 500, constituencySeats: 0 },
    { partyId: 'B', partyVotes: 1000 - 500 - c, constituencySeats: 0 },
    { partyId: 'C', partyVotes: c, constituencySeats: d }];
  it('qualifies exactly 5.00% and excludes 4.99%', () => {
    expect(seats(run(three(50, 0)), 'C')).toMatchObject({ qualified: true, qualificationReason: 'party-vote-threshold' });
    expect(seats(run(three(49, 0)), 'C')).toMatchObject({ qualified: false, qualificationReason: 'not-qualified', totalSeats: 0 });
  });
  it('lets one electorate win qualify a sub-5% party', () => {
    const r = run(three(30, 1));
    expect(seats(r, 'C')).toMatchObject({ qualified: true, qualificationReason: 'electorate-seat' });
    expect(seats(r, 'C').totalSeats).toBeGreaterThanOrEqual(1);
  });
  it('removes a non-qualifying party from the allocation, not from the vote total', () => {
    const r = run(three(49, 0));
    expect(r.audit.totalValidPartyVotes).toBe(1000);
    expect(r.audit.entitlements.C).toBe(0);
    expect(r.audit.steps.some(s => s.partyId === 'C')).toBe(false);
  });
  it('records both reasons when both routes apply', () => {
    expect(seats(run(three(100, 1)), 'C').qualificationReason).toBe('party-vote-threshold-and-electorate-seat');
  });
});

describe('independents, ties and list exhaustion', () => {
  const two = [{ partyId: 'A', partyVotes: 600, constituencySeats: 0 }, { partyId: 'B', partyVotes: 400, constituencySeats: 0 }];
  it('takes independent electorate seats out of the 120 (s 191(8)) without growing Parliament', () => {
    const r = run(two, { nominalSeats: 10, independentElectorateSeats: 1 });
    expect(r.audit.seatsAllocatedBySainteLague).toBe(9);
    expect(r.allocation).toMatchObject({ independentElectorateSeats: 1, parliamentSize: 10, overhangSeats: 0, unfilledSeats: 0 });
    expect(r.allocation.parties.reduce((s, p) => s + p.totalSeats, 1)).toBe(10);
  });
  it('flags an exact tie at the cut-off instead of choosing (s 191(9))', () => {
    const tied = [{ partyId: 'A', partyVotes: 100, constituencySeats: 0 }, { partyId: 'B', partyVotes: 100, constituencySeats: 0 }];
    expect(allocateSeats({ ...base, parties: tied, nominalSeats: 2 }).kind).toBe('allocated');
    expect(allocateSeats({ ...base, parties: tied, nominalSeats: 3 })).toMatchObject({ kind: 'tie-at-cutoff', tiedPartyIds: ['A', 'B'], seatsRemaining: 1 });
  });
  it('leaves seats unfilled when a list is exhausted (s 193(4))', () => {
    const r = run([{ ...two[0], availableListCandidates: 2 }, two[1]], { nominalSeats: 10 });
    expect(seats(r, 'A').listSeats).toBe(2);
    expect(r.allocation).toMatchObject({ unfilledSeats: 4, parliamentSize: 10 });
  });
});

describe('input validation and serialization', () => {
  it.each([
    [{ partyId: 'A', partyVotes: -1, constituencySeats: 0 }],
    [{ partyId: 'A', partyVotes: 1.5, constituencySeats: 0 }],
    [{ partyId: 'A', partyVotes: 10, constituencySeats: -1 }],
    [{ partyId: 'A', partyVotes: 2 ** 52, constituencySeats: 0 }],
  ])('rejects invalid party %#', party => {
    expect(() => allocateSeats({ ...base, parties: [party] })).toThrow(RangeError);
  });
  it('rejects duplicate parties, no qualifying party and excess independents', () => {
    const p = { partyId: 'A', partyVotes: 10, constituencySeats: 0 };
    expect(() => allocateSeats({ ...base, parties: [p, p] })).toThrow(RangeError);
    expect(() => allocateSeats({ ...base, parties: [] })).toThrow(RangeError);
    expect(() => allocateSeats({ ...base, parties: [p], nominalSeats: 2, independentElectorateSeats: 3 })).toThrow(RangeError);
  });
  it('round-trips through JSON (Web Worker message safe) and is deterministic', () => {
    const input: MmpAllocationInput = { ...base, nominalSeats: 10, parties: [
      { partyId: 'A', partyVotes: 620, constituencySeats: 1 }, { partyId: 'B', partyVotes: 380, constituencySeats: 0 }] };
    const once = allocateSeats(JSON.parse(JSON.stringify(input)));
    expect(JSON.parse(JSON.stringify(once))).toEqual(once);
    expect(allocateSeats(input)).toEqual(once);
  });
});

describe('seat accounting properties (seeded synthetic inputs)', () => {
  it('always reconciles with the domain schema', () => {
    let state = 12345;
    const next = (n: number) => { state = (state * 1103515245 + 12345) % 2147483648; return state % n; };
    for (let trial = 0; trial < 300; trial++) {
      const k = 2 + next(5);
      const parties = Array.from({ length: k }, (_, i) => ({
        partyId: `P${i}`, partyVotes: 1 + next(1_000_000), constituencySeats: next(4) === 0 ? next(6) : 0 }));
      const independents = next(3) === 0 ? next(3) : 0;
      const result = allocateSeats({ ...base, parties, independentElectorateSeats: independents });
      if (result.kind === 'tie-at-cutoff') continue;
      MmpAllocationSchema.parse(result.allocation);
      const entitled = Object.values(result.audit.entitlements).reduce((a, b) => a + b, 0);
      expect(entitled).toBe(120 - independents);
      expect(result.allocation.parliamentSize).toBe(120 + result.allocation.overhangSeats);
    }
  });
});

describe('replay of official 2008–2023 seat tables', () => {
  for (const election of oracle.elections) {
    it(`reproduces ${election.year} exactly`, () => {
      const parties = election.listedParties.map(p => ({ partyId: p.partyName, partyVotes: p.partyVotes, constituencySeats: p.constituencySeats }));
      const r = run(parties, { electionId: `nz-${election.year}`, independentElectorateSeats: election.constituencySeatsOutsidePartyBallot });
      for (const official of election.listedParties)
        expect(seats(r, official.partyName).listSeats, official.partyName).toBe(official.officialListSeats);
      expect(r.allocation.parliamentSize).toBe(election.officialParliamentSize);
      expect(r.allocation.unfilledSeats).toBe(0);
    });
  }
  it('captures the known overhang cases', () => {
    const overhang = Object.fromEntries(oracle.elections.map(e => [e.year, e.officialParliamentSize - 120]));
    expect(overhang).toEqual({ 2008: 2, 2011: 1, 2014: 1, 2017: 0, 2020: 0, 2023: 2 });
  });
});
