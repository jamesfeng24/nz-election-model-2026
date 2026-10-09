import { INTERVAL_LEVELS, type IntervalSet, type MmpAllocation, type SimulationConfig } from '../../types/domain';
import { z } from 'zod';
import { ForecastSnapshotSchema, NationalPollSchema, NationalTrendSchema, SeatPollBaseSchema, SnapshotEvidenceSchema, type ForecastSnapshot } from '../../types/export';
import { allocateDraw, SeatSummaryAccumulator, type BlocDefinition, type SeatDrawOutcome, type SeatLayerConfig } from '../mmp/seatLayer';
import { batchMeansMcse, chainOrder, type ChainOrder } from './batchMeans';
import { DrawBankSchema, type DrawBank, type SimulatedSeat } from './drawBank';

/**
 * Stage74: a Stage73 draw bank to a validated v2 nowcast snapshot. Every bank row is one simulated election; the
 * Stage65 seat layer (Stage49 allocator, unchanged) runs on each row. Probabilities carry effective-sample Monte Carlo
 * errors by batch means within national MCMC chains. Anything missing is an explicit `unavailable` record: an
 * unavailable seat withholds the seat layer and MMP, never fills them with zeros. The snapshot schema rejects a
 * synthetic bank presented as a model run.
 */
export interface NowcastSnapshotOptions {
  snapshotId: string;
  createdAt: string;
  /** ISO datetime of the data cutoff (the bank carries the date). */
  dataCutoff: string;
  electionId: string;
  electionDate: string;
  boundaryVersionId: string;
  modelVersion: string;
  codeRevision: string;
  bankSha256: string;
  /** Required for the seat layer; null withholds it with a reason. */
  mmp: { rulesVersion: string; rulesSourceIds: string[]; blocs: BlocDefinition[]; hungParliament?: HungParliament | null } | null;
  nationalBasis: string;
  limitations: string[];
  syntheticLabel?: string;
  /** Optional site evidence file written by `scripts/site_evidence/build.py`: the polls used and the national trend. */
  evidence?: unknown;
}

/** The evidence file: national polls and trend, and seat polls keyed by electorate name (resolved against the directory). */
export const EvidenceFileSchema = z.object({
  source: SnapshotEvidenceSchema.shape.source,
  nationalPolls: z.array(NationalPollSchema),
  trend: NationalTrendSchema.nullable(),
  seatPolls: z.array(SeatPollBaseSchema.omit({ results: true }).extend({
    electorateName: z.string().trim().min(1),
    results: z.array(z.object({ name: z.string().trim().min(1), party: z.string().nullable(), percent: z.number().min(0).max(100), approximate: z.boolean().optional() }).strict()).min(1),
  })),
}).loose();

const plain = (text: string) => text.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

const BASIS_GENERAL = 'No seat poll feeds this seat. The estimate starts from the 2023 result on the 2026 boundaries, is moved with the national picture, and allows for candidate effects.';
const BASIS_FALLBACK = 'No seat poll feeds this seat. It starts from the 2023 result carried forward, with wide uncertainty.';
const BASIS_POLLED = 'Estimated from the seat poll listed below together with earlier results at the 2026 boundaries.';

/** Per-seat evidence: the polls found for this seat (matched by name, never guessed) and a plain statement of what the estimate rests on. */
function seatEvidence(seat: SimulatedSeat, electorateName: string, bank: DrawBank, file: z.infer<typeof EvidenceFileSchema>) {
  const polls = file.seatPolls.filter(p => plain(p.electorateName) === plain(electorateName)).map(({ electorateName: _name, results, ...rest }) => ({
    ...rest,
    results: results.map(r => {
      const matches = bank.directory.candidates.filter(c => c.electorateId === seat.electorateId && plain(c.name) === plain(r.name));
      return { candidateId: matches.length === 1 ? matches[0].candidateId : null, name: r.name, party: r.party, percent: r.percent, ...(r.approximate === undefined ? {} : { approximate: r.approximate }) };
    }),
  }));
  const used = polls.some(p => p.usedInModel);
  const unused = polls.length > 0 && !used ? ' A poll for this seat was found but is not used in this forecast.' : '';
  const basis = (seat.source ?? '').toLowerCase().includes('fallback') ? BASIS_FALLBACK + unused : used ? BASIS_POLLED : BASIS_GENERAL + unused;
  return { basis, polls };
}

/** Hung parliament over two named blocs, with an optional kingmaker party (James, 2026-10-07). */
export interface HungParliament { blocs: [string, string]; kingmaker?: string | null; definition?: string }

const METHOD = 'empirical-quantile (linear) of the bank rows';
const SEAT_METHOD = 'empirical-quantile (lower step) of the bank rows';
const MCSE_METHOD = 'batch means within national MCMC chains (non-overlapping, about sqrt(n) batches)';

