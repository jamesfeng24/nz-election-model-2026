import { z } from 'zod';

// Draft v1 exchange contracts, not observations or statistical algorithms.
const id = z.string().trim().min(1);
const count = z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER);
const share = z.number().min(0).max(1);
const date = z.iso.date();
const ids = z.array(id).refine(values => new Set(values).size === values.length, 'IDs must be unique');
const sourced = { schemaVersion: z.literal(1), id, sourceIds: ids.min(1) };
const nullableCount = count.nullable();

export const PartySchema = z.object({
  ...sourced, name: id, abbreviation: id,
  // Relationships describe identity evidence, never automatic model transfer.
  relatedPartyIds: ids, validFrom: date.nullable(), validTo: date.nullable(),
}).strict();
export type Party = z.infer<typeof PartySchema>;

export const PollsterSchema = z.object({ ...sourced, name: id, methodologyUrl: z.url().nullable() }).strict();
export type Pollster = z.infer<typeof PollsterSchema>;

export const PollSchema = z.object({
  ...sourced, pollsterId: id, fieldworkStart: date, fieldworkEnd: date,
  publishedOn: date, sampleSize: count.positive().nullable(), population: id,
  mode: id, voteType: z.enum(['party', 'candidate']),
  electorateId: id.nullable(), boundaryVersionId: id.nullable(),
  denominator: id, undecidedShare: share.nullable(),
  results: z.array(z.object({ choiceId: id, share }).strict()).min(1),
  limitations: z.array(id),
}).strict().superRefine((poll, ctx) => {
  if (poll.fieldworkEnd < poll.fieldworkStart || poll.publishedOn < poll.fieldworkEnd)
    ctx.addIssue({ code: 'custom', message: 'Invalid poll chronology' });
  if ((poll.electorateId === null) !== (poll.boundaryVersionId === null))
    ctx.addIssue({ code: 'custom', message: 'Local polls require electorate and boundary together' });
  if (poll.voteType === 'candidate' && poll.electorateId === null)
    ctx.addIssue({ code: 'custom', message: 'Candidate polls require an electorate' });
  if (new Set(poll.results.map(r => r.choiceId)).size !== poll.results.length)
    ctx.addIssue({ code: 'custom', message: 'Duplicate poll choice' });
  // Allow published rounding and incomplete choice coverage. Undecideds may use a different base.
  if (poll.results.reduce((sum, r) => sum + r.share, 0) > 1.01)
    ctx.addIssue({ code: 'custom', message: 'Reported shares exceed rounding tolerance' });
});
export type Poll = z.infer<typeof PollSchema>;

export const ElectionSchema = z.object({
  ...sourced, name: id, electionDate: date.nullable(),
  kind: z.enum(['general', 'by-election']), boundaryVersionId: id,
  rulesSourceIds: ids, expectedElectorateCount: nullableCount,
}).strict();
export type Election = z.infer<typeof ElectionSchema>;

export const ElectorateBoundaryVersionSchema = z.object({
  ...sourced, label: id, effectiveFrom: date.nullable(), effectiveTo: date.nullable(),
  geometryArtifactId: id.nullable(), coordinateReferenceSystem: id.nullable(),
}).strict();
export type ElectorateBoundaryVersion = z.infer<typeof ElectorateBoundaryVersionSchema>;

export const ElectorateSchema = z.object({
  ...sourced, name: id, boundaryVersionId: id,
  kind: z.enum(['general', 'maori']), predecessorIds: ids,
}).strict();
export type Electorate = z.infer<typeof ElectorateSchema>;

export const CandidateSchema = z.object({ ...sourced, name: id }).strict();
export type Candidate = z.infer<typeof CandidateSchema>;

export const CandidateStatusSchema = z.object({
  ...sourced, candidateId: id, electionId: id, electorateId: id.nullable(),
  boundaryVersionId: id.nullable(), partyId: id.nullable(),
  status: z.enum([
    'established-continuing-incumbent', 'first-term-incumbent',
    'returning-former-incumbent', 'replacement-candidate',
    'returning-challenger', 'completely-new-candidate', 'list-only-candidate', 'unknown',
  ]),
  isPartyLeader: z.boolean().nullable(), priorElectorateTerms: nullableCount,
  replacesCandidateId: id.nullable(), classificationReason: id,
}).strict().superRefine((record, ctx) => {
  if ((record.electorateId === null) !== (record.boundaryVersionId === null))
    ctx.addIssue({ code: 'custom', message: 'Electorate and boundary must occur together' });
  if (record.status === 'list-only-candidate' && record.electorateId !== null)
    ctx.addIssue({ code: 'custom', message: 'List-only candidates cannot contest an electorate' });
  if (!['list-only-candidate', 'unknown'].includes(record.status) && record.electorateId === null)
    ctx.addIssue({ code: 'custom', message: 'Electorate status requires electorate context' });
  if (record.status === 'first-term-incumbent' && record.priorElectorateTerms !== 1)
    ctx.addIssue({ code: 'custom', message: 'First-term classification requires exactly one evidenced term before this election' });
  if (record.status === 'completely-new-candidate' && record.priorElectorateTerms !== 0)
    ctx.addIssue({ code: 'custom', message: 'New candidates require zero prior electorate terms' });
});
export type CandidateStatus = z.infer<typeof CandidateStatusSchema>;

