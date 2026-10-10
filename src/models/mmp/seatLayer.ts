// Per-draw MMP seat layer: simulated party-vote shares plus electorate winners in, Parliament outcomes and
// summaries out, using the Stage49 allocator unchanged. DOM-free, plain-object input and output, so it runs in
// a module Web Worker and chunk summaries merge exactly. See docs/stage65-seat-layer-design.md.
import type { MmpAllocation } from '../../types/domain';
import { allocateSeats, NOMINAL_SEATS, THRESHOLD_DENOMINATOR, type MmpPartyInput } from './allocate';

export interface BlocDefinition {
  id: string;
  label: string;
  /** Listed parties whose total seats are summed. The 2026 choices belong to the project owner, not to code. */
  partyIds: string[];
}

export interface SeatLayerConfig {
  rulesVersion: string;
  rulesSourceIds: string[];
  /** Normally 120. */
  nominalSeats?: number;
  /** Parties on the party-vote ballot. */
  listedPartyIds: string[];
  /** Aggregate vote buckets (for example "other"): counted in the valid-vote total, never qualified, never seated. */
  unlistedBucketIds?: string[];
  /**
   * Registered parties on the party-list ballot whose party votes are simulated inside a bucket (audit J3, James 2026-10-10). An electorate
   * winner of one of them is that party's seat, not an independent's: the party qualifies by the electorate (s 191(4)(b)) with zero party
   * votes of its own, earns no Sainte-Laguë seat and its seats are overhang (s 192(5)). Approximation: its real votes stay in the bucket, so
   * a vote large enough to earn one list seat (about 0.4%) is not modelled. Winners of any other unlisted party, or none, stay s 191(8).
   */
  zeroVotePartyIds?: string[];
  /** Integer vote total that shares are converted to (default 10^9; continuous for practical purposes). */
  voteScale?: number;
  /** When given, every draw must name exactly one winner for each of these electorates (missing is never zero). */
  expectedElectorateIds?: { general: string[]; maori: string[] };
  blocs: BlocDefinition[];
}

export interface ElectorateWinnerInput { electorateId: string; partyId: string | null; candidateId?: string }

interface SeatLayerDrawBase {
  electionId: string;
  /** General-roll electorate winners. */
  generalWinners: ElectorateWinnerInput[];
  /** Māori electorate winners, a separate input because the Māori seats are modelled separately. */
  maoriWinners: ElectorateWinnerInput[];
}
export interface SeatLayerDraw extends SeatLayerDrawBase {
  /** Valid party-vote shares over listed parties and buckets; must sum to 1 within 1e-6. */
  partyVoteShares: Record<string, number>;
}
export interface SeatLayerVotesDraw extends SeatLayerDrawBase {
  /** Integer valid party votes over listed parties (and buckets, if any). */
  partyVotes: Record<string, number>;
}

export interface PartySeatOutcome {
  electorateSeats: number;
  listSeats: number;
  totalSeats: number;
  entitlement: number;
  overhang: number;
  qualified: boolean;
  qualifiedByPartyVote: boolean;
  qualifiedByElectorate: boolean;
}
export interface SeatDrawOutcome {
  nominalSeats: number;
  parliamentSize: number;
  overhangSeats: number;
  unfilledSeats: number;
  independentElectorateSeats: number;
  /** Lots drawn under s 191(9) for this draw (almost always 0). */
  lotsDrawn: number;
  parties: Record<string, PartySeatOutcome>;
  allocation: MmpAllocation;
}

export class TieAtCutoffError extends Error {
  constructor(public readonly tiedPartyIds: string[]) {
    super(`Exact tie at the Sainte-Laguë cut-off among ${tiedPartyIds.join(', ')}; a lot (s 191(9)) is required and no stream was supplied`);
  }
}

export const DEFAULT_VOTE_SCALE = 1_000_000_000;
const SHARE_SUM_TOLERANCE = 1e-6;

const unique = (xs: string[]) => new Set(xs).size === xs.length;