function quantile(sorted: number[], p: number): number {
  const pos = (sorted.length - 1) * p, lo = Math.floor(pos), hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}
function linearIntervals(values: number[]): IntervalSet {
  const s = [...values].sort((a, b) => a - b), median = quantile(s, 0.5);
  return INTERVAL_LEVELS.map(level => ({ lower: quantile(s, (1 - level) / 2), median, upper: quantile(s, 1 - (1 - level) / 2), level, method: METHOD }));
}
/** Integer outcomes: the smallest value whose cumulative frequency reaches q, as the Stage65 summaries. */
function stepQuantile(sorted: number[], q: number): number {
  return sorted[Math.min(sorted.length - 1, Math.max(0, Math.ceil(q * sorted.length - 1e-9) - 1))];
}
function stepIntervals(values: number[]): IntervalSet {
  const s = [...values].sort((a, b) => a - b), median = stepQuantile(s, 0.5);
  return INTERVAL_LEVELS.map(level => ({ lower: stepQuantile(s, (1 - level) / 2), median, upper: stepQuantile(s, 1 - (1 - level) / 2), level, method: SEAT_METHOD }));
}
const probability = (flags: number[], layout: ChainOrder, unit = 1) => {
  const r = batchMeansMcse(flags, layout, unit);
  return { p: r.mean, mcse: r.mcse, ess: r.ess };
};

export function seatLayerConfig(bank: DrawBank, mmp: NonNullable<NowcastSnapshotOptions['mmp']>): SeatLayerConfig {
  const other = bank.partyVote.otherBucket;
  return {
    rulesVersion: mmp.rulesVersion, rulesSourceIds: mmp.rulesSourceIds, blocs: mmp.blocs,
    listedPartyIds: bank.partyVote.groups.filter(g => g !== other), unlistedBucketIds: [other],
    expectedElectorateIds: {
      general: bank.seats.filter(s => s.scope === 'general').map(s => s.electorateId),
      maori: bank.seats.filter(s => s.scope === 'maori').map(s => s.electorateId),
    },
  };
}

/** Run the Stage65 seat layer on every bank row. Requires every seat simulated. */
export function runSeatLayer(bank: DrawBank, config: SeatLayerConfig, electionId: string): { outcomes: SeatDrawOutcome[]; accumulator: SeatSummaryAccumulator } {
  const seats = bank.seats as SimulatedSeat[];
  if (bank.seats.some(s => s.status !== 'simulated')) throw new RangeError('The seat layer needs a winner in every electorate');
  const accumulator = new SeatSummaryAccumulator(config);
  const outcomes: SeatDrawOutcome[] = [];
  for (let row = 0; row < bank.draws; row++) {
    const winners = (scope: 'general' | 'maori') => seats.filter(s => s.scope === scope)
      .map(s => ({ electorateId: s.electorateId, partyId: s.candidateParty[s.winners[row]], candidateId: s.candidates[s.winners[row]] }));
    const outcome = allocateDraw(config, {
      electionId,
      partyVoteShares: Object.fromEntries(bank.partyVote.groups.map((g, i) => [g, bank.partyVote.shares[Math.floor(row / bank.layerReplicates)][i]])),
      generalWinners: winners('general'), maoriWinners: winners('maori'),
    });
    accumulator.add(outcome);
    outcomes.push(outcome);
  }
  return { outcomes, accumulator };
}

function hungScenarios(config: SeatLayerConfig, hung: HungParliament,
  flag: (f: (o: SeatDrawOutcome) => boolean) => { p: number; mcse: number; ess: number }) {
  const blocs = hung.blocs.map(id => config.blocs.find(b => b.id === id));
  if (blocs.some(b => !b)) throw new RangeError('Hung-parliament blocs must be configured blocs');
  const [a, b] = blocs as BlocDefinition[];
  const seats = (o: SeatDrawOutcome, ids: string[]) => ids.reduce((sum, id) => sum + o.parties[id].totalSeats, 0);
  const majority = (o: SeatDrawOutcome, ids: string[]) => 2 * seats(o, ids) > o.parliamentSize;
  const isHung = (o: SeatDrawOutcome) => !majority(o, a.partyIds) && !majority(o, b.partyIds);
  const out = [{ id: 'hung', label: `Hung parliament (neither ${a.label} nor ${b.label})`,
    definition: `Neither ${a.label} nor ${b.label} holds more than half of that simulated Parliament`, probability: flag(isHung) }];
  const k = hung.kingmaker;
  if (k) {
    if (!config.listedPartyIds.includes(k) || a.partyIds.includes(k) || b.partyIds.includes(k)) throw new RangeError('Kingmaker must be a listed party outside both blocs');
    const withA = (o: SeatDrawOutcome) => isHung(o) && majority(o, [...a.partyIds, k]);
    const withB = (o: SeatDrawOutcome) => isHung(o) && majority(o, [...b.partyIds, k]);
    // James (2026-10-07): only the cases where the kingmaker decides are reported; hung with neither side able to
    // reach a majority even with the kingmaker is the remainder of `hung` and is not a separate output.
    out.push(
      { id: `hung-${k}-kingmaker`, label: `Hung parliament, ${k} kingmaker (either side)`,
        definition: `Hung, and adding ${k}'s seats gives either ${a.label} or ${b.label} a majority`, probability: flag(o => withA(o) && withB(o)) },
      { id: `hung-${k}-${a.id}-only`, label: `Hung parliament, only ${a.label} with ${k}`,
        definition: `Hung; ${a.label} plus ${k} is a majority, ${b.label} plus ${k} is not`, probability: flag(o => withA(o) && !withB(o)) },
      { id: `hung-${k}-${b.id}-only`, label: `Hung parliament, only ${b.label} with ${k}`,
        definition: `Hung; ${b.label} plus ${k} is a majority, ${a.label} plus ${k} is not`, probability: flag(o => withB(o) && !withA(o)) });
  }
  return out;
}