const localResult = {
  ...sourced, electionId: id, electorateId: id, boundaryVersionId: id,
  votes: nullableCount, totalValidVotes: nullableCount,
  basis: z.enum(['official', 'reconstructed']), missingReason: id.nullable(),
};
function validateVotes(result: { votes: number | null; totalValidVotes: number | null; missingReason: string | null }, ctx: z.RefinementCtx) {
  if ((result.votes === null || result.totalValidVotes === null) && result.missingReason === null)
    ctx.addIssue({ code: 'custom', message: 'Missing counts require a reason' });
  if (result.votes !== null && result.totalValidVotes !== null && result.votes > result.totalValidVotes)
    ctx.addIssue({ code: 'custom', message: 'Votes exceed valid-vote denominator' });
}
export const CandidateElectionResultSchema = z.object({
  ...localResult, candidateId: id, partyId: id.nullable(), elected: z.boolean().nullable(),
}).strict().superRefine(validateVotes);
export type CandidateElectionResult = z.infer<typeof CandidateElectionResultSchema>;
export const PartyVoteResultSchema = z.object({ ...localResult, partyId: id }).strict().superRefine(validateVotes);
export type PartyVoteResult = z.infer<typeof PartyVoteResultSchema>;

export const SplitVoteMatrixSchema = z.object({
  ...sourced, electionId: id, electorateId: id, boundaryVersionId: id,
  // Explicit categories also permit invalid, other and withheld cells.
  partyCategories: z.array(z.object({ id, partyId: id.nullable(), label: id }).strict()).min(1),
  candidateCategories: z.array(z.object({ id, candidateId: id.nullable(), label: id }).strict()).min(1),
  cells: z.array(z.object({ partyCategoryId: id, candidateCategoryId: id, count: nullableCount }).strict()),
  denominator: id, totalBallots: nullableCount, completeness: z.enum(['complete', 'partial']), limitations: z.array(id),
}).strict().superRefine((matrix, ctx) => {
  const rows = new Set(matrix.partyCategories.map(c => c.id));
  const cols = new Set(matrix.candidateCategories.map(c => c.id));
  const keys = new Set<string>();
  if (rows.size !== matrix.partyCategories.length || cols.size !== matrix.candidateCategories.length)
    ctx.addIssue({ code: 'custom', message: 'Duplicate matrix category' });
  for (const cell of matrix.cells) {
    const key = JSON.stringify([cell.partyCategoryId, cell.candidateCategoryId]);
    if (!rows.has(cell.partyCategoryId) || !cols.has(cell.candidateCategoryId) || keys.has(key))
      ctx.addIssue({ code: 'custom', message: 'Invalid or duplicate matrix cell' });
    keys.add(key);
  }
  const total = matrix.cells.reduce((sum, cell) => sum + (cell.count ?? 0), 0);
  if (matrix.totalBallots !== null && total > matrix.totalBallots)
    ctx.addIssue({ code: 'custom', message: 'Cells exceed ballot total' });
  if (matrix.completeness === 'complete' && (keys.size !== rows.size * cols.size ||
      matrix.cells.some(c => c.count === null) || matrix.totalBallots === null || total !== matrix.totalBallots))
    ctx.addIssue({ code: 'custom', message: 'Complete matrix requires all cells and a matching total' });
});
export type SplitVoteMatrix = z.infer<typeof SplitVoteMatrixSchema>;

export const IntervalSchema = z.object({
  lower: z.number().finite(), median: z.number().finite(), upper: z.number().finite(),
  level: z.number().gt(0).lt(1), method: id,
}).strict().refine(v => v.lower <= v.median && v.median <= v.upper, 'Interval must be ordered');