export function validateSeatLayerConfig(config: SeatLayerConfig): void {
  const buckets = config.unlistedBucketIds ?? [];
  if (config.listedPartyIds.length === 0 || !unique(config.listedPartyIds) || config.listedPartyIds.some(p => !p))
    throw new RangeError('listedPartyIds must be non-empty, unique and non-blank');
  if (!unique(buckets) || buckets.some(b => !b || config.listedPartyIds.includes(b)))
    throw new RangeError('unlistedBucketIds must be unique, non-blank and disjoint from listedPartyIds');
  const zero = config.zeroVotePartyIds ?? [];
  if (!unique(zero) || zero.some(z => !z || config.listedPartyIds.includes(z) || buckets.includes(z) || z.includes('#')))
    throw new RangeError('zeroVotePartyIds must be unique, non-blank and disjoint from listedPartyIds and unlistedBucketIds');
  const nominal = config.nominalSeats ?? NOMINAL_SEATS;
  if (!Number.isSafeInteger(nominal) || nominal <= 0) throw new RangeError('nominalSeats must be a positive integer');
  const scale = config.voteScale ?? DEFAULT_VOTE_SCALE;
  // Largest odd divisor times the largest vote must stay exact inside the allocator.
  if (!Number.isSafeInteger(scale) || scale <= 0 || scale * (2 * nominal + 1) > Number.MAX_SAFE_INTEGER)
    throw new RangeError('voteScale must be a positive integer small enough for exact comparison');
  if (!unique(config.blocs.map(b => b.id))) throw new RangeError('Duplicate bloc id');
  for (const b of config.blocs) {
    if (!b.id || b.partyIds.length === 0 || !unique(b.partyIds) || b.partyIds.some(p => !config.listedPartyIds.includes(p)))
      throw new RangeError(`Bloc ${b.id}: partyIds must be non-empty, unique and listed`);
  }
  const e = config.expectedElectorateIds;
  if (e && (!unique([...e.general, ...e.maori]))) throw new RangeError('expectedElectorateIds must be unique across general and maori');
}

/** Largest-remainder conversion of non-negative shares summing to 1 into integer votes summing to `scale`. */
export function sharesToVotes(shares: Record<string, number>, scale: number): Record<string, number> {
  const ids = Object.keys(shares);
  let total = 0;
  for (const id of ids) {
    const s = shares[id];
    if (!Number.isFinite(s) || s < 0) throw new RangeError(`Share for ${id} must be a finite non-negative number`);
    total += s;
  }
  if (Math.abs(total - 1) > SHARE_SUM_TOLERANCE) throw new RangeError(`Party-vote shares sum to ${total}, not 1`);
  const exact = ids.map(id => (shares[id] / total) * scale);
  const votes = exact.map(Math.floor);
  let left = scale - votes.reduce((a, b) => a + b, 0);
  const order = ids.map((_, i) => i).sort((a, b) => (exact[b] - votes[b]) - (exact[a] - votes[a]) || a - b);
  for (let k = 0; left > 0; k = (k + 1) % ids.length, left--) votes[order[k]] += 1;
  return Object.fromEntries(ids.map((id, i) => [id, votes[i]]));
}

function splitBucket(id: string, votes: number, total: number): MmpPartyInput[] {
  if (votes === 0) return [];
  // Pieces strictly below 5% of the total can never qualify, yet still count in the valid-vote total.
  let k = Math.floor((THRESHOLD_DENOMINATOR * votes) / total) + 1;
  const piece = (n: number) => Math.ceil(votes / n);
  while (THRESHOLD_DENOMINATOR * piece(k) >= total) {
    k++;
    if (k > votes) throw new RangeError(`Bucket ${id} cannot be kept below the threshold at total ${total}`);
  }
  const base = Math.floor(votes / k), extra = votes - base * k;
  return Array.from({ length: k }, (_, i) => ({ partyId: `${id}#${i + 1}`, partyVotes: base + (i < extra ? 1 : 0), constituencySeats: 0 }));
}

