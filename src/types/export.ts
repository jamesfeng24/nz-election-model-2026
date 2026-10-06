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
  candidates: z.array(z.object({ candidateId: id, name: id, electorateId: id, partyId: id.nullable() }).strict()),
}).strict();

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
  // The site must show uncalibrated outputs as such; the release policy is a separate decision.
  calibrationStatus: z.enum(['uncalibrated', 'validated']),
  directory: ForecastDirectorySchema,
  national: z.object({
    partyVoteShares: z.array(z.object({ partyId: id, share: IntervalSetSchema }).strict()).min(1),
    basis: id,
  }).strict(),
  simulation: SimulationResultSchema,
  unavailableElectorates: z.array(z.object({ electorateId: id, reason: id }).strict()),
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
  if (!synthetic && s.calibrationStatus === 'validated' && s.simulation.limitations.length === 0)
    bad('Validated snapshots must state residual limitations', ['simulation', 'limitations']);
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
