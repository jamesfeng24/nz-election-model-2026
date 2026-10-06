// Exact MMP seat allocation under Electoral Act 1993 ss 191-193 (version as at 1 January 2026).
// DOM-free and serializable: plain-object input, plain-object output, no clock or randomness,
// so the same function can run in a module Web Worker. See docs/mmp-rules-verification.md.
import type { MmpAllocation } from '../../types/domain';

export const NOMINAL_SEATS = 120;
/** Threshold is inclusive: a party with exactly 5% of valid party votes qualifies (s 191(4)(a)). */
export const THRESHOLD_NUMERATOR = 1;
export const THRESHOLD_DENOMINATOR = 20;

export interface MmpPartyInput {
  /** A party listed on the party-vote part of the ballot paper. */
  partyId: string;
  /** Valid party votes received (s 179(1)(a)); a non-negative integer. */
  partyVotes: number;
  /** Constituency seats won by the party, including any component-party winners (ss 191(4)(b), 192(2)(b)). */
  constituencySeats: number;
  /** List candidates available after removing electorate winners (s 193(3)-(4)); omit for "never exhausted". */
  availableListCandidates?: number;
}

export interface MmpAllocationInput {
  electionId: string;
  rulesVersion: string;
  rulesSourceIds: string[];
  /** Normally 120. */
  nominalSeats?: number;
  parties: MmpPartyInput[];
  /** Electorate winners who are independents or belong to a party not on the party-vote list (s 191(8)). */
  independentElectorateSeats?: number;
}

export interface QuotientStep {
  step: number;
  partyId: string;
  /** Odd divisor used: 1, 3, 5, ... */
  divisor: number;
}

export interface AllocationAudit {
  seatsAllocatedBySainteLague: number;
  totalValidPartyVotes: number;
  steps: QuotientStep[];
  entitlements: Record<string, number>;
  overhangByParty: Record<string, number>;
}

export type AllocationResult =
  | { kind: 'allocated'; allocation: MmpAllocation; audit: AllocationAudit }
  /** The lowest selected quotient equals an unselected one; s 191(9) requires a lot, which this code never draws. */
  | { kind: 'tie-at-cutoff'; tiedPartyIds: string[]; seatsRemaining: number; steps: QuotientStep[] };

const isCount = (n: unknown): n is number => Number.isSafeInteger(n) && (n as number) >= 0;

function validate(input: MmpAllocationInput, nominal: number, independents: number): void {
  if (!Number.isSafeInteger(nominal) || nominal <= 0) throw new RangeError('nominalSeats must be a positive integer');
  if (!isCount(independents)) throw new RangeError('independentElectorateSeats must be a non-negative integer');
  const ids = new Set<string>();
  for (const p of input.parties) {
    if (!p.partyId || ids.has(p.partyId)) throw new RangeError(`Missing or duplicate partyId: ${p.partyId}`);
    ids.add(p.partyId);
    if (!isCount(p.partyVotes) || !isCount(p.constituencySeats))
      throw new RangeError(`Party ${p.partyId}: votes and constituency seats must be non-negative integers`);
    if (p.availableListCandidates !== undefined && !isCount(p.availableListCandidates))
      throw new RangeError(`Party ${p.partyId}: availableListCandidates must be a non-negative integer`);
    // Cross-multiplication of a vote total by the largest odd divisor must stay exact.
    if (p.partyVotes * (2 * nominal + 1) > Number.MAX_SAFE_INTEGER)
      throw new RangeError(`Party ${p.partyId}: vote total too large for exact comparison`);
  }
}

/** Compare a/b with c/d for positive integer b, d via cross-multiplication (exact within safe range). */
const compare = (a: number, b: number, c: number, d: number): number => {
  const left = a * d, right = c * b;
  return left === right ? 0 : left > right ? 1 : -1;
};

