import type { MmpAllocation } from '../../types/domain';
import type {
  CandidateStage, ElectorateWinner, LocalPartyStage, MmpStage, NationalStage, PartyShares, PipelineInputs, PipelineStages,
} from './pipeline';

/**
 * SYNTHETIC PLACEHOLDER STAGES. They exist to exercise the pipeline and export contract on labelled
 * fixtures. They are not project models, are not fitted, and their output must never be presented as
 * a forecast. Real components implement the same interfaces.
 */
export interface SyntheticParameters {
  nationalLogSd: number;
  localLogSd: number;
  candidateLogSd: number;
  /** log-share offset per electorate and party. */
  electorateLean: Record<string, Record<string, number>>;
  independentLogShare: number;
  nominalSeats: number;
  threshold: number;
}

export function syntheticParameters(inputs: PipelineInputs): SyntheticParameters {
  return inputs.stageParameters['synthetic'] as SyntheticParameters;
}

function normalise(raw: PartyShares): PartyShares {
  const total = Object.values(raw).reduce((a, b) => a + b, 0);
  return Object.fromEntries(Object.entries(raw).map(([k, v]) => [k, v / total]));
}

export const syntheticNational: NationalStage = {
  drawNational(inputs, rng) {
    const sd = syntheticParameters(inputs).nationalLogSd;
    const sums: PartyShares = Object.fromEntries(inputs.parties.map(p => [p.id, 0]));
    const used = inputs.polls.filter(p => p.voteType === 'party' && p.electorateId === null);
    for (const poll of used) for (const r of poll.results) if (r.choiceId in sums) sums[r.choiceId] += r.share / used.length;
    return normalise(Object.fromEntries(Object.entries(sums).map(([k, v]) => [k, Math.max(v, 1e-6) * Math.exp(sd * rng.normal())])));
  },
};

export const syntheticLocalParty: LocalPartyStage = {
  drawLocal(inputs, national, rng) {
    const { localLogSd, electorateLean } = syntheticParameters(inputs);
    return Object.fromEntries(inputs.electorates.map(e => [e.id, normalise(Object.fromEntries(
      Object.entries(national).map(([p, v]) => [p, v * Math.exp((electorateLean[e.id]?.[p] ?? 0) + localLogSd * rng.normal())])))]));
  },
};

export const syntheticCandidate: CandidateStage = {
  drawCandidates(inputs, local, rng) {
    const { candidateLogSd, independentLogShare } = syntheticParameters(inputs);
    const out: Record<string, Record<string, number>> = {};
    for (const e of inputs.electorates) {
      const cs = inputs.candidates.filter(c => c.electorateId === e.id);
      if (cs.length === 0) continue;
      const raw = Object.fromEntries(cs.map(c => [c.id, (c.partyId === null ? Math.exp(independentLogShare) : local[e.id][c.partyId] ?? 1e-6) * Math.exp(candidateLogSd * rng.normal())]));
      out[e.id] = normalise(raw);
    }
    return out;
  },
};

export const SYNTHETIC_RULES_VERSION = 'UNVERIFIED-PLACEHOLDER-synthetic-only';

/**
 * Placeholder seat allocation: NOT the NZ electoral rules, which are being verified separately.
 * Threshold, Sainte-Laguë and the overhang treatment are stand-ins so seat accounting can be exercised.
 */
export const syntheticMmp: MmpStage = {
  rulesVersion: SYNTHETIC_RULES_VERSION,
  allocate(inputs: PipelineInputs, partyVotes: PartyShares, winners: ElectorateWinner[]): MmpAllocation {
    const { nominalSeats, threshold } = syntheticParameters(inputs);
    const elec: Record<string, number> = {};
    let independents = 0;
    for (const w of winners) { if (w.partyId === null) independents++; else elec[w.partyId] = (elec[w.partyId] ?? 0) + 1; }
    const qualified = inputs.parties.map(p => p.id).filter(p => (partyVotes[p] ?? 0) >= threshold || (elec[p] ?? 0) > 0);
    const listPool = nominalSeats - independents;
    const ent: Record<string, number> = Object.fromEntries(qualified.map(p => [p, 0]));
    for (let s = 0; s < listPool && qualified.length > 0; s++) {
      let best = qualified[0];
      for (const p of qualified) if (partyVotes[p] / (2 * ent[p] + 1) > partyVotes[best] / (2 * ent[best] + 1)) best = p;
      ent[best]++;
    }
    let overhang = 0;
    const parties = inputs.parties.map(({ id }) => {
      const q = qualified.includes(id), e = elec[id] ?? 0, n = q ? ent[id] : 0, total = Math.max(n, e);
      overhang += total - n;
      return { partyId: id, qualified: q, qualificationReason: q ? ((partyVotes[id] ?? 0) >= threshold ? 'placeholder-threshold' : 'placeholder-electorate-win') : 'below-placeholder-threshold', electorateSeats: e, listSeats: total - e, totalSeats: total };
    });
    return {
      schemaVersion: 1, electionId: inputs.electionId, rulesVersion: SYNTHETIC_RULES_VERSION,
      rulesSourceIds: ['synthetic-fixture'], nominalSeats, parliamentSize: nominalSeats + overhang, overhangSeats: overhang,
      unfilledSeats: 0, parties, independentElectorateSeats: independents,
    };
  },
};

export const syntheticStages: PipelineStages = { national: syntheticNational, localParty: syntheticLocalParty, candidate: syntheticCandidate, mmp: syntheticMmp };