function checkWinners(config: SeatLayerConfig, draw: SeatLayerDrawBase): void {
  const seen = new Set<string>();
  for (const w of [...draw.generalWinners, ...draw.maoriWinners]) {
    if (!w.electorateId) throw new RangeError('Winner without electorateId');
    if (seen.has(w.electorateId)) throw new RangeError(`Electorate ${w.electorateId} has more than one winner or appears in both general and Māori inputs`);
    seen.add(w.electorateId);
  }
  const e = config.expectedElectorateIds;
  if (!e) return;
  const check = (kind: string, expected: string[], got: ElectorateWinnerInput[]) => {
    const want = new Set(expected), have = new Set(got.map(w => w.electorateId));
    const missing = expected.filter(id => !have.has(id)), extra = [...have].filter(id => !want.has(id));
    if (missing.length || extra.length)
      throw new RangeError(`${kind} winners must cover exactly the expected electorates (missing: ${missing.join(', ') || 'none'}; unexpected: ${extra.join(', ') || 'none'})`);
  };
  check('General', e.general, draw.generalWinners);
  check('Māori', e.maori, draw.maoriWinners);
}

/** Allocate one draw from integer party votes; the Stage49 allocator is called unchanged. */
export function allocateDrawFromVotes(
  config: SeatLayerConfig, draw: SeatLayerVotesDraw, options: { uniform?: () => number } = {},
): SeatDrawOutcome {
  validateSeatLayerConfig(config);
  checkWinners(config, draw);
  const buckets = config.unlistedBucketIds ?? [];
  const expected = new Set([...config.listedPartyIds, ...buckets]);
  for (const id of Object.keys(draw.partyVotes)) if (!expected.has(id)) throw new RangeError(`Unknown party or bucket in party votes: ${id}`);
  for (const id of expected) {
    const v = draw.partyVotes[id];
    if (v === undefined) throw new RangeError(`Party votes missing for ${id}`);
    if (!Number.isSafeInteger(v) || v < 0) throw new RangeError(`Party votes for ${id} must be a non-negative integer`);
  }
  const nominal = config.nominalSeats ?? NOMINAL_SEATS;

  const seats = new Map<string, number>(config.listedPartyIds.map(p => [p, 0]));
  const zeroVote = new Map<string, number>((config.zeroVotePartyIds ?? []).map(p => [p, 0]));
  let independents = 0;
  for (const w of [...draw.generalWinners, ...draw.maoriWinners]) {
    if (w.partyId !== null && seats.has(w.partyId)) seats.set(w.partyId, seats.get(w.partyId)! + 1);
    else if (w.partyId !== null && zeroVote.has(w.partyId)) zeroVote.set(w.partyId, zeroVote.get(w.partyId)! + 1);
    else independents++; // independent or a party not on the party-list ballot (s 191(8))
  }
  const total = [...expected].reduce((s, id) => s + draw.partyVotes[id], 0);
  if (!Number.isSafeInteger(total) || total <= 0) throw new RangeError('Total party votes must be a positive safe integer');

  const listed: MmpPartyInput[] = config.listedPartyIds.map(partyId => ({
    partyId, partyVotes: draw.partyVotes[partyId], constituencySeats: seats.get(partyId)!,
  }));
  // A bucketed list party enters the allocation only in a draw where it holds an electorate seat (audit J3).
  const zeroVoteParties: MmpPartyInput[] = [...zeroVote].filter(([, n]) => n > 0).map(([partyId, n]) => ({ partyId, partyVotes: 0, constituencySeats: n }));
  const bucketPieces = buckets.flatMap(b => splitBucket(b, draw.partyVotes[b], total));

  let lots = 0;
  const bumped = new Map<string, number>();
  for (;;) {
    const parties = [...listed.map(p => ({ ...p, partyVotes: p.partyVotes + (bumped.get(p.partyId) ?? 0) })), ...zeroVoteParties, ...bucketPieces];
    const result = allocateSeats({
      electionId: draw.electionId, rulesVersion: config.rulesVersion, rulesSourceIds: config.rulesSourceIds,
      nominalSeats: nominal, parties, independentElectorateSeats: independents,
    });
    if (result.kind === 'tie-at-cutoff') {
      if (!options.uniform) throw new TieAtCutoffError(result.tiedPartyIds);
      // The lot chooses one tied party for a remaining seat; one extra vote makes that choice strict.
      const pick = result.tiedPartyIds[Math.min(result.tiedPartyIds.length - 1, Math.floor(options.uniform() * result.tiedPartyIds.length))];
      bumped.set(pick, (bumped.get(pick) ?? 0) + 1);
      if (++lots > config.listedPartyIds.length + 1) throw new RangeError('Tie resolution did not converge');
      continue;
    }
    const byId = new Map(result.allocation.parties.map(p => [p.partyId, p]));
    for (const piece of bucketPieces)
      if (byId.get(piece.partyId)!.qualified) throw new RangeError(`Bucket piece ${piece.partyId} unexpectedly qualified`);
    const outcomes: Record<string, PartySeatOutcome> = {};
    const kept = result.allocation.parties.filter(p => config.listedPartyIds.includes(p.partyId) || zeroVote.has(p.partyId));
    for (const p of kept) {
      outcomes[p.partyId] = {
        electorateSeats: p.electorateSeats, listSeats: p.listSeats, totalSeats: p.totalSeats,
        entitlement: result.audit.entitlements[p.partyId], overhang: result.audit.overhangByParty[p.partyId],
        qualified: p.qualified,
        qualifiedByPartyVote: p.qualificationReason.includes('party-vote-threshold'),
        qualifiedByElectorate: p.qualificationReason.includes('electorate-seat'),
      };
    }
    const allocation: MmpAllocation = { ...result.allocation, parties: kept };
    return {
      nominalSeats: nominal, parliamentSize: allocation.parliamentSize, overhangSeats: allocation.overhangSeats,
      unfilledSeats: allocation.unfilledSeats, independentElectorateSeats: independents, lotsDrawn: lots, parties: outcomes, allocation,
    };
  }
}

