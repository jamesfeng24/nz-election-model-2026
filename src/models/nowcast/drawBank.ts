import { z } from 'zod';
import { SeatEvidenceSchema } from '../../types/export';

/**
 * Stage73/74 draw bank (Python `scripts/nowcast_assembly`, schema 2): one row per simulated election. Row i carries
 * national draw i's party vote and, for every simulated seat, that row's winner. Seats without inputs are explicit
 * `unavailable` records with a reason, never zeros. Validated before any use; a malformed bank throws.
 */
const id = z.string().trim().min(1);
const level = z.union([z.literal(0.5), z.literal(0.8), z.literal(0.9)]);

const ShareSummarySchema = z.object({
  candidateId: id,
  mean: z.number().finite(),
  intervals: z.array(z.object({ level, lower: z.number().finite(), median: z.number().finite(), upper: z.number().finite() }).strict()).length(3),
}).strict();

/** Stage79: the seat-poll update applied to a general seat's National/Labour balance (absent when no poll was used). */
const SeatPoll = z.object({
  pollIds: z.array(id).min(1),
  pollValue: z.number().finite(), pollVariance: z.number().finite().positive(),
  ageWeeks: z.number().finite().nonnegative(), rho: z.number().finite().min(0).max(1), weight: z.number().finite().min(0).max(1),
  modelCentre: z.number().finite(), modelSD: z.number().finite().positive(),
  shift: z.number().finite(), posteriorSD: z.number().finite().positive(), sharedSD: z.number().finite().positive(),
}).strict();

const Simulated = z.object({
  electorateId: id, scope: z.enum(['general', 'maori']), status: z.literal('simulated'),
  class: z.enum(['ordinary', 'exceptional', 'maori-layer']),
  multiplier: z.number().positive().optional(),
  withinMultiplier: z.number().positive().optional(),
  massMultiplier: z.number().positive().optional(),
  source: id.optional(),
  pollFieldworkEnd: z.iso.date().optional(),
  seatPoll: SeatPoll.optional(),
  candidates: z.array(id).min(2),
  candidateNames: z.array(id).optional(),
  candidateParty: z.array(id.nullable()),
  candidateShares: z.array(ShareSummarySchema),
  /** Per row, the index of the winning candidate in `candidates`. */
  winners: z.array(z.number().int().nonnegative()),
  /** Polled Māori seats only: per row, the winner under Stage71's variance-inflation arm P, the other end of the labelled range (D127). */
  inflationWinners: z.array(z.number().int().nonnegative()).optional(),
}).strict();
const Unavailable = z.object({ electorateId: id, scope: z.enum(['general', 'maori']), status: z.literal('unavailable'), reason: id }).strict();