export function allocateSeats(input: MmpAllocationInput): AllocationResult {
  const nominal = input.nominalSeats ?? NOMINAL_SEATS;
  const independents = input.independentElectorateSeats ?? 0;
  validate(input, nominal, independents);

  const totalVotes = input.parties.reduce((sum, p) => sum + p.partyVotes, 0);
  if (!Number.isSafeInteger(totalVotes)) throw new RangeError('Total party votes not exactly representable');

  const qualification = new Map<string, string>();
  for (const p of input.parties) {
    const byVotes = p.partyVotes * THRESHOLD_DENOMINATOR >= totalVotes * THRESHOLD_NUMERATOR && totalVotes > 0;
    const bySeat = p.constituencySeats >= 1;
    qualification.set(p.partyId, byVotes && bySeat ? 'party-vote-threshold-and-electorate-seat'
      : byVotes ? 'party-vote-threshold' : bySeat ? 'electorate-seat' : 'not-qualified');
  }
  const qualified = input.parties.filter(p => qualification.get(p.partyId) !== 'not-qualified');

  const seatsToAllocate = nominal - independents;
  if (seatsToAllocate < 0) throw new RangeError('Independent electorate seats exceed nominal seats');
  if (qualified.length === 0 && seatsToAllocate > 0) throw new RangeError('No party qualifies for seats');

  const drawn = new Map(qualified.map(p => [p.partyId, 0]));
  const steps: QuotientStep[] = [];
  for (let step = 1; step <= seatsToAllocate; step++) {
    let best: MmpPartyInput[] = [];
    for (const p of qualified) {
      if (best.length === 0) { best = [p]; continue; }
      const c = compare(p.partyVotes, 2 * drawn.get(p.partyId)! + 1, best[0].partyVotes, 2 * drawn.get(best[0].partyId)! + 1);
      if (c > 0) best = [p]; else if (c === 0) best.push(p);
    }
    const remaining = seatsToAllocate - step + 1;
    if (best.length > remaining) return { kind: 'tie-at-cutoff', tiedPartyIds: best.map(p => p.partyId), seatsRemaining: remaining, steps };
    // Tied quotients in different columns are all inside the top N, so any order selects the same set.
    const chosen = best[0];
    steps.push({ step, partyId: chosen.partyId, divisor: 2 * drawn.get(chosen.partyId)! + 1 });
    drawn.set(chosen.partyId, drawn.get(chosen.partyId)! + 1);
  }

  let overhangSeats = 0, unfilledSeats = 0;
  const entitlements: Record<string, number> = {}, overhangByParty: Record<string, number> = {};
  const parties = input.parties.map(p => {
    const entitlement = drawn.get(p.partyId) ?? 0;
    const isQualified = qualification.get(p.partyId) !== 'not-qualified';
    const owed = Math.max(0, entitlement - p.constituencySeats); // s 192(2)-(5)
    const overhang = Math.max(0, p.constituencySeats - entitlement);
    const listSeats = Math.min(owed, p.availableListCandidates ?? owed); // s 193(4)
    entitlements[p.partyId] = entitlement;
    overhangByParty[p.partyId] = overhang;
    overhangSeats += overhang;
    unfilledSeats += owed - listSeats;
    return {
      partyId: p.partyId, qualified: isQualified, qualificationReason: qualification.get(p.partyId)!,
      electorateSeats: p.constituencySeats, listSeats, totalSeats: p.constituencySeats + listSeats,
    };
  });

  const allocation: MmpAllocation = {
    schemaVersion: 1, electionId: input.electionId, rulesVersion: input.rulesVersion,
    rulesSourceIds: input.rulesSourceIds, nominalSeats: nominal, parliamentSize: nominal + overhangSeats,
    overhangSeats, unfilledSeats, parties, independentElectorateSeats: independents,
  };
  return {
    kind: 'allocated', allocation,
    audit: { seatsAllocatedBySainteLague: seatsToAllocate, totalValidPartyVotes: totalVotes, steps, entitlements, overhangByParty },
  };
}