const prediction = {
  schemaVersion: z.literal(1), id, electionId: id, modelVersion: id,
  sourceIds: ids.min(1), artifactIds: ids.min(1), asOf: z.iso.datetime({ offset: true }),
  limitations: z.array(id),
};
export const ModelPredictionSchema = z.object({
  ...prediction, estimator: z.enum(['split-ticket', 'elasticity', 'normalized-premium', 'national-support', 'ensemble']),
  target: z.discriminatedUnion('kind', [
    z.object({ kind: z.literal('national-party'), partyId: id }).strict(),
    z.object({ kind: z.literal('electorate-party'), partyId: id, electorateId: id, boundaryVersionId: id }).strict(),
    z.object({ kind: z.literal('electorate-candidate'), candidateId: id, electorateId: id, boundaryVersionId: id }).strict(),
  ]),
  unit: z.literal('proportion'), estimate: IntervalSchema,
}).strict().refine(v => v.estimate.lower >= 0 && v.estimate.upper <= 1, 'Vote-share interval must be within 0–1');
export type ModelPrediction = z.infer<typeof ModelPredictionSchema>;

export const SeatPredictionSchema = z.object({
  ...prediction, electorateId: id, boundaryVersionId: id,
  candidates: z.array(z.object({ candidateId: id, winProbability: share }).strict()).min(1),
}).strict().superRefine((seat, ctx) => {
  if (new Set(seat.candidates.map(c => c.candidateId)).size !== seat.candidates.length ||
      Math.abs(seat.candidates.reduce((sum, c) => sum + c.winProbability, 0) - 1) > 1e-6)
    ctx.addIssue({ code: 'custom', message: 'Candidate probabilities must be unique and sum to one' });
});
export type SeatPrediction = z.infer<typeof SeatPredictionSchema>;

export const MmpAllocationSchema = z.object({
  schemaVersion: z.literal(1), electionId: id, rulesVersion: id, rulesSourceIds: ids.min(1),
  nominalSeats: count.positive(), parliamentSize: count.positive(), overhangSeats: count,
  unfilledSeats: count,
  parties: z.array(z.object({
    partyId: id, qualified: z.boolean(), qualificationReason: id,
    electorateSeats: count, listSeats: count, totalSeats: count,
  }).strict()),
  independentElectorateSeats: count,
}).strict().superRefine((allocation, ctx) => {
  if (new Set(allocation.parties.map(p => p.partyId)).size !== allocation.parties.length ||
      allocation.parties.some(p => p.totalSeats !== p.electorateSeats + p.listSeats))
    ctx.addIssue({ code: 'custom', message: 'Duplicate party or inconsistent party seats' });
  const filled = allocation.parties.reduce((sum, p) => sum + p.totalSeats, allocation.independentElectorateSeats);
  if (filled + allocation.unfilledSeats !== allocation.parliamentSize ||
      allocation.parliamentSize !== allocation.nominalSeats + allocation.overhangSeats)
    ctx.addIssue({ code: 'custom', message: 'Seat accounting does not reconcile' });
});
export type MmpAllocation = z.infer<typeof MmpAllocationSchema>;

export const SimulationConfigSchema = z.object({
  schemaVersion: z.literal(1), electionId: id, modelVersion: id, codeRevision: id,
  seed: id, prng: id, prngVersion: id, draws: count.positive(),
  inputs: z.array(z.object({ artifactId: id, sha256: z.string().regex(/^[a-f0-9]{64}$/) }).strict()).min(1),
  governmentCombinations: z.array(z.object({ id, partyIds: ids.min(1), requiredSeats: count.positive() }).strict()),
}).strict();
export type SimulationConfig = z.infer<typeof SimulationConfigSchema>;
export const SimulationResultSchema = z.object({
  schemaVersion: z.literal(1), runId: id, config: SimulationConfigSchema,
  completedDraws: count.positive(), electoratePredictions: z.array(SeatPredictionSchema),
  partySeatSummaries: z.array(z.object({ partyId: id, seats: IntervalSchema }).strict()),
  governmentOutcomes: z.array(z.object({ combinationId: id, probability: share }).strict()),
  limitations: z.array(id),
}).strict().refine(r => r.completedDraws <= r.config.draws, 'Completed draws exceed requested draws');
export type SimulationResult = z.infer<typeof SimulationResultSchema>;

// Plain JSON only: this defines the boundary, not a running worker or simulation.
export type SimulationWorkerRequest = { type: 'run'; requestId: string; config: SimulationConfig };
export type SimulationWorkerResponse =
  | { type: 'progress'; requestId: string; completedDraws: number }
  | { type: 'result'; requestId: string; result: SimulationResult }
  | { type: 'error'; requestId: string; message: string };
