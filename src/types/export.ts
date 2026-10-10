import { z } from 'zod';
import { IntervalSetSchema, MmpAllocationSchema, SimulationResultSchema } from './domain';

/**
 * Versioned website export contract (v2): the only way results reach the site.
 * The primary product is a nowcast (D106, docs/nowcast-specification.md): `targetType` names the estimand and
 * `modelStateAsOf` the latent-state date; the election date is context only. The `Forecast*` identifiers are
 * historical names kept for stability. Missing values are explicit `unavailable` records, never zero.
 */
const id = z.string().trim().min(1);
const sha256 = z.string().regex(/^[a-f0-9]{64}$/);
const unique = (values: string[]) => new Set(values).size === values.length;

export const SYNTHETIC_ID_PREFIX = 'synthetic-';
export const PLACEHOLDER_RULES_PREFIX = 'UNVERIFIED';
export const FORECAST_ARCHIVE_ROOT = 'forecasts';

export const ProvenanceSchema = z.discriminatedUnion('kind', [
  // Synthetic fixtures exercise plumbing only. Never application results.
  z.object({ kind: z.literal('synthetic-fixture'), label: id }).strict(),
  z.object({ kind: z.literal('model'), modelVersion: id, codeRevision: id, configVersion: id }).strict(),
]);

const Unavailable = z.object({ status: z.literal('unavailable'), reason: id }).strict();

export const ForecastDirectorySchema = z.object({
  parties: z.array(z.object({ partyId: id, name: id, abbreviation: id }).strict()).min(1),
  electorates: z.array(z.object({ electorateId: id, name: id, kind: z.enum(['general', 'maori']) }).strict()).min(1),
  // partyLabel keeps the ballot-group key of a candidate whose party has no national group (a minor party inside Other).
  candidates: z.array(z.object({ candidateId: id, name: id, electorateId: id, partyId: id.nullable(), partyLabel: id.nullable().optional() }).strict()),
}).strict();

/** A probability with its effective-sample Monte Carlo standard error and effective sample size. */
export const ProbabilityEstimateSchema = z.object({
  p: z.number().min(0).max(1), mcse: z.number().finite().nonnegative(), ess: z.number().finite().positive(),
}).strict();

/** Stage65 seat layer over every simulated election, with nested 50/80/90 seat intervals (D106). */
export const SeatLayerExportSchema = z.object({
  draws: z.number().int().positive(),
  rulesVersion: id,
  mcseMethod: id,
  parties: z.array(z.object({
    partyId: id, meanSeats: z.number().finite(), meanElectorateSeats: z.number().finite(), meanListSeats: z.number().finite(),
    seats: IntervalSetSchema, seatDistribution: z.record(z.string(), z.number().min(0).max(1)),
    probAnySeat: ProbabilityEstimateSchema, probQualified: ProbabilityEstimateSchema, probQualifiedByPartyVote: ProbabilityEstimateSchema,
    probQualifiedByLifeboatOnly: ProbabilityEstimateSchema, probOverhang: ProbabilityEstimateSchema,
  }).strict()),
  blocs: z.array(z.object({
    id, label: id, partyIds: z.array(id).min(1), meanSeats: z.number().finite(), seats: IntervalSetSchema,
    probMajority: ProbabilityEstimateSchema, probExactHalf: ProbabilityEstimateSchema,
  }).strict()),
  /** Named seat-arithmetic outcomes over blocs (for example a hung parliament); scenarios, not coalition predictions. */
  scenarios: z.array(z.object({ id, label: id, definition: id, probability: ProbabilityEstimateSchema }).strict()),
  parliament: z.object({
    meanSize: z.number().finite(), size: IntervalSetSchema, sizeDistribution: z.record(z.string(), z.number().min(0).max(1)),
    overhangDistribution: z.record(z.string(), z.number().min(0).max(1)), probAnyOverhang: ProbabilityEstimateSchema,
    meanOverhang: z.number().finite(),
  }).strict(),
}).strict();

