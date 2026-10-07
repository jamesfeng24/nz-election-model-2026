import { z } from 'zod';

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

const Simulated = z.object({
  electorateId: id, scope: z.enum(['general', 'maori']), status: z.literal('simulated'),
  class: z.enum(['ordinary', 'exceptional', 'maori-layer']),
  multiplier: z.number().positive().optional(),
  source: id.optional(),
  candidates: z.array(id).min(2),
  candidateNames: z.array(id).optional(),
  candidateParty: z.array(id.nullable()),
  candidateShares: z.array(ShareSummarySchema),
  winnerParty: z.array(id.nullable()),
  winnerCandidate: z.array(id),
}).strict();
const Unavailable = z.object({ electorateId: id, scope: z.enum(['general', 'maori']), status: z.literal('unavailable'), reason: id }).strict();

export const DrawBankSchema = z.object({
  schemaVersion: z.literal(2),
  stage: z.number().int(),
  electionYear: z.number().int(),
  provenance: z.enum(['live', 'synthetic-fixture']),
  configVersion: id,
  estimand: z.literal('nowcast'),
  modelStateAsOf: z.iso.date(),
  dataCutoff: z.iso.date(),
  nationalStateKey: z.literal('lastDataSupport'),
  inputs: z.record(z.string(), z.string()),
  draws: z.number().int().positive(),
  drawIds: z.array(id),
  partyVote: z.object({ groups: z.array(id).min(2), otherBucket: id, shares: z.array(z.array(z.number().finite().nonnegative())) }).strict(),
  seats: z.array(z.discriminatedUnion('status', [Simulated, Unavailable])),
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
  if (bank.drawIds.length !== n || new Set(bank.drawIds).size !== n) bad('Every row needs one distinct national draw id', ['drawIds']);
  if (bank.partyVote.shares.length !== n) bad('Every row needs one party vote', ['partyVote', 'shares']);
  if (!bank.partyVote.groups.includes(bank.partyVote.otherBucket)) bad('The other bucket must be a national group', ['partyVote']);
  bank.partyVote.shares.forEach((row, i) => {
    if (row.length !== bank.partyVote.groups.length || Math.abs(row.reduce((a, b) => a + b, 0) - 1) > 1e-9)
      bad('Party vote row must be a simplex over the national groups', ['partyVote', 'shares', i]);
  });
  const ids = bank.seats.map(s => s.electorateId);
  if (new Set(ids).size !== ids.length) bad('Duplicate electorate', ['seats']);
  bank.seats.forEach((s, i) => {
    if (s.status !== 'simulated') return;
    if (s.winnerParty.length !== n || s.winnerCandidate.length !== n) bad('Every row needs one winner', ['seats', i]);
    if (s.candidateParty.length !== s.candidates.length || s.candidateShares.length !== s.candidates.length) bad('Candidate arrays disagree', ['seats', i]);
    const known = new Set(s.candidates);
    if (s.winnerCandidate.some(c => !known.has(c))) bad('Winner is not a candidate of the seat', ['seats', i]);
    if ((s.scope === 'general') !== (s.class !== 'maori-layer')) bad('Class does not match scope', ['seats', i]);
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
