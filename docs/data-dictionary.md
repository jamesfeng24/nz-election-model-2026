# Data dictionary — draft exchange contracts v1

The Stage 1 contracts below describe intended model records. Actual Stage 2 historical exports have a separate contract documented at the end of this file. Runtime Zod schemas and inferred TypeScript types are in `src/types/domain.ts`; provenance schemas remain in `src/types/contracts.ts`. No model or electoral rule is implemented by schema validation.

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

Availability<T> distinguishes unavailable/reason from available/value/sourceIds; it is not yet a runtime result wrapper. Domain schemas do not verify external authenticity, foreign-key existence, electoral legality, whole-dataset completeness or calibration. Future dataset validators must enforce joins, source references, boundary consistency, semantic dates, scenario references and election coverage before publication. Historical exports now exist under the separate ingestion contract below; they are not instances of every draft model schema.

Breaking changes require explicit versioning, migration guidance and tests. Do not treat this provisional contract as permission to force evidence into an unsuitable representation.

## Historical ingestion export v1 — implemented for 2008 and 2011

These are deterministic JSON preparation outputs, not forecasts and not yet wired into the website or Stage 1 Zod model schemas. `schemaVersion` is 1; the processor is the executable validation contract. Changes require review and regeneration.

| Output/field | Meaning |
| --- | --- |
| elections/YEAR.json | year, general `electorates`, all-electorate `nationalControls`, input `sourceIds` |
| electorate | election-local id/electionId, sourceElectorateNumber, source name, kind, historical boundaryVersionId, validPartyVotes, validCandidateVotes, partyBallot/candidateBallot, parties/candidates, winnerCandidateId, majority and sourceIds |
| party record | sourceHeader, partyName, comparison partyKey, integer votes, calculated share of local valid party votes |
| candidate record | full source name/party, integer votes, sourceShare and calculated share of local valid candidate votes, elected flag, occurrence id, partyKey, nameMatchKey, personId:null |
| ballot record | ordinary/special valid and informal counts, ordinary/special disallowed counts, validVotes, informalVotes, votesCast, enrolled, electoralPopulation, reportedTurnoutPercent, source name/scope |
| nationalControls | separate party/candidate general, Māori and national summaries; official national party and candidate-party totals with provenance |
| split-votes/YEAR.json | year and matrices; each matrix has id, electorateId, sourceIds, sourceElectorateLabel, encoding, countAvailability, rows |
| matrix row | partyLabel, exact totalPartyVotes, cells, reportedTotalPercent; final row is an overall total, not another party observation |
| matrix cell | source candidateLabel, category (candidate/informal/party-vote-only), nullable candidateId, count:null, reportedPercent (0–100 or null) |
| YEAR-validation.json | coverage counts, national totals, checks, labelMappings, discrepancies and limitations |

All `share` and `sourceShare` fields are proportions (0–1). Fields ending `Percent` are percentages (0–100). Split percentages have two-decimal source rounding; exact joint counts are unavailable, never silently estimated. Split denominator is valid plus informal party votes, excluding disallowed ballots; it differs from valid party/candidate share denominators. Party-vote-only accounts for absent candidate votes. Zero means an observed zero, null means unavailable. Missing required count inputs fail processing.

Candidate IDs refer to occurrences, not persons. Comparison keys remove accents/punctuation only for joins while original Unicode labels remain. Local name variants are explicitly recorded in the report; keys must never establish cross-election identity. Boundary version labels describe the historical publication only, with no geometry or crosswalk claim. Māori inputs are retained raw for national reconciliation; general-electorate output coverage is deliberate.

### 2011 additions and source precision

The shared election/local-matrix fields are unchanged. Party keys remain canonical normalized source-name identifiers within the dataset, not political-continuity claims. Candidate occurrence IDs are election-local; full candidate names are in election records and original abbreviated/common labels in split cells, linked by candidateId. Eight alternate-surname mappings are explicit in the validation report. Unicode source names such as Māngere and Māori Party are preserved.

The 2011 split export additionally contains `aggregateMatrices` keyed general/maori/national, each with sourceIds and the same percentage-row representation; here candidateLabel names a destination **party/category**, not an individual candidate. `officialSplitSummary` contains sourceIds, limitations and rows: partyLabel, totalPartyVotes, nonSplitCandidateVotes, reportedNonSplitPercent, splitCandidateVotes, reportedSplitPercent, isTotal. Counts in this summary are published exact aggregate counts, never inferred local joint counts. Its final total row is not an extra observation. The informal-party non-split source convention is explicitly flagged. `sourcePeculiarities` is an additional 2011 validation-report field. These additive ingestion fields do not change 2008 exports or imply model-facing TypeScript compatibility.