/**
 * Per-seat detail: the D107 uncertainty class, candidate-share intervals and win probabilities with their errors. A polled Māori seat
 * also carries `winProbabilityInflation`, the win probability under Stage71's variance-inflation calibration (arm P): with
 * `winProbability` (the Stage66 control, C, which the seat totals use) it is the labelled C–P range (D114, D127).
 */
export const ElectorateDetailSchema = z.object({
  electorateId: id,
  uncertaintyClass: z.enum(['ordinary', 'exceptional', 'maori-layer']),
  candidates: z.array(z.object({
    candidateId: id, meanShare: z.number().min(0).max(1), share: IntervalSetSchema, winProbability: ProbabilityEstimateSchema,
    winProbabilityInflation: ProbabilityEstimateSchema.optional(),
  }).strict()).min(1),
}).strict().superRefine((d, ctx) => {
  const ranged = d.candidates.filter(c => c.winProbabilityInflation).length;
  if (ranged && (d.uncertaintyClass !== 'maori-layer' || ranged !== d.candidates.length))
    ctx.addIssue({ code: 'custom', message: 'A calibration range covers every candidate of a Māori seat, or none', path: ['candidates'] });
});

/**
 * Stage85 per-seat evidence (optional block; display data only, no forecast number depends on it). Names the polls found for a seat,
 * how much each moved the model, the seat's starting baseline and its uncertainty class. Balances are log(National / Labour).
 * A general seat's `weight` is exactly its contribution to the updated balance: updated = model + sum(weight x (poll - model)), and
 * the model keeps `modelWeight` = 1 - effectiveWeight = 1 - sum(weight). A Maori seat's poll is the one input of its layer, so it has
 * no share or weight. `status: 'not-used'` polls are context and carry the `reason`.
 */
const Fraction = z.number().min(0).max(1);
export const SeatPollEvidenceSchema = z.object({
  pollId: id, pollster: id.nullable(), sponsorGroup: id.nullable(),
  fieldworkStart: z.iso.date(), fieldworkEnd: z.iso.date(),
  sampleSize: z.number().positive().nullable(), sampleSizeAssumed: z.boolean(),
  candidateVotePct: z.array(z.object({ party: id, pct: z.number().min(0).max(100), name: id.optional() }).strict()).min(1),
  approximate: z.array(id), evidenceGrade: id.nullable(),
  status: z.enum(['used', 'not-used']), reason: id.nullable(),
  shareOfPoll: Fraction.nullable(), weight: Fraction.nullable(),
}).strict();

export const SeatPollUpdateSchema = z.object({
  pollBalance: z.number().finite(), modelBalance: z.number().finite(), updatedBalance: z.number().finite(),
  ageWeeks: z.number().finite().nonnegative(), ageFactor: Fraction, pollWeight: Fraction, effectiveWeight: Fraction, modelWeight: Fraction,
  modelSD: z.number().finite().positive(), posteriorSD: z.number().finite().positive(),
}).strict();