/** Allocate one simulated draw from party-vote shares. */
export function allocateDraw(config: SeatLayerConfig, draw: SeatLayerDraw, options: { uniform?: () => number } = {}): SeatDrawOutcome {
  validateSeatLayerConfig(config);
  const { partyVoteShares, ...rest } = draw;
  const expected = new Set([...config.listedPartyIds, ...(config.unlistedBucketIds ?? [])]);
  for (const id of Object.keys(partyVoteShares)) if (!expected.has(id)) throw new RangeError(`Unknown party or bucket in shares: ${id}`);
  for (const id of expected) if (!(id in partyVoteShares)) throw new RangeError(`Share missing for ${id}; a missing share is never treated as zero`);
  return allocateDrawFromVotes(config, { ...rest, partyVotes: sharesToVotes(partyVoteShares, config.voteScale ?? DEFAULT_VOTE_SCALE) }, options);
}

// ---------------------------------------------------------------------------------------------------------
// Summaries

export interface PartyTally {
  seatHist: Record<string, number>;
  anySeat: number;
  qualified: number;
  qualifiedByPartyVote: number;
  /** Qualified through an electorate win while under 5% of party votes (the lifeboat). */
  qualifiedByLifeboatOnly: number;
  overhangDraws: number;
  sumElectorate: number;
  sumList: number;
}
export interface BlocTally { seatHist: Record<string, number>; majority: number; exactHalf: number }
export interface SeatSummaryState {
  schemaVersion: 1;
  draws: number;
  lotsDrawn: number;
  parties: Record<string, PartyTally>;
  blocs: Record<string, BlocTally>;
  overhangHist: Record<string, number>;
  sizeHist: Record<string, number>;
}

