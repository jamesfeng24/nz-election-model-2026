// Adapter that lets the seat layer satisfy the Stage53 `MmpStage` interface of the simulation pipeline.
// Not wired into any forecast: the pipeline still ships only the labelled synthetic stages.
import type { MmpAllocation } from '../../types/domain';
import { createRng } from '../simulation/prng';
import type { ElectorateWinner, MmpStage, PartyShares, PipelineInputs } from '../simulation/pipeline';
import { allocateDraw, type SeatLayerConfig } from './seatLayer';

/**
 * Winners whose electorate is listed under `expectedElectorateIds.maori` are passed as the separate Māori
 * input; all others are general winners. An exact tie at the cut-off is settled by a lot drawn from a stream
 * seeded by `lotSeed` and the draw's party shares, so the result is a pure function of the draw.
 */
export function createSeatLayerMmpStage(config: SeatLayerConfig, lotSeed = 'mmp-seat-layer-lot'): MmpStage {
  const maori = new Set(config.expectedElectorateIds?.maori ?? []);
  return {
    rulesVersion: config.rulesVersion,
    allocate(inputs: PipelineInputs, partyVotes: PartyShares, winners: ElectorateWinner[]): MmpAllocation {
      const rng = createRng(lotSeed, JSON.stringify(Object.entries(partyVotes).sort(([a], [b]) => (a < b ? -1 : 1))));
      const outcome = allocateDraw(config, {
        electionId: inputs.electionId,
        partyVoteShares: partyVotes,
        generalWinners: winners.filter(w => !maori.has(w.electorateId)),
        maoriWinners: winners.filter(w => maori.has(w.electorateId)),
      }, { uniform: () => rng.uniform() });
      return outcome.allocation;
    },
  };
}