export const SeatEvidenceSchema = z.object({
  electorateId: id,
  uncertaintyClass: z.enum(['ordinary', 'exceptional', 'maori-layer']),
  multipliers: z.object({ balance: z.number().positive(), within: z.number().positive(), mass: z.number().positive() }).strict().nullable(),
  baseline: z.object({ basis: id, partyVote: z.array(z.object({ partyId: id, share: Fraction }).strict()).min(1) }).strict().nullable(),
  pollUpdate: SeatPollUpdateSchema.nullable(),
  polls: z.array(SeatPollEvidenceSchema),
}).strict().superRefine((e, ctx) => {
  const bad = (message: string, path: (string | number)[] = []) => ctx.addIssue({ code: 'custom', message, path });
  const close = (a: number, b: number) => Math.abs(a - b) < 1e-6;
  const maori = e.uncertaintyClass === 'maori-layer';
  if (maori !== (e.multipliers === null) || maori !== (e.baseline === null)) bad('Multipliers and baseline belong to general seats only', ['multipliers']);
  if (maori && e.pollUpdate !== null) bad('A Maori seat has no balance update', ['pollUpdate']);
  if (e.baseline && !close(e.baseline.partyVote.reduce((a, p) => a + p.share, 0), 1)) bad('Baseline party shares must sum to 1', ['baseline']);
  if (!unique(e.polls.map(p => p.pollId))) bad('Duplicate poll', ['polls']);
  const used = e.polls.filter(p => p.status === 'used');
  e.polls.forEach((p, i) => {
    if (p.fieldworkStart > p.fieldworkEnd) bad('Fieldwork ends before it starts', ['polls', i]);
    if ((p.status === 'not-used') !== (p.reason !== null)) bad('Exactly the unused polls carry a reason', ['polls', i, 'reason']);
    if (maori || p.status === 'not-used' ? p.shareOfPoll !== null || p.weight !== null : p.shareOfPoll === null || p.weight === null)
      bad('Share and weight belong to the used polls of a general seat', ['polls', i]);
  });
  if (!maori && (e.pollUpdate !== null) !== (used.length > 0)) bad('A general seat has a poll update exactly when a poll was used', ['pollUpdate']);
  if (e.pollUpdate && used.length > 0 && !maori) {
    const u = e.pollUpdate;
    if (!close(used.reduce((a, p) => a + (p.shareOfPoll ?? 0), 0), 1)) bad('Used poll shares must sum to 1', ['polls']);
    if (!close(used.reduce((a, p) => a + (p.weight ?? 0), 0), u.effectiveWeight)) bad('Poll weights must sum to the effective weight', ['polls']);
    if (!close(u.effectiveWeight + u.modelWeight, 1)) bad('Model and poll weights must sum to 1', ['pollUpdate']);
    if (!close(u.effectiveWeight, u.ageFactor * u.pollWeight)) bad('Effective weight is the age factor times the poll weight', ['pollUpdate']);
  }
});
export type SeatEvidence = z.infer<typeof SeatEvidenceSchema>;

export const BoundaryReferenceSchema = z.object({
  artifactId: id, path: z.string().regex(/^(?!\/)(?!.*\.\.)(?!.*\\).+\.geojson$/), sha256,
}).strict();

/** `nowcast` is the primary product; an election-day scenario may only ever be a separately labelled output. */
export const TARGET_TYPES = ['nowcast', 'election-day-scenario'] as const;

