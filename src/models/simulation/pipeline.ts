import { z } from 'zod';
import {
  CandidateSchema, ElectorateSchema, INTERVAL_LEVELS, PartySchema, PollSchema, type IntervalSet, type MmpAllocation,
  type SimulationConfig, type SimulationResult,
} from '../../types/domain';
import { drawRng, type Rng } from './prng';

/**
 * Pipeline skeleton: polls → national draws → local party → candidate → MMP → aggregate.
 * Each arrow is an interface so real components replace the synthetic ones without changing the
 * export contract. DOM-free and JSON-serialisable for Web Worker execution.
 */
export const PipelineInputsSchema = z.object({
  schemaVersion: z.literal(1),
  electionId: z.string().min(1),
  boundaryVersionId: z.string().min(1),
  parties: z.array(PartySchema).min(1),
  polls: z.array(PollSchema),
  electorates: z.array(ElectorateSchema).min(1),
  candidates: z.array(CandidateSchema.extend({ electorateId: z.string().min(1), partyId: z.string().min(1).nullable() }).strict()),
  /** Stage parameters belong to the stage that reads them; the pipeline passes them through untouched. */
  stageParameters: z.record(z.string(), z.unknown()),
}).strict();
export type PipelineInputs = z.infer<typeof PipelineInputsSchema>;

export type PartyShares = Record<string, number>;
export type CandidateShares = Record<string, number>;
export interface ElectorateWinner { electorateId: string; partyId: string | null; candidateId: string }

export interface NationalStage { drawNational(inputs: PipelineInputs, rng: Rng): PartyShares }
export interface LocalPartyStage { drawLocal(inputs: PipelineInputs, national: PartyShares, rng: Rng): Record<string, PartyShares> }
export interface CandidateStage { drawCandidates(inputs: PipelineInputs, local: Record<string, PartyShares>, rng: Rng): Record<string, CandidateShares> }
/** Interface the MMP thread's allocator must satisfy (or be adapted to). */
export interface MmpStage {
  readonly rulesVersion: string;
  allocate(inputs: PipelineInputs, partyVotes: PartyShares, winners: ElectorateWinner[]): MmpAllocation;
}
export interface PipelineStages { national: NationalStage; localParty: LocalPartyStage; candidate: CandidateStage; mmp: MmpStage }

export type PipelineRunRequest = { type: 'run'; requestId: string; config: SimulationConfig; inputs: PipelineInputs };
export type { SimulationWorkerResponse } from '../../types/domain';

export interface PipelineOutput {
  result: SimulationResult;
  nationalShares: Record<string, IntervalSet>;
  exampleDrawAllocation: MmpAllocation | null;
}

function quantile(sorted: number[], p: number): number {
  const pos = (sorted.length - 1) * p, lo = Math.floor(pos), hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}
/** Central 50/80/90% intervals (INTERVAL_LEVELS) sharing one median; empirical quantiles of the draws. */
function intervals(values: number[], method: string): IntervalSet {
  const s = [...values].sort((x, y) => x - y);
  const median = quantile(s, 0.5);
  return INTERVAL_LEVELS.map(level => ({ lower: quantile(s, (1 - level) / 2), median, upper: quantile(s, 1 - (1 - level) / 2), level, method }));
}

export function runPipeline(
  config: SimulationConfig, inputs: PipelineInputs, stages: PipelineStages,
  options: { runId: string; asOf: string; limitations: string[]; onProgress?: (completed: number) => void } ,
): PipelineOutput {
  const partyIds = inputs.parties.map(p => p.id);
  const national: Record<string, number[]> = Object.fromEntries(partyIds.map(p => [p, []]));
  const seats: Record<string, number[]> = Object.fromEntries(partyIds.map(p => [p, []]));
  const wins: Record<string, Record<string, number>> = {};
  for (const e of inputs.electorates) wins[e.id] = Object.fromEntries(inputs.candidates.filter(c => c.electorateId === e.id).map(c => [c.id, 0]));
  const govt = config.governmentCombinations.map(() => 0);
  let example: MmpAllocation | null = null;

  for (let draw = 0; draw < config.draws; draw++) {
    const rng = drawRng(config.seed, draw);
    const nat = stages.national.drawNational(inputs, rng);
    const local = stages.localParty.drawLocal(inputs, nat, rng);
    const cand = stages.candidate.drawCandidates(inputs, local, rng);
    const winners: ElectorateWinner[] = [];
    for (const e of inputs.electorates) {
      const shares = cand[e.id];
      if (!shares) continue; // electorate without a candidate model contributes no winner
      let best: string | null = null;
      for (const [cid, v] of Object.entries(shares)) if (best === null || v > shares[best] || (v === shares[best] && cid < best)) best = cid;
      if (best === null) continue;
      wins[e.id][best] += 1;
      winners.push({ electorateId: e.id, candidateId: best, partyId: inputs.candidates.find(c => c.id === best)?.partyId ?? null });
    }
    const alloc = stages.mmp.allocate(inputs, nat, winners);
    if (draw === 0) example = alloc;
    for (const p of partyIds) {
      national[p].push(nat[p] ?? 0);
      seats[p].push(alloc.parties.find(q => q.partyId === p)?.totalSeats ?? 0);
    }
    config.governmentCombinations.forEach((g, i) => {
      if (g.partyIds.reduce((sum, p) => sum + (alloc.parties.find(q => q.partyId === p)?.totalSeats ?? 0), 0) >= g.requiredSeats) govt[i]++;
    });
    options.onProgress?.(draw + 1);
  }

  const electoratePredictions = inputs.electorates.flatMap(e => {
    const tally = wins[e.id];
    const entries = Object.entries(tally);
    if (entries.length === 0) return [];
    // Sorted by id for a stable file; probabilities are empirical winner frequencies of the draws.
    const candidates = entries.sort(([a], [b]) => (a < b ? -1 : 1)).map(([candidateId, n]) => ({ candidateId, winProbability: n / config.draws }));
    return [{
      schemaVersion: 1 as const, id: `${options.runId}:${e.id}`, electionId: config.electionId, modelVersion: config.modelVersion,
      sourceIds: ['synthetic-fixture'], artifactIds: config.inputs.map(i => i.artifactId), asOf: options.asOf, limitations: options.limitations,
      electorateId: e.id, boundaryVersionId: inputs.boundaryVersionId, candidates,
    }];
  });
  const method = 'empirical-quantile';
  return {
    result: {
      schemaVersion: 1, runId: options.runId, config, completedDraws: config.draws, electoratePredictions,
      partySeatSummaries: partyIds.map(partyId => ({ partyId, seats: intervals(seats[partyId], method) })),
      governmentOutcomes: config.governmentCombinations.map((g, i) => ({ combinationId: g.id, probability: govt[i] / config.draws })),
      limitations: options.limitations,
    },
    nationalShares: Object.fromEntries(partyIds.map(p => [p, intervals(national[p], method)])),
    exampleDrawAllocation: example,
  };
}