function seatLayerSummary(bank: DrawBank, config: SeatLayerConfig, layout: ChainOrder, electionId: string, hung: HungParliament | null) {
  const { outcomes, accumulator } = runSeatLayer(bank, config, electionId);
  const summary = accumulator.summarise();
  const unit = bank.layerReplicates;
  const flag = (f: (o: SeatDrawOutcome) => boolean) => probability(outcomes.map(o => (f(o) ? 1 : 0)), layout, unit);
  return {
    example: outcomes[0].allocation as MmpAllocation,
    summary: {
      draws: summary.draws, rulesVersion: config.rulesVersion, mcseMethod: MCSE_METHOD,
      parties: summary.parties.map(p => ({
        partyId: p.partyId, meanSeats: p.meanSeats, meanElectorateSeats: p.meanElectorateSeats, meanListSeats: p.meanListSeats,
        seats: stepIntervals(outcomes.map(o => o.parties[p.partyId].totalSeats)), seatDistribution: p.seatDistribution,
        probAnySeat: flag(o => o.parties[p.partyId].totalSeats > 0),
        probQualified: flag(o => o.parties[p.partyId].qualified),
        probQualifiedByPartyVote: flag(o => o.parties[p.partyId].qualifiedByPartyVote),
        probQualifiedByLifeboatOnly: flag(o => o.parties[p.partyId].qualified && !o.parties[p.partyId].qualifiedByPartyVote),
        probOverhang: flag(o => o.parties[p.partyId].overhang > 0),
      })),
      blocs: config.blocs.map((b, i) => {
        const seats = outcomes.map(o => b.partyIds.reduce((sum, id) => sum + o.parties[id].totalSeats, 0));
        return {
          id: b.id, label: b.label, partyIds: [...b.partyIds], meanSeats: summary.blocs[i].meanSeats, seats: stepIntervals(seats),
          probMajority: probability(outcomes.map((o, k) => (2 * seats[k] > o.parliamentSize ? 1 : 0)), layout, unit),
          probExactHalf: probability(outcomes.map((o, k) => (2 * seats[k] === o.parliamentSize ? 1 : 0)), layout, unit),
        };
      }),
      scenarios: hung ? hungScenarios(config, hung, flag) : [],
      parliament: {
        meanSize: summary.parliament.meanSize, size: stepIntervals(outcomes.map(o => o.parliamentSize)),
        sizeDistribution: summary.parliament.sizeDistribution, overhangDistribution: summary.parliament.overhangDistribution,
        probAnyOverhang: flag(o => o.overhangSeats > 0), meanOverhang: summary.parliament.meanOverhang,
      },
    },
  };
}

function shareIntervals(seat: SimulatedSeat, candidateId: string): { mean: number; share: IntervalSet } {
  const s = seat.candidateShares.find(c => c.candidateId === candidateId);
  if (!s) throw new RangeError(`${seat.electorateId}: no share summary for ${candidateId}`);
  return { mean: s.mean, share: s.intervals.map(v => ({ ...v, method: METHOD })) };
}

