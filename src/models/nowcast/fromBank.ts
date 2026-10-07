import { INTERVAL_LEVELS, type IntervalSet, type MmpAllocation, type SimulationConfig } from '../../types/domain';
import { ForecastSnapshotSchema, type ForecastSnapshot } from '../../types/export';
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
  mmp: { rulesVersion: string; rulesSourceIds: string[]; blocs: BlocDefinition[] } | null;
  nationalBasis: string;
  limitations: string[];
  syntheticLabel?: string;
}

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

function seatLayerSummary(bank: DrawBank, config: SeatLayerConfig, layout: ChainOrder, electionId: string) {
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
    const result = seatLayerSummary(bank, seatLayerConfig(bank, options.mmp), layout, options.electionId);
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
  const electorateDetail = simulated.map(seat => ({
    electorateId: seat.electorateId, uncertaintyClass: seat.class,
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
    calibrationStatus: 'uncalibrated',
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
  });
}
