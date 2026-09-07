import { describe, expect, it } from 'vitest';
import {
  CandidateStatusSchema, PartyVoteResultSchema, PollSchema, SplitVoteMatrixSchema,
  ModelPredictionSchema, SeatPredictionSchema, MmpAllocationSchema, SimulationConfigSchema,
} from './domain';

// Synthetic structural fixtures only: no real parties, candidates or election observations.
const sourced = { schemaVersion: 1, id: 'synthetic', sourceIds: ['synthetic-source'] };
const status = { ...sourced, candidateId: 'synthetic-person', electionId: 'synthetic-election',
  electorateId: 'synthetic-seat', boundaryVersionId: 'synthetic-boundary', partyId: null,
  status: 'first-term-incumbent', isPartyLeader: true, priorElectorateTerms: 1,
  replacesCandidateId: null, classificationReason: 'Synthetic test history' };
const poll = { ...sourced, pollsterId: 'synthetic-pollster', fieldworkStart: '2026-01-01',
  fieldworkEnd: '2026-01-02', publishedOn: '2026-01-03', sampleSize: null,
  population: 'Synthetic adults', mode: 'Synthetic', voteType: 'party', electorateId: null,
  boundaryVersionId: null, denominator: 'Synthetic decided respondents', undecidedShare: null,
  results: [{ choiceId: 'synthetic-party', share: 0.4 }], limitations: ['Not real data'] };
const matrix = { ...sourced, electionId: 'synthetic-election', electorateId: 'synthetic-seat',
  boundaryVersionId: 'synthetic-boundary',
  partyCategories: [{ id: 'row', partyId: 'synthetic-party', label: 'Test row' }],
  candidateCategories: [{ id: 'col', candidateId: 'synthetic-person', label: 'Test column' }],
  cells: [{ partyCategoryId: 'row', candidateCategoryId: 'col', count: 2 }],
  denominator: 'Synthetic paired ballots', totalBallots: 2, completeness: 'complete', limitations: [] };
const prediction = { ...sourced, electionId: 'synthetic-election', modelVersion: 'test-only',
  artifactIds: ['test-artifact'], asOf: '2026-01-01T00:00:00Z', limitations: ['Not a forecast'] };

describe('domain contracts with synthetic evidence', () => {
  it('keeps leadership orthogonal to candidate history', () => {
    expect(CandidateStatusSchema.parse(status).isPartyLeader).toBe(true);
  });
  it('rejects a former multi-term member classified as first-term', () => {
    expect(CandidateStatusSchema.safeParse({ ...status, priorElectorateTerms: 2 }).success).toBe(false);
  });
  it('allows evidenced returning incumbency without a freshman classification', () => {
    expect(CandidateStatusSchema.safeParse({ ...status, status: 'returning-former-incumbent', priorElectorateTerms: 2 }).success).toBe(true);
  });
  it('requires no electorate for list-only candidacy', () => {
    expect(CandidateStatusSchema.safeParse({ ...status, status: 'list-only-candidate' }).success).toBe(false);
  });
  it('accepts partial polls but rejects invalid chronology or percentage units', () => {
    expect(PollSchema.safeParse(poll).success).toBe(true);
    expect(PollSchema.safeParse({ ...poll, fieldworkEnd: '2025-12-31' }).success).toBe(false);
    expect(PollSchema.safeParse({ ...poll, results: [{ choiceId: 'test', share: 40 }] }).success).toBe(false);
  });
  it('does not equate unknown vote counts with zero', () => {
    const result = { ...sourced, electionId: 'test', electorateId: 'test', boundaryVersionId: 'test',
      partyId: 'test', votes: null, totalValidVotes: 5, basis: 'official', missingReason: null };
    expect(PartyVoteResultSchema.safeParse(result).success).toBe(false);
    expect(PartyVoteResultSchema.safeParse({ ...result, missingReason: 'Suppressed in synthetic source' }).success).toBe(true);
    expect(PartyVoteResultSchema.safeParse({ ...result, votes: 0 }).success).toBe(true);
    expect(PartyVoteResultSchema.safeParse({ ...result, votes: 6 }).success).toBe(false);
  });
  it('validates matrix coverage, references and denominators', () => {
    expect(SplitVoteMatrixSchema.safeParse(matrix).success).toBe(true);
    expect(SplitVoteMatrixSchema.safeParse({ ...matrix, totalBallots: 3 }).success).toBe(false);
    expect(SplitVoteMatrixSchema.safeParse({ ...matrix, cells: [matrix.cells[0], matrix.cells[0]] }).success).toBe(false);
    expect(SplitVoteMatrixSchema.safeParse({ ...matrix, cells: [{ ...matrix.cells[0], candidateCategoryId: 'absent' }] }).success).toBe(false);
  });
  it('requires bounded ordered uncertainty intervals', () => {
    const model = { ...prediction, estimator: 'elasticity', target: { kind: 'national-party', partyId: 'test' },
      unit: 'proportion', estimate: { lower: 0.2, median: 0.3, upper: 0.4, level: 0.9, method: 'Synthetic' } };
    expect(ModelPredictionSchema.safeParse(model).success).toBe(true);
    expect(ModelPredictionSchema.safeParse({ ...model, estimate: { ...model.estimate, upper: 0.1 } }).success).toBe(false);
  });
  it('requires a complete unique winner probability distribution', () => {
    const seat = { ...prediction, electorateId: 'test', boundaryVersionId: 'test', candidates: [{ candidateId: 'test', winProbability: 1 }] };
    expect(SeatPredictionSchema.safeParse(seat).success).toBe(true);
    expect(SeatPredictionSchema.safeParse({ ...seat, candidates: [{ candidateId: 'test', winProbability: 0.5 }] }).success).toBe(false);
  });
  it('checks seat arithmetic without implementing allocation rules', () => {
    const allocation = { schemaVersion: 1, electionId: 'test', rulesVersion: 'synthetic', rulesSourceIds: ['test'],
      nominalSeats: 2, parliamentSize: 2, overhangSeats: 0, unfilledSeats: 0, independentElectorateSeats: 0,
      parties: [{ partyId: 'test', qualified: true, qualificationReason: 'Synthetic only', electorateSeats: 1, listSeats: 1, totalSeats: 2 }] };
    expect(MmpAllocationSchema.safeParse(allocation).success).toBe(true);
    expect(MmpAllocationSchema.safeParse({ ...allocation, parliamentSize: 3 }).success).toBe(false);
  });
  it('requires reproducibility metadata for serializable run configuration', () => {
    const config = { schemaVersion: 1, electionId: 'test', modelVersion: 'test', codeRevision: 'test',
      seed: 'test-seed', prng: 'not-implemented', prngVersion: 'test', draws: 2,
      inputs: [{ artifactId: 'test', sha256: 'a'.repeat(64) }], governmentCombinations: [] };
    expect(SimulationConfigSchema.parse(JSON.parse(JSON.stringify(config)))).toEqual(config);
    expect(SimulationConfigSchema.safeParse({ ...config, seed: '' }).success).toBe(false);
  });
});
