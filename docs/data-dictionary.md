# Data dictionary — draft exchange contracts v1

These contracts describe future records, not real observations. Runtime Zod schemas and inferred TypeScript types are in `src/types/domain.ts`; provenance schemas remain in `src/types/contracts.ts`. No model or electoral rule is implemented by schema validation.

## Conventions

Records are strict objects. IDs are opaque, nonempty, case-sensitive strings; relationships use IDs, never display-name matching. Most evidence records carry `schemaVersion: 1`, `id` and nonempty unique `sourceIds`. Dates are ISO YYYY-MM-DD; timestamps include a timezone. Boundary-sensitive observations require both electorate and boundary-version IDs. A new boundary vintage requires an explicit crosswalk, never a name-only join.

Shares and probabilities use proportions from 0 to 1, not percentages. Counts are nonnegative safe integers. Unknown counts use null plus a reason where required; zero means observed zero. Poll sample size is positive or null. A null party affiliation denotes an independent candidate; unresolved affiliation must be resolved before publishing a candidate result/status record or documented as a schema limitation. Null dates or leadership flags mean unknown/not established. No silent zero filling is permitted.

## Entity contracts

| Type | Fields and meaning |
| --- | --- |
| Party | name, abbreviation; relatedPartyIds are documented identity relationships only, never behavioural carryover; validFrom/validTo describe identity validity |
| Pollster | name and nullable methodologyUrl |
| Poll | pollsterId; fieldworkStart/end and publishedOn; sampleSize; population and mode; voteType; optional local electorate/boundary pair; denominator text; undecidedShare; results of choiceId/share; limitations |
| Election | name, nullable electionDate, general/by-election kind, boundaryVersionId, rulesSourceIds, nullable expectedElectorateCount; no built-in 2026 count |
| ElectorateBoundaryVersion | label, effectiveFrom/to, optional geometryArtifactId and coordinateReferenceSystem; geometry is exported separately as GeoJSON |
| Electorate | name, boundaryVersionId, general/maori kind, predecessorIds (relationships, not allocation weights) |
| Candidate | persistent person identity and name; election-specific party/status lives in results and CandidateStatus |
| CandidateStatus | candidateId, electionId, optional electorate/boundary pair, partyId, status, isPartyLeader, priorElectorateTerms, replacesCandidateId, classificationReason |
| CandidateElectionResult | election/electorate/boundary IDs, candidateId, partyId, votes, totalValidVotes, basis official/reconstructed, missingReason and nullable elected |
| PartyVoteResult | election/electorate/boundary IDs, partyId, votes, totalValidVotes, basis official/reconstructed and missingReason |
| SplitVoteMatrix | election/electorate/boundary IDs; explicit partyCategories and candidateCategories; cells reference category IDs with nullable count; denominator, totalBallots, completeness and limitations |
| ModelPrediction | ID, electionId, modelVersion, sourceIds, artifactIds, asOf, limitations; estimator; national-party/local-party/local-candidate target; proportion unit and estimate interval |
| SeatPrediction | same prediction metadata; electorate/boundary IDs; all candidates' winProbability values, unique and summing to 1 within 1e-6 |
| MmpAllocation | electionId, rulesVersion/rulesSourceIds, nominalSeats, parliamentSize, overhangSeats, unfilledSeats; party rows with qualification reason and electorate/list/total seats; independentElectorateSeats |
| SimulationResult | runId, versioned config, completedDraws, electoratePredictions, partySeatSummaries, governmentOutcomes by combinationId, limitations |

Poll choiceId refers to a party for party-vote polls and candidate for candidate-vote polls. Denominator must say whether undecideds, others and nonrespondents were excluded. Individual reported choices may be incomplete; a 0.01 total rounding tolerance is allowed but does not normalize results. Undecided share is not automatically added because the source may use a different denominator.

Official vote records use the appropriate local valid party-vote or candidate-vote total, never the other ballot's denominator. The initial result contract supports integer reconstructed outputs only; fractional geographic estimates and reconstruction intervals need a separately reviewed contract before use. Do not silently round to fit the schema.

Matrix category IDs permit invalid, other and withheld categories. Their nullable partyId/candidateId indicates a non-party/non-candidate category, described by label. Rows are party choices; columns are candidate choices. Complete matrices require every row/column pair and exact total reconciliation; partial matrices do not imply that omitted cells are zero. No independence assumption is made from a matrix shape.

## Candidate status

Allowed statuses: established-continuing-incumbent, first-term-incumbent, returning-former-incumbent, replacement-candidate, returning-challenger, completely-new-candidate, list-only-candidate, unknown. Leadership is a separate nullable flag because a leader can also occupy any relevant tenure category.

`priorElectorateTerms` counts evidenced electorate terms before the target election, including the term ending at that election and earlier interrupted spells. First-term requires exactly one such term, but that count alone does not establish first-term status: classification must also verify continuity/history under the statistical specification. Completely new requires zero prior terms and no earlier candidacy; candidacy history must be validated against sources. Unknown history must not trigger a bonus. Returning/former incumbents remain distinct from freshman incumbents. ClassificationReason records evidence and interpretation. List-only forbids a current electorate. A replacement link is nullable if evidence is incomplete; do not invent the outgoing candidate.

## Uncertainty, simulation and accounting

Intervals contain finite lower/median/upper, an explicit level between 0 and 1 and method description. Model vote-share intervals must be bounded by 0 and 1. Seat-summary intervals express seat counts (potentially fractional quantiles), not probabilities.

SimulationConfig records election/model/code revision, seed, PRNG name and version, positive draws, input artifact IDs and SHA-256 hashes. Government combinations name unique party sets and an explicit requiredSeats threshold; no scenario is created by default. Future varying-Parliament majority scenarios need a reviewed dynamic-threshold contract; the present field only represents fixed thresholds. No political coalition is assumed.

MmpAllocation performs structural accounting only: party total equals electorate plus list; filled seats plus unfilled seats equal Parliament size; Parliament size equals nominal plus overhang. Here parliamentSize includes unfilled positions; verify/revise conventions against official rules before implementation. This is not qualification or Sainte-Laguë logic and does not identify actual list MPs. List ordering/eligibility schemas are deferred until source review.

SimulationWorkerRequest/Response are plain TypeScript message unions (run, progress, result, error) keyed by requestId. No worker or model runs yet. The future worker must validate messages at its boundary and resolve checked input artifacts without relying on UI state.

## Provenance and limitations

SourceRegistrySchema is a strict version-1 registry with unique source IDs. SourceRecord fields are defined in [DATA_SOURCES.md](../DATA_SOURCES.md). rawPath is a repository-relative materialization location; processingScript is null until a script exists. SHA-256 refers to unchanged bytes. `scripts/validate/source_files.py` checks local containment, file existence and checksums; it does not download missing inputs. Full metadata validation is exercised by Vitest.

Availability<T> distinguishes unavailable/reason from available/value/sourceIds; it is not yet a runtime result wrapper. Domain schemas do not verify external authenticity, foreign-key existence, electoral legality, whole-dataset completeness or calibration. Future dataset validators must enforce joins, source references, boundary consistency, semantic dates, scenario references and election coverage before publication. No domain dataset exists to validate now.

Breaking changes require explicit versioning, migration guidance and tests. Do not treat this provisional contract as permission to force evidence into an unsuitable representation.