export interface Probability { p: number; mcse: number }
export interface SeatQuantiles { q05: number; q10: number; q25: number; q50: number; q75: number; q90: number; q95: number }
export interface PartySeatSummary {
  partyId: string;
  meanSeats: number;
  meanElectorateSeats: number;
  meanListSeats: number;
  seats: SeatQuantiles;
  seatDistribution: Record<string, number>;
  probAnySeat: Probability;
  probQualified: Probability;
  probQualifiedByPartyVote: Probability;
  probQualifiedByLifeboatOnly: Probability;
  probOverhang: Probability;
}
export interface BlocSummary {
  id: string;
  label: string;
  partyIds: string[];
  meanSeats: number;
  seats: SeatQuantiles;
  seatDistribution: Record<string, number>;
  /** Strictly more than half of that draw's Parliament. */
  probMajority: Probability;
  /** Exactly half of that draw's Parliament (neither side has a majority). */
  probExactHalf: Probability;
}
export interface SeatLayerSummary {
  schemaVersion: 1;
  draws: number;
  lotsDrawn: number;
  parties: PartySeatSummary[];
  blocs: BlocSummary[];
  parliament: {
    meanSize: number;
    sizeDistribution: Record<string, number>;
    overhangDistribution: Record<string, number>;
    probAnyOverhang: Probability;
    meanOverhang: number;
  };
}

const bump = (hist: Record<string, number>, v: number) => { hist[String(v)] = (hist[String(v)] ?? 0) + 1; };
const addHist = (into: Record<string, number>, from: Record<string, number>) => { for (const [k, n] of Object.entries(from)) into[k] = (into[k] ?? 0) + n; };
const sortedHist = (h: Record<string, number>) => Object.fromEntries(Object.entries(h).sort(([a], [b]) => Number(a) - Number(b)));
const histMean = (h: Record<string, number>, n: number) => Object.entries(h).reduce((s, [k, c]) => s + Number(k) * c, 0) / n;
function histQuantile(h: Record<string, number>, n: number, q: number): number {
  // Smallest value whose cumulative frequency reaches q of the draws.
  let cum = 0;
  const entries = Object.entries(h).map(([k, c]) => [Number(k), c] as const).sort((a, b) => a[0] - b[0]);
  for (const [v, c] of entries) { cum += c; if (cum >= q * n - 1e-9) return v; }
  return entries[entries.length - 1][0];
}
const quantiles = (h: Record<string, number>, n: number): SeatQuantiles => ({
  q05: histQuantile(h, n, 0.05), q10: histQuantile(h, n, 0.1), q25: histQuantile(h, n, 0.25), q50: histQuantile(h, n, 0.5),
  q75: histQuantile(h, n, 0.75), q90: histQuantile(h, n, 0.9), q95: histQuantile(h, n, 0.95),
});
const prob = (count: number, n: number): Probability => { const p = count / n; return { p, mcse: Math.sqrt((p * (1 - p)) / n) }; };
const distribution = (h: Record<string, number>, n: number) => Object.fromEntries(Object.entries(sortedHist(h)).map(([k, c]) => [k, c / n]));

export class SeatSummaryAccumulator {
  readonly state: SeatSummaryState;
  constructor(private readonly config: SeatLayerConfig, state?: SeatSummaryState) {
    validateSeatLayerConfig(config);
    this.state = state ?? {
      schemaVersion: 1, draws: 0, lotsDrawn: 0, overhangHist: {}, sizeHist: {},
      parties: Object.fromEntries(config.listedPartyIds.map(p => [p, {
        seatHist: {}, anySeat: 0, qualified: 0, qualifiedByPartyVote: 0, qualifiedByLifeboatOnly: 0, overhangDraws: 0, sumElectorate: 0, sumList: 0,
      }])),
      blocs: Object.fromEntries(config.blocs.map(b => [b.id, { seatHist: {}, majority: 0, exactHalf: 0 }])),
    };
    if (state && (state.schemaVersion !== 1 ||
        config.listedPartyIds.some(p => !(p in state.parties)) || config.blocs.some(b => !(b.id in state.blocs))))
      throw new RangeError('Summary state does not match the configuration');
  }