export const DrawBankSchema = z.object({
  schemaVersion: z.literal(3),
  stage: z.number().int(),
  electionYear: z.number().int(),
  provenance: z.enum(['live', 'synthetic-fixture']),
  configVersion: id,
  estimand: z.literal('nowcast'),
  modelStateAsOf: z.iso.date(),
  dataCutoff: z.iso.date(),
  nationalStateKey: z.literal('lastDataSupport'),
  inputs: z.record(z.string(), z.string()),
  /** Rows: national draws times layer replicates; row r uses national draw floor(r / layerReplicates). */
  draws: z.number().int().positive(),
  nationalDraws: z.number().int().positive(),
  layerReplicates: z.number().int().positive(),
  /** One id per national draw. */
  drawIds: z.array(id),
  /** `ballotPartyIds`: every registered party with a 2026 party list; one simulated inside the other bucket is seated as a zero-vote party (audit J3). */
  partyVote: z.object({
    groups: z.array(id).min(2), otherBucket: id, ballotPartyIds: z.array(id).min(1),
    shares: z.array(z.array(z.number().finite().nonnegative())),
  }).strict(),
  seats: z.array(z.discriminatedUnion('status', [Simulated, Unavailable])),
  /** Stage85: optional per-seat evidence (display data, not part of the simulated content). */
  seatEvidence: z.array(SeatEvidenceSchema).optional(),
  directory: z.object({
    parties: z.array(z.object({ partyId: id, name: id, abbreviation: id }).strict()),
    electorates: z.array(z.object({ electorateId: id, name: id, kind: z.enum(['general', 'maori']) }).strict()),
    candidates: z.array(z.object({ candidateId: id, name: id, electorateId: id, partyId: id.nullable(), partyLabel: id.nullable() }).strict()),
  }).strict(),
  diagnostics: z.record(z.string(), z.unknown()),
  label: id.optional(),
}).strict().superRefine((bank, ctx) => {
  const bad = (message: string, path: (string | number)[] = []) => ctx.addIssue({ code: 'custom', message, path });
  const n = bank.draws;
  const m = bank.nationalDraws;
  if (n !== m * bank.layerReplicates) bad('Rows must be national draws times layer replicates', ['draws']);
  if (bank.drawIds.length !== m || new Set(bank.drawIds).size !== m) bad('Every national draw needs one distinct id', ['drawIds']);
  if (bank.partyVote.shares.length !== m) bad('Every national draw needs one party vote', ['partyVote', 'shares']);
  if (!bank.partyVote.groups.includes(bank.partyVote.otherBucket)) bad('The other bucket must be a national group', ['partyVote']);
  const ballot = bank.partyVote.ballotPartyIds;
  if (new Set(ballot).size !== ballot.length || ballot.includes(bank.partyVote.otherBucket)
      || bank.partyVote.groups.some(g => g !== bank.partyVote.otherBucket && !ballot.includes(g)))
    bad('ballotPartyIds must be unique, exclude the other bucket and include every party group', ['partyVote', 'ballotPartyIds']);
  bank.partyVote.shares.forEach((row, i) => {
    if (row.length !== bank.partyVote.groups.length || Math.abs(row.reduce((a, b) => a + b, 0) - 1) > 1e-9)
      bad('Party vote row must be a simplex over the national groups', ['partyVote', 'shares', i]);
  });
  const ids = bank.seats.map(s => s.electorateId);
  if (new Set(ids).size !== ids.length) bad('Duplicate electorate', ['seats']);
  if (bank.seatEvidence) {
    const simulated = new Set(bank.seats.filter(s => s.status === 'simulated').map(s => s.electorateId));
    const evidenced = bank.seatEvidence.map(e => e.electorateId);
    if (new Set(evidenced).size !== evidenced.length || evidenced.length !== simulated.size || evidenced.some(e => !simulated.has(e)))
      bad('Seat evidence must cover exactly the simulated seats, once each', ['seatEvidence']);
    bank.seatEvidence.forEach((e, i) => {
      const seat = bank.seats.find(s => s.electorateId === e.electorateId);
      if (seat && seat.status === 'simulated' && seat.class !== e.uncertaintyClass) bad('Seat evidence class differs from the seat', ['seatEvidence', i]);
    });
  }
  bank.seats.forEach((s, i) => {
    if (s.status !== 'simulated') return;
    if (s.winners.length !== n) bad('Every row needs one winner', ['seats', i]);
    if (s.candidateParty.length !== s.candidates.length || s.candidateShares.length !== s.candidates.length) bad('Candidate arrays disagree', ['seats', i]);
    if (s.winners.some(w => w >= s.candidates.length)) bad('Winner is not a candidate of the seat', ['seats', i]);
    if ((s.scope === 'general') !== (s.class !== 'maori-layer')) bad('Class does not match scope', ['seats', i]);
    if (s.seatPoll && s.scope !== 'general') bad('A seat poll update applies to general seats only', ['seats', i]);
    if (s.inflationWinners) {
      if (s.class !== 'maori-layer') bad('The calibration range applies to Māori seats only', ['seats', i]);
      if (s.inflationWinners.length !== n) bad('Every row needs one inflation winner', ['seats', i]);
      if (s.inflationWinners.some(w => w >= s.candidates.length)) bad('Inflation winner is not a candidate of the seat', ['seats', i]);
    }
  });
});
export type DrawBank = z.infer<typeof DrawBankSchema>;
export type SimulatedSeat = Extract<DrawBank['seats'][number], { status: 'simulated' }>;

/** Chain and within-chain position of a national draw id such as `live-A-attempt1-chain3-draw0012`. */
export function chainPosition(drawId: string): { chain: string; index: number } {
  const m = /^(.*-chain\d+)-draw(\d+)$/.exec(drawId);
  if (!m) throw new RangeError(`Draw id ${drawId} does not name a chain and draw`);
  return { chain: m[1], index: Number(m[2]) };
}