export const ForecastSnapshotSchema = z.object({
  schemaVersion: z.literal(2),
  snapshotId: id,
  targetType: z.enum(TARGET_TYPES),
  createdAt: z.iso.datetime({ offset: true }),
  dataCutoff: z.iso.datetime({ offset: true }),
  // Date of the latent national state the results describe (the latest poll-midpoint week), not "today".
  modelStateAsOf: z.iso.date(),
  electionId: id,
  // Context only: the election the nowcast refers to. Not the estimand of a nowcast.
  electionDate: z.iso.date(),
  provenance: ProvenanceSchema,
  directory: ForecastDirectorySchema,
  national: z.object({
    partyVoteShares: z.array(z.object({ partyId: id, share: IntervalSetSchema }).strict()).min(1),
    basis: id,
  }).strict(),
  simulation: SimulationResultSchema,
  unavailableElectorates: z.array(z.object({ electorateId: id, reason: id }).strict()),
  electorateDetail: z.array(ElectorateDetailSchema),
  /** Optional (Stage85): per-seat polls, baseline and class for the seat pages. Display data only. */
  seatEvidence: z.array(SeatEvidenceSchema).optional(),
  seatLayer: z.discriminatedUnion('status', [
    z.object({ status: z.literal('available'), summary: SeatLayerExportSchema }).strict(),
    z.object({ status: z.literal('unavailable'), reason: z.string().trim().min(1) }).strict(),
  ]),
  mmp: z.discriminatedUnion('status', [
    z.object({
      status: z.literal('available'),
      // One draw's allocation to show seat accounting. Not a forecast; the forecast is in simulation.
      exampleDrawAllocation: MmpAllocationSchema,
    }).strict(),
    Unavailable,
  ]),
  boundaries: BoundaryReferenceSchema.nullable(),
  limitations: z.array(id).min(1),
}).strict().superRefine((s, ctx) => {
  const bad = (message: string, path: (string | number)[] = []) => ctx.addIssue({ code: 'custom', message, path });
  const synthetic = s.provenance.kind === 'synthetic-fixture';
  if (synthetic !== s.snapshotId.startsWith(SYNTHETIC_ID_PREFIX))
    bad(`Snapshot id must start with "${SYNTHETIC_ID_PREFIX}" exactly when provenance is synthetic`, ['snapshotId']);
  if (!synthetic && s.mmp.status === 'available' &&
      s.mmp.exampleDrawAllocation.rulesVersion.toUpperCase().startsWith(PLACEHOLDER_RULES_PREFIX))
    bad('Placeholder MMP rules are only allowed in synthetic snapshots', ['mmp', 'exampleDrawAllocation', 'rulesVersion']);
  if (s.modelStateAsOf > s.dataCutoff.slice(0, 10))
    bad('The model state cannot postdate the data cutoff', ['modelStateAsOf']);
  if (Date.parse(s.dataCutoff) > Date.parse(s.createdAt))
    bad('The data cutoff cannot postdate the snapshot', ['dataCutoff']);
  if (s.targetType === 'nowcast' && s.electionDate < s.modelStateAsOf)
    bad('A nowcast model state cannot postdate the election', ['electionDate']);
  if (s.simulation.completedDraws !== s.simulation.config.draws)
    bad('A published snapshot must contain every requested draw', ['simulation', 'completedDraws']);
  if (s.simulation.config.electionId !== s.electionId)
    bad('Simulation election does not match snapshot election', ['simulation', 'config', 'electionId']);
  if (s.mmp.status === 'available' && s.mmp.exampleDrawAllocation.electionId !== s.electionId)
    bad('MMP election does not match snapshot election', ['mmp']);

  const partyIds = s.directory.parties.map(p => p.partyId);
  const electorateIds = s.directory.electorates.map(e => e.electorateId);
  const candidateIds = s.directory.candidates.map(c => c.candidateId);
  if (!unique(partyIds) || !unique(electorateIds) || !unique(candidateIds)) bad('Directory ids must be unique', ['directory']);
  const parties = new Set(partyIds), electorates = new Set(electorateIds), candidates = new Set(candidateIds);
  s.directory.candidates.forEach((c, i) => {
    if (!electorates.has(c.electorateId) || (c.partyId !== null && !parties.has(c.partyId)))
      bad('Candidate references unknown electorate or party', ['directory', 'candidates', i]);
  });
  s.national.partyVoteShares.forEach((p, i) => {
    if (!parties.has(p.partyId)) bad('Unknown party', ['national', 'partyVoteShares', i]);
    if (p.share.some(v => v.lower < 0 || v.upper > 1)) bad('Vote-share interval must be within 0–1', ['national', 'partyVoteShares', i]);
  });
  if (!unique(s.national.partyVoteShares.map(p => p.partyId))) bad('Duplicate national party', ['national']);
  // Missing is never zero: a listed party without a national share must fail, not render as blank or 0%.
  const shared = new Set(s.national.partyVoteShares.map(p => p.partyId));
  partyIds.forEach((partyId, i) => {
    if (!shared.has(partyId)) bad(`Party "${partyId}" has no national vote share`, ['national', 'partyVoteShares', i]);
  });
  // Fixture identifiers must never reach a model snapshot, whatever the snapshot id or provenance claims.
  if (!synthetic) {
    const fixtureIds: [string, (string | number)[]][] = [];
    s.directory.parties.forEach((p, i) => fixtureIds.push([p.partyId, ['directory', 'parties', i, 'partyId']]));
    s.directory.electorates.forEach((e, i) => fixtureIds.push([e.electorateId, ['directory', 'electorates', i, 'electorateId']]));
    s.directory.candidates.forEach((c, i) => fixtureIds.push([c.candidateId, ['directory', 'candidates', i, 'candidateId']]));
    fixtureIds.push([s.electionId, ['electionId']]);
    fixtureIds.forEach(([value, path]) => {
      if (value.toLowerCase().startsWith(SYNTHETIC_ID_PREFIX))
        bad(`Synthetic id "${value}" is not allowed in a non-synthetic snapshot`, path);
    });
  }

  const detailed = s.electorateDetail.map(d => d.electorateId);
  if (!unique(detailed)) bad('Duplicate electorate detail', ['electorateDetail']);
  s.electorateDetail.forEach((d, i) => {
    const prediction = s.simulation.electoratePredictions.find(p => p.electorateId === d.electorateId);
    if (!prediction) { bad('Electorate detail without a prediction', ['electorateDetail', i]); return; }
    const ids = new Set(prediction.candidates.map(c => c.candidateId));
    if (d.candidates.length !== ids.size || d.candidates.some(c => !ids.has(c.candidateId)))
      bad('Electorate detail must cover exactly the predicted candidates', ['electorateDetail', i]);
    d.candidates.forEach(c => {
      if (c.share.some(v => v.lower < 0 || v.upper > 1)) bad('Candidate-share interval must be within 0–1', ['electorateDetail', i]);
    });
  });
  // A model snapshot carries detail for every predicted seat; only synthetic pipeline fixtures may omit it.
  if (!synthetic && detailed.length !== s.simulation.electoratePredictions.length)
    bad('Every predicted electorate needs its uncertainty class and candidate-share intervals', ['electorateDetail']);
  if (s.seatEvidence) {
    const predictedIds = new Set(s.simulation.electoratePredictions.map(p => p.electorateId));
    const evidenced = s.seatEvidence.map(e => e.electorateId);
    if (!unique(evidenced) || evidenced.length !== predictedIds.size || evidenced.some(e => !predictedIds.has(e)))
      bad('Seat evidence must cover exactly the predicted electorates, once each', ['seatEvidence']);
    s.seatEvidence.forEach((e, i) => {
      const detail = s.electorateDetail.find(d => d.electorateId === e.electorateId);
      if (detail && detail.uncertaintyClass !== e.uncertaintyClass) bad('Seat evidence class differs from the electorate detail', ['seatEvidence', i, 'uncertaintyClass']);
      e.baseline?.partyVote.forEach(p => { if (!parties.has(p.partyId)) bad('Unknown party', ['seatEvidence', i, 'baseline']); });
    });
  }
  if (s.seatLayer.status === 'available') {
    s.seatLayer.summary.parties.forEach((p, i) => { if (!parties.has(p.partyId)) bad('Unknown party', ['seatLayer', 'summary', 'parties', i]); });
    if (s.seatLayer.summary.draws !== s.simulation.completedDraws) bad('Seat layer must use every simulated election', ['seatLayer']);
    if (s.mmp.status !== 'available') bad('An available seat layer needs an MMP example allocation', ['mmp']);
    if (!synthetic && s.seatLayer.summary.rulesVersion.toUpperCase().startsWith(PLACEHOLDER_RULES_PREFIX))
      bad('Placeholder MMP rules are only allowed in synthetic snapshots', ['seatLayer', 'summary', 'rulesVersion']);
  }
  if (s.seatLayer.status === 'available' && s.unavailableElectorates.length > 0)
    bad('The seat layer needs a winner in every electorate', ['seatLayer']);

  const predicted = s.simulation.electoratePredictions.map(p => p.electorateId);
  const unavailable = s.unavailableElectorates.map(u => u.electorateId);
  if (!unique([...predicted, ...unavailable]) || [...predicted, ...unavailable].some(e => !electorates.has(e)) ||
      predicted.length + unavailable.length !== electorates.size)
    bad('Every directory electorate needs exactly one prediction or an explicit unavailable record', ['unavailableElectorates']);
  s.simulation.electoratePredictions.forEach((p, i) => p.candidates.forEach(c => {
    if (!candidates.has(c.candidateId)) bad('Prediction names unknown candidate', ['simulation', 'electoratePredictions', i]);
  }));
  s.simulation.partySeatSummaries.forEach((p, i) => {
    if (!parties.has(p.partyId)) bad('Unknown party', ['simulation', 'partySeatSummaries', i]);
  });
  if (s.mmp.status === 'available') s.mmp.exampleDrawAllocation.parties.forEach(p => {
    if (!parties.has(p.partyId)) bad('MMP names unknown party', ['mmp']);
  });
  s.simulation.governmentOutcomes.forEach(g => {
    if (!s.simulation.config.governmentCombinations.some(c => c.id === g.combinationId))
      bad('Government outcome has no configured combination', ['simulation', 'governmentOutcomes']);
  });
});
export type ForecastSnapshot = z.infer<typeof ForecastSnapshotSchema>;