  add(outcome: SeatDrawOutcome): void {
    const s = this.state;
    s.draws++;
    s.lotsDrawn += outcome.lotsDrawn;
    bump(s.overhangHist, outcome.overhangSeats);
    bump(s.sizeHist, outcome.parliamentSize);
    for (const id of this.config.listedPartyIds) {
      const o = outcome.parties[id], t = s.parties[id];
      bump(t.seatHist, o.totalSeats);
      if (o.totalSeats > 0) t.anySeat++;
      if (o.qualified) t.qualified++;
      if (o.qualifiedByPartyVote) t.qualifiedByPartyVote++;
      if (o.qualified && !o.qualifiedByPartyVote) t.qualifiedByLifeboatOnly++;
      if (o.overhang > 0) t.overhangDraws++;
      t.sumElectorate += o.electorateSeats;
      t.sumList += o.listSeats;
    }
    for (const b of this.config.blocs) {
      const seats = b.partyIds.reduce((sum, p) => sum + outcome.parties[p].totalSeats, 0);
      const t = s.blocs[b.id];
      bump(t.seatHist, seats);
      if (2 * seats > outcome.parliamentSize) t.majority++;
      else if (2 * seats === outcome.parliamentSize) t.exactHalf++;
    }
  }

  /** Exact merge of another accumulator's counts (all quantities are integer counts). */
  merge(other: SeatSummaryState): void {
    const s = this.state;
    s.draws += other.draws;
    s.lotsDrawn += other.lotsDrawn;
    addHist(s.overhangHist, other.overhangHist);
    addHist(s.sizeHist, other.sizeHist);
    for (const id of this.config.listedPartyIds) {
      const t = s.parties[id], o = other.parties[id];
      if (!o) throw new RangeError(`Merged state lacks party ${id}`);
      addHist(t.seatHist, o.seatHist);
      t.anySeat += o.anySeat; t.qualified += o.qualified; t.qualifiedByPartyVote += o.qualifiedByPartyVote;
      t.qualifiedByLifeboatOnly += o.qualifiedByLifeboatOnly; t.overhangDraws += o.overhangDraws;
      t.sumElectorate += o.sumElectorate; t.sumList += o.sumList;
    }
    for (const b of this.config.blocs) {
      const t = s.blocs[b.id], o = other.blocs[b.id];
      if (!o) throw new RangeError(`Merged state lacks bloc ${b.id}`);
      addHist(t.seatHist, o.seatHist);
      t.majority += o.majority; t.exactHalf += o.exactHalf;
    }
  }

  summarise(): SeatLayerSummary {
    const s = this.state, n = s.draws;
    if (n === 0) throw new RangeError('No draws accumulated');
    return {
      schemaVersion: 1, draws: n, lotsDrawn: s.lotsDrawn,
      parties: this.config.listedPartyIds.map(partyId => {
        const t = s.parties[partyId];
        return {
          partyId, meanSeats: histMean(t.seatHist, n), meanElectorateSeats: t.sumElectorate / n, meanListSeats: t.sumList / n,
          seats: quantiles(t.seatHist, n), seatDistribution: distribution(t.seatHist, n),
          probAnySeat: prob(t.anySeat, n), probQualified: prob(t.qualified, n), probQualifiedByPartyVote: prob(t.qualifiedByPartyVote, n),
          probQualifiedByLifeboatOnly: prob(t.qualifiedByLifeboatOnly, n), probOverhang: prob(t.overhangDraws, n),
        };
      }),
      blocs: this.config.blocs.map(b => {
        const t = s.blocs[b.id];
        return {
          id: b.id, label: b.label, partyIds: [...b.partyIds], meanSeats: histMean(t.seatHist, n), seats: quantiles(t.seatHist, n),
          seatDistribution: distribution(t.seatHist, n), probMajority: prob(t.majority, n), probExactHalf: prob(t.exactHalf, n),
        };
      }),
      parliament: {
        meanSize: histMean(s.sizeHist, n), sizeDistribution: distribution(s.sizeHist, n), overhangDistribution: distribution(s.overhangHist, n),
        probAnyOverhang: prob(n - (s.overhangHist['0'] ?? 0), n), meanOverhang: histMean(s.overhangHist, n),
      },
    };
  }
}