export async function buildNowcastSnapshot(raw: unknown, options: NowcastSnapshotOptions): Promise<ForecastSnapshot> {
  const bank = DrawBankSchema.parse(raw);
  const layout = chainOrder(bank.drawIds, bank.layerReplicates);
  const unit = bank.layerReplicates;
  const simulated = bank.seats.filter((s): s is SimulatedSeat => s.status === 'simulated');
  const unavailable = bank.seats.filter(s => s.status === 'unavailable');
  const synthetic = bank.provenance === 'synthetic-fixture';
  const asOf = options.createdAt;

  let seatLayer: ForecastSnapshot['seatLayer'];
  let mmp: ForecastSnapshot['mmp'];
  let partySeatSummaries: { partyId: string; seats: IntervalSet }[] = [];
  if (unavailable.length > 0) {
    const reason = `${unavailable.length} of ${bank.seats.length} electorates have no simulated winner; every MMP output is withheld`;
    seatLayer = { status: 'unavailable', reason };
    mmp = { status: 'unavailable', reason };
  } else if (options.mmp === null) {
    const reason = 'MMP rules version and bloc definitions are not configured';
    seatLayer = { status: 'unavailable', reason };
    mmp = { status: 'unavailable', reason };
  } else {
    const result = seatLayerSummary(bank, seatLayerConfig(bank, options.mmp), layout, options.electionId, options.mmp.hungParliament ?? null);
    seatLayer = { status: 'available', summary: result.summary };
    mmp = { status: 'available', exampleDrawAllocation: result.example };
    partySeatSummaries = result.summary.parties.map(p => ({ partyId: p.partyId, seats: p.seats }));
  }

  const config: SimulationConfig = {
    schemaVersion: 1, electionId: options.electionId, modelVersion: options.modelVersion, codeRevision: options.codeRevision,
    seed: bank.configVersion, prng: 'scipy-sobol-scrambled+numpy-pcg64 (Python draw bank)', prngVersion: `bank-schema-${bank.schemaVersion}`,
    draws: bank.draws, inputs: [{ artifactId: `nowcast-draw-bank-${bank.configVersion}`, sha256: options.bankSha256 }], governmentCombinations: [],
  };
  const electoratePredictions = simulated.map(seat => {
    const counts = new Map(seat.candidates.map(c => [c, 0]));
    seat.winners.forEach(w => counts.set(seat.candidates[w], counts.get(seat.candidates[w])! + 1));
    return {
      schemaVersion: 1 as const, id: `${options.snapshotId}:${seat.electorateId}`, electionId: options.electionId, modelVersion: options.modelVersion,
      sourceIds: [seat.source ?? 'nowcast-draw-bank'], artifactIds: [config.inputs[0].artifactId], asOf, limitations: options.limitations,
      electorateId: seat.electorateId, boundaryVersionId: options.boundaryVersionId,
      candidates: seat.candidates.map(candidateId => ({ candidateId, winProbability: counts.get(candidateId)! / bank.draws })),
    };
  });
  const evidence = options.evidence === undefined ? null : EvidenceFileSchema.parse(options.evidence);
  if (evidence) {
    const known = new Set(bank.directory.electorates.map(e => plain(e.name)));
    const unknown = [...new Set(evidence.seatPolls.map(p => p.electorateName))].filter(n => !known.has(plain(n)));
    if (unknown.length) throw new Error(`Seat polls name electorates that are not in the directory: ${unknown.join(', ')}`);
  }
  const electorateDetail = simulated.map(seat => ({
    electorateId: seat.electorateId, uncertaintyClass: seat.class,
    ...(evidence ? { evidence: seatEvidence(seat, bank.directory.electorates.find(e => e.electorateId === seat.electorateId)!.name, bank, evidence) } : {}),
    candidates: seat.candidates.map(candidateId => {
      const { mean, share } = shareIntervals(seat, candidateId);
      return { candidateId, meanShare: mean, share, winProbability: probability(seat.winners.map(w => (seat.candidates[w] === candidateId ? 1 : 0)), layout, unit) };
    }),
  }));

  return ForecastSnapshotSchema.parse({
    schemaVersion: 2, snapshotId: options.snapshotId, targetType: 'nowcast', createdAt: options.createdAt, dataCutoff: options.dataCutoff,
    modelStateAsOf: bank.modelStateAsOf, electionId: options.electionId, electionDate: options.electionDate,
    provenance: synthetic
      ? { kind: 'synthetic-fixture', label: options.syntheticLabel ?? 'Synthetic draw bank; not a nowcast' }
      : { kind: 'model', modelVersion: options.modelVersion, codeRevision: options.codeRevision, configVersion: bank.configVersion },
    directory: bank.directory,
    national: {
      partyVoteShares: bank.partyVote.groups.map((g, i) => ({ partyId: g, share: linearIntervals(bank.partyVote.shares.map(row => row[i])) })),
      basis: options.nationalBasis,
    },
    simulation: {
      schemaVersion: 1, runId: options.snapshotId, config, completedDraws: bank.draws, electoratePredictions,
      partySeatSummaries, governmentOutcomes: [], limitations: options.limitations,
    },
    unavailableElectorates: unavailable.map(s => ({ electorateId: s.electorateId, reason: s.reason })),
    electorateDetail, seatLayer, mmp, boundaries: null, limitations: options.limitations,
    ...(evidence ? { evidence: { source: evidence.source, nationalPolls: evidence.nationalPolls, trend: evidence.trend } } : {}),
  });
}