/** Append-only archive index. Snapshot files are immutable; corrections add a new entry that supersedes. */
export const ForecastIndexSchema = z.object({
  schemaVersion: z.literal(1),
  snapshots: z.array(z.object({
    snapshotId: id,
    createdAt: z.iso.datetime({ offset: true }),
    dataCutoff: z.iso.datetime({ offset: true }),
    provenanceKind: z.enum(['synthetic-fixture', 'model']),
    // Relative to the index; content-addressed so a changed file cannot be loaded silently.
    path: z.string().regex(/^(?!\/)(?!.*\.\.)(?!.*\\)[A-Za-z0-9._-]+\/snapshot\.json$/),
    sha256,
    supersedes: id.nullable(),
    status: z.enum(['published', 'withdrawn']),
    withdrawnReason: id.nullable(),
  }).strict()),
}).strict().superRefine((index, ctx) => {
  const bad = (message: string, path: (string | number)[]) => ctx.addIssue({ code: 'custom', message, path });
  const ids = index.snapshots.map(e => e.snapshotId);
  if (!unique(ids)) bad('Duplicate snapshot id', ['snapshots']);
  index.snapshots.forEach((e, i) => {
    if (e.path !== `${e.snapshotId}/snapshot.json`) bad('Path must be <snapshotId>/snapshot.json', ['snapshots', i, 'path']);
    if ((e.provenanceKind === 'synthetic-fixture') !== e.snapshotId.startsWith(SYNTHETIC_ID_PREFIX))
      bad('Provenance kind disagrees with snapshot id prefix', ['snapshots', i]);
    if ((e.status === 'withdrawn') !== (e.withdrawnReason !== null)) bad('Withdrawn entries need a reason and only they have one', ['snapshots', i]);
    if (e.supersedes !== null && !ids.slice(0, i).includes(e.supersedes)) bad('supersedes must name an earlier entry', ['snapshots', i, 'supersedes']);
    if (i > 0 && e.createdAt < index.snapshots[i - 1].createdAt) bad('Entries must be ordered by createdAt', ['snapshots', i, 'createdAt']);
  });
});
export type ForecastIndex = z.infer<typeof ForecastIndexSchema>;

const Position = z.tuple([z.number().finite(), z.number().finite()]).rest(z.number().finite());
export const ElectorateGeometrySchema = z.object({
  type: z.literal('FeatureCollection'),
  features: z.array(z.object({
    type: z.literal('Feature'),
    properties: z.object({ electorateId: id }).passthrough(),
    geometry: z.discriminatedUnion('type', [
      z.object({ type: z.literal('Polygon'), coordinates: z.array(z.array(Position)) }).strict(),
      z.object({ type: z.literal('MultiPolygon'), coordinates: z.array(z.array(z.array(Position))) }).strict(),
    ]),
  }).strict()).min(1),
}).strict();
export type ElectorateGeometry = z.infer<typeof ElectorateGeometrySchema>;
