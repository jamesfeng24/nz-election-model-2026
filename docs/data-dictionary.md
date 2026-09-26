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

## Historical ingestion export v1 — implemented for 2008, 2011 and 2014

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

### 2014 entries and split-party grouping

Existing v1 election and split fields are reused. Coverage is 64 general electorates and 15 party-vote choices per electorate. Source electorate numbers are publication-specific; they cannot be joined across years without boundary evidence. Local matrix countAvailability records rounded percentages and count:null. Aggregate summary counts remain exact only at the published aggregate level.

The split export adds `partyGrouping`: sourceCandidateParties [Internet Party, MANA Movement], splitReportParty Internet MANA, and a scope explanation. The validation report exposes the same record as `splitPartyGrouping`. This applies only to 2014 split joins/controls. Candidate `party`, `partyKey`, and national candidate-party controls retain their original affiliations; the grouping does not merge party identities or estimate behaviour.

Eight labelMappings preserve original split labels and official candidate-table names, including the Kaikōura spelling difference and Wellington Central independent-name variant. Exact raw labels are retained in immutable CSVs; display fields follow the existing NFC/trim parsing conventions. Unknown cross-election personId stays null. The 337 informal-party non-split source convention is recorded in sourcePeculiarities and officialSplitSummary.limitations. No prior-year processed schema/data changed.

## Integrated 2008–2014 panel (Stage 2D, schemaVersion 1)

`data/processed/historical/2008-2014/` contains five record containers (`schemaVersion`, `years`, `records`) and `manifest.json`. It is a lossless projection of the committed per-year historical contracts, not an instance of the provisional model-facing TypeScript schemas.

| File | Record/key | Representation |
| --- | --- | --- |
| electorate metadata: `electorates.json` | `id`; year + official electorate number | Original metadata except nested parties/candidates; includes boundary version, both ballot denominators/turnout, winner, majority and source IDs. |
| `party-votes.json` | `(year, electorateId, partyKey)` | Original party fields plus year, electionId, electorateId, sourceIds and canonicalPartyId. |
| `candidate-votes.json` | `(year, id)` | Original candidate fields plus year, electionId, electorateId, sourceIds and canonicalPartyId. IDs identify occurrences, not people. |
| `split-votes.json` | `(year, electorateId)` | Original full matrices unchanged, including source labels, candidate references, countAvailability and rounded percentages. |
| `election-controls.json` | `year` | Original nationalControls, sourceIds, perYearValidation (including name mappings), aggregateMatrices, officialSplitSummary, partyGrouping and aggregateSplitAvailability. |
| `manifest.json` | input/output paths | Nine per-year input SHA-256 hashes, five panel output hashes, counts, reviewed canonical aliases and evidence URL. Manifest does not hash itself. |

Safe invariants for future stages:

- Every top-level observation has an explicit year; nested split observations inherit the enclosing matrix's year/electorate. There are exactly 63/63/64 general electorates and 190 matrices; year-specific geography is not harmonized.
- `partyKey` is the existing source-name comparison key. `canonicalPartyId` is a separate historical party identifier: conservativeparty → conservative; mana → manamovement; other keys unchanged. Independent has null canonicalPartyId because it is not one political party. Original `partyName`/`party`, headers and split labels are retained. No other organizational equivalence is inferred.
- Raw election controls and split reports intentionally retain their published labels rather than receiving a false uniform affiliation. The 2014 `partyGrouping` applies only to split-report joins. Internet MANA never replaces Internet Party/MANA Movement candidate affiliations.
- Candidate `personId` remains null; source-name comparison keys are not person IDs. Preserved within-year name mappings do not establish cross-year identity. Electorate IDs also must not be treated as cross-year continuity identifiers.
- Vote counts are nonnegative integers. Party/candidate `share` is a fraction from its own valid-vote denominator. Source `sourceShare` is retained for candidates. Party/candidate denominators are not interchangeable.
- Split `reportedPercent` is percentage points (0–100), published to two decimals; local `count` is null, never reconstructed. Rounding tolerance is 0.005 percentage points per cell; existing per-year validators apply the corresponding row/weighted-column bounds. Split rows include informal party votes but exclude disallowed ballots. The final total row is a control, not another source party.
- Exact aggregate split/non-split summary counts remain separately identified and do not imply exact local joint counts. Null and zero remain distinct. For 2008, aggregateSplitAvailability is `not-collected` and aggregate fields are null; this is not a claim that the official source lacks such data. For 2011/2014 it is `preserved`.
- Primary records are general electorates. General/Māori/national controls preserve supporting scope; detailed Māori candidate outputs were not added. No overall national total should be equated to the general-only record sum.
- All source IDs resolve through the unchanged registry. Per-year outputs and their labels/precision are unchanged by integration; the manifest identifies their exact bytes.

## 2017 modern publication adapter

The 2017 per-election exports retain the historical electorate/candidate/party shape, without extending the 2008–2014 panel. General records: 64 electorates, 431 candidates, 1,024 party observations. Supporting Māori evidence remains in raw files and general/Māori/national controls.

- Candidate `reportedPercent` preserves the published 0–100 value; `sourceShare` is that rounded value divided by 100; `share` is independently calculated from valid candidate votes. Unlike old source files, the 2017 candidate footer supplies percentages rather than fractions.
- Ballot `reportedInformalPercent` uses valid plus informal votes. Candidate-ballot `reportedWinnerPercentOfVotesCast` uses all votes cast, with null for aggregate rows. Turnout percentages use the enrolled denominator and two-decimal rounding tolerance.
- `sourceDisclosureNotes` retains nonnumeric source disclosure notes; `votingPlaceRowsValidated` counts numeric rows reconciled to official totals, not geocoded or residential observations.
- National party controls preserve `sourceGroup`, published zero party votes for candidate-only affiliations, `candidateNominations` and reported party/candidate percentages. Missing values are never substituted with zero.
- Split `precision` records rounded-percentage representation, decimalPlaces 2, percentageUnit percent and exactJointCountsAvailable false. Exact national summary counts remain separate. No candidate aliases or cross-year identities are asserted; personId stays null.

## 2020 modern export additions

The shared modern contract also covers 2020: 65 general electorates, 561 candidates and 1,105 party observations. Election year, official numbering and as-published boundary IDs are distinct from 2017. No cross-election identity or geography is inferred.

2020 split exports add `supportingMatrices` (one Māori local matrix, distinct from the 65 primary matrices) and `aggregateAffiliationMappings`: sourceAffiliation, aggregateSplitColumn, scope, evidence basis and sourceIds. NZ Public Party → Advance NZ applies only to aggregate split controls; exact candidate affiliations and local labels are untouched. This is an explicitly recorded inference about report grouping, not political-party canonicalization. Matrix precision, null exact joint counts and separate exact summary retain the 2017 meanings.

## 2023 cancellation and publication-discrepancy additions

2023 electorate `candidateContestStatus` is `held` or `cancelled`; earlier exports retain their existing bytes. Cancelled records preserve source nomination votes/percentages as evidence, but `winnerCandidateId`, `majority`, candidate `share`, `sourceShare` and `elected` are null. Port Waikato's valid-party denominator remains substantive; its valid-candidate denominator is the published zero, never used to produce a share. `personId` remains null everywhere.

Cancelled split tables have `behaviouralEvidence: false`, `unallocatedPartyVotes` and source status. Aggregate `cancelledContestAllocation` records included denominator mass, not an observed destination allocation. `officialSplitSummary.cancelledContestConvention` distinguishes published residual split counts from wholly behavioural observations. `sourceRows` preserve complementary overall-summary rows including blanks; aggregate affiliation mappings and party-label joins are evidence-local.

`sourceDiscrepancies` (split output) and `discrepancies` (validation output) contain stable assertion IDs, provenance, exact rational `leftInterval`/`rightInterval` endpoints and `minimumGapVotes`. They are feasibility enclosures, not reconstructed joint counts. `splitStatus: validated-with-source-discrepancies` means the known source inconsistencies remain unresolved and visible. An unknown or changed discrepancy fails. See `docs/2023-split-discrepancy.md`; do not normalize these observations to make them appear reconciled.

## Full 2008–2023 integrated panel — Stage 3D

The existing five JSON record families now live under `data/processed/historical/2008-2023/`, with `manifest.json`. This replaces the 2008-2014 directory; no parallel format is introduced. Schema version remains 1 and years are exactly 2008/2011/2014/2017/2020/2023. All original source fields survive lossless projection. Totals: 384 electorate-years, 6,210 party records, 2,833 candidate occurrences and 384 local split publications (383 ordinary, one cancelled).

Electorate/election/occurrence IDs are election-local; each boundaryVersionId is historical-election-YEAR-as-published. Equal names across years do not assert geographic equality. Candidate personId remains null. Missing candidateContestStatus in pre-2023 records means held; the 2023 field explicitly represents held/cancelled. Cancelled shares, winner, majority and elected status remain null while source nomination zeros and substantive party votes remain intact.

CanonicalPartyId is an additional conservative integration key; source partyKey, labels and affiliations are unchanged. Rename evidence is versioned in panel_config.py. Alliance/aggregate grouping mappings remain scoped to their reports; they do not replace affiliations. Source-local abbreviated labels are not new cross-year aliases.

Election-controls preserves nationalControls, sourceIds, perYearValidation, aggregate availability and every extra split layer present in a year, including supportingMatrices, aggregateAffiliationMappings, sourceDiscrepancies and cancellation/summary conventions. Absent 2008 aggregates and summary remain null/not-collected. Local exact count stays null; existing precision metadata and known 2023 inconsistencies survive unchanged. Manifest discrepancies and knownSourceDiscrepancies carry the same 21 documented assertions, not new failures or corrections.

The input contract pins 18 processed hashes. The manifest hashes five outputs and integration code/configuration, reports counts and carries old-slice compatibility hashes. Every build reconstructs the original 2008–2014 content envelopes and legacy manifest byte-for-byte. These invariants authorize structural use of evidence, not model fitting, constant-boundary assumptions or candidate-person links.

## Boundary-transition feasible crosswalk (Stage 4)

`data/processed/boundaries/2023-2026/crosswalk.json` is a separate synthetic reconstruction contract, not observed election results. Source/target codes refer to explicit boundary versions in its transition configuration; general and Māori scopes are separate. Each edge preserves a meshblock count, suppression count, controlled population lower/upper bounds, exact rational outgoing weight bounds, and null point weight unless uniquely identified. Population belongs to the 2023 Census electoral-population universe, not a source election turnout denominator.

The `constraints` object is essential: target population sums equal published controls; source populations equal outgoing edge sums; each weight is edge/source population. Marginal intervals cannot be selected independently. `nominalAllocation` is null. Tests construct feasible witnesses for every weight endpoint and verify source conservation, rather than claiming that endpoint sums are a point matrix.

Target metadata records official change/rename status, reverse predecessor composition, guaranteed dominant predecessor when identifiable, dominant share bounds, non-dominant population share, positive predecessor count bounds and effective predecessor count bounds. Effective count is `(sum population)^2 / sum(population^2)`. Non-dominant share measures predecessor mixing, not residential migration. Bounds are sharp over integer partitions under the stated target controls; they are not confidence intervals. The two suppressed technical exceptions retain possible nonzero mass despite Schedule B's unchanged designation. No population is imputed or discarded.

### Stage4 population feasible sets and notional party diagnostics

`boundaries/2011-2014/crosswalk.json` uses necessary Census category bounds plus final2014 controls (D024, LevelB). Its `constraints.groups` retain22 split-parent conservation intervals. `lower`/`upper` and rational weight endpoints are global extrema conditional on this outer feasible set, not imputed observations. Existing2017→2020 and2023→2026 crosswalk formats remain unchanged and are adapted read-only by `contract.py`.

`boundaries/<transition>/party-votes.json` is explicitly synthetic. `votesLower/Upper` and `shareLower/Upper` enclose extrema under the full crosswalk; minimum/maximum brackets retain an attainable feasible value and the remaining numerical gap. The node budget may prevent exact extrema, which is recorded rather than suppressed. A scalar is emitted only when identified analytically; no arbitrary midpoint. Source records retain exact election-local party keys/names and observed counts; seven supporting Māori records are read from existing authoritative tables and reconcile to national controls. `partyMassConservation` is an invariant for every feasible matrix, not the sum of independently selected lower or upper values. Port Waikato party votes remain substantive; no candidate/split inference or TOP/Opportunity mapping follows.

### Stage4 readiness and secondary availability

`backtesting-readiness.json` links five same-boundary observed/synthetic comparisons and the future2026 baseline, records input hashes and verifies notional party inventories, numerical brackets and conservation controls. Observed election-local boundary IDs remain unchanged; integration explicitly records the official boundary regime. Code043's malformed2014 source label has a narrow, recorded typography join.

`secondary-availability.json` provides population-origin coverage bounds from held candidate-contest predecessors using the full coupled system. It is not a ballot-observation rate. Unidentified candidate-affiliation/split vote baselines are null; no zero filling. Original21 source-discrepancy records are copied exactly. No candidate person linking, inferred joint cells or Port Waikato behavioural observation.

### Evidence-repair/design cohort frame

`data/processed/checkpoints/evidence-repair/cohort-inventory.json` is a **selection frame, not an identity or effect dataset**. Each of 213 rows keys source/target year, scope and election-local seat number under one validated unchanged-boundary regime. It preserves the two source seat labels, source and target occurrence ID lists, held/cancelled status and a deterministic sample flag. `summary` counts the fixed 30 selected seat clusters and 415 source/target occurrences; `selectionRule` and `inputHashes` make the choice and consumed Stage7/geography bytes reproducible. No vote, residual, winner, person ID, identity confidence or career-status field enters sample selection. The corresponding design document defines proposed future evidence routes and uncertainty; no selected occurrence has been adjudicated by this checkpoint.

### Stage5 party-vote transformation outputs

Each backtest record keys transition × election-local electorate × canonical party. Shares are fractions; score summaries use percentage points, clipping frequency fractions. Point predictions/errors are null when not identified; outer prediction/error bounds are marginal/conservative. Numerical reconstruction brackets are separate. Continuity statuses exclude entrants/exits instead of zero-filling. Scores macro-average party MAEs equally; vote weights are actual target party counts. selection.json retains an unresolved candidate set with null default. No vector normalization.

### Stage6 party-seat elasticity

`records.json` stores held paired candidacies, their separate candidate/party denominators via pinned source records, fraction shares/deltas, original candidate labels, scope/geography and frozen Stage5 predicted party shares. Names do not assert person continuity. `fits.json` contains zero-intercept unrestricted slopes/sample sizes/training years; Māori reference diagnostics are not operational coefficients. `backtests.json` distinguishes descriptive, leave-one-out stability and chronological modes with raw candidate predictions and percentage-point loss metrics. `selection.json` separates descriptive historicalOLS from nullable selectedBeta andβ1 benchmark. No cancelled/missing candidate zero filling.

## Stage7 candidate-overperformance output family

`data/processed/models/candidate-overperformance/` is a separate descriptive modelling layer; historical inputs are unchanged.

- `specification.json`: frozen formulas, eligibility, universe, leave-one-out and interpretation policy.
- `input-contract.json`: path→SHA256 of all consumed preserved evidence, including supporting Māori candidate files; no synthetic candidate inputs.
- `occurrences.json.records`: all nominations, keyed by immutable election-local `candidateOccurrenceId`. Includes year/election/boundary/official seat identity, exact candidate/affiliation/party labels, null `personId`, published vote evidence, distinct denominators, shares, `rawPremium`, eligibility/reasons and provenance paths/source IDs. Supporting Māori IDs use official election/number and source order. `sourcePartyHeader` preserves the published column label separately from normalized party identity.
- `references.json.references`: party/election reference ID, exact matched seat/occurrence lists, counts, all-electorate coverage fraction, scope counts, candidate/party sums and aggregate shares. All official seats, including the cancelled seat, form the coverage denominator; only eligible held contests enter references.
- Occurrence `leaveOneOutReference`: aggregate counts/denominators after removing the entire focal contest; shares/offset null when no contest remains. `referenceCoverage` describes the original slate. Only one minimum: at least two matched contests before subtraction.
- `methods`: parameterized additive/proportional/log_odds raw/bounded expectations, out-of-range flags, unavailable reasons and raw residuals. `normalizedPremium` is the raw additive residual in fractions. A singleton retains raw premium but has null normalized premium and `insufficient_reference_contests`. Excluded occurrences have null premiums, explicit exclusions, and preserved source evidence; Port Waikato's published zeros are not observed candidate outcomes.
- `diagnostics.json` / `normalization-sensitivity.json`: counts, coverage, distributions in percentage points, scope/party/election comparisons, correlations and scale differences. No person rankings, fitted effects or inferred quality.
- `selection.json`: descriptive primary, sensitivity methods and interpretation/forecast restrictions. `manifest.json`: base revision, input/specification/code/output hashes and coverage counts.

A residual is an outcome description. Future persistence may use a prior residual only with valid history and temporal separation; target-election observed offsets/residuals cannot enter predictors for that election. Missing values and undefined transforms remain null, never epsilon-smoothed or zero-filled.

## Stage8 candidate-persistence output family

`data/processed/models/candidate-persistence/` is separate from Stage7 occurrences and earlier numerical data. Stage6/7 provenance contracts/manifests and Stage6 record input-hash metadata were corrected under D032 without changing numerical outputs.

- `specification.json` preserves the original pre-fit freeze and adds an explicitly post-fit `auditAmendment` correcting identity confidence and cohort eligibility. `input-contract.json` pins Stage7 occurrences, six observed election files, two preserved Parliament indexes and their Stage8 source plan/specification by SHA-256.
- `person-links.json.links` maps immutable `candidateOccurrenceId` to separate `personId`, occurrence `status`, `personExistenceStatus`, method and evidence. Only a directly corroborated winner is confirmed; profile-anchored exact-chain projections remain probable. Anchor occurrence/election dates and evidence retrieval are retained; unknown publication time is null. `unresolved` is explicit, and source aliases remain unchanged. Stage7 `personId` stays null.
- `history-status.json.records` has one row per Stage7 occurrence with election year, status, linked earlier occurrence IDs, prior-tenure and `careerHistoryEvidenceStatus`, `leftCensored` and nullable orthogonal `leadership`. Projected identity does not by itself establish career tenure. Unknown is not new or first-term. No status coefficients are present.
- `pairs.json.pairs` records adjacent linked histories, scope, party keys, electorates/boundary regimes, both occurrence links and evidence, anchor timing/outcome roles, additive prior/target residuals and alternative scales. `validationEligible` is outcome-independent of target/later wins but source-winner selected; `retrospectiveConfirmedEligible` is target-win selected and diagnostic only; `probableSensitivityEligible` is the broad comparable set. Each cohort has explicit inclusion/exclusion reasons. `targetResidual` is outcome evidence only.
- `analysis.json.primary` is the corrected source-anchored validation diagnostic, separate from `retrospectiveWinnerSelected`, zero-intercept, proportional/log-odds, broad probable-link and Māori sensitivities. Residuals internally are fractions; reported losses/intercepts are percentage points. Winner-selected scores do not determine `selection.json`.
- `selection.json.selectedOperationalCoefficient` is nullable and currently null. `manifest.json` pins branch base, input/code/output hashes and identity/pair counts. No candidate effect is exposed as an application coefficient.

## Stage9 freshman-incumbency output family

`data/processed/models/freshman-incumbency/` extends the Stage8 evidence layer without editing its occurrences, links or model outputs. Its source plan at `data/source-plans/freshman-incumbency-tenure-sources.json` pins108 new raw Parliament resources separately from the shared registry.

- `tenure-evidence.json.profiles` contains each official profile source ID/URL, display name, publication/retrieval dates, first Parliament election date, dated `serviceRows` (`electorate` or `list`, seat, party, start/end), unparsed-row count and evidence status. A missing table is `no_usable_dated_rows`, not “never served.” `input-contract.json` and `manifest.json` pin the pre-fit inventory's source plan, raw bytes, election/Stage8 inputs, code and output bytes.
- `inventory.json.records` retains all532 Stage8 adjacent linked pairs with source/target occurrence IDs, source-winner flag, Stage8 occurrence confidence, unique matched profile, source service dates, prior-list evidence, `tenureCategory`, `tenureReason`, primary eligibility and explicit exclusions. The pre-fit inventory's93 primary eligible pairs are historical; no target residual or target winner is a classification input. Seat switches, former careers, off-cycle entry, prior-list freshmen and unresolved histories remain distinct. `first_term` means first-ever electorate service starts at the source general election; it does not mean first appearance in the panel.
- `specification.json` is the committed pre-fit equation, cohorts, benchmarks, chronology and gates. `postfit-audit-amendment.json` explicitly records a later correction: three inherited Stage8 links depended on target/later winner anchors. The former remains unchanged in history. `cohort-audit.json.records` shows whether each of125 original comparable source-winner pairs survives a winner-flag counterfactual with candidate and tenure evidence fixed. The final evaluation set is90 pairs.
- `analysis.json.primary` holds the corrected general-electorate descriptive full-sample fit, no-freshman fit, mean-change sensitivity, earlier-election-only chronological fits and identical-sample MAE/RMSE benchmarks. `normalizationSensitivity`, `priorListSensitivity`, `offCycleSensitivity` and `bothConfirmedRetrospectiveWinnerSelected` are distinct. `supersededPreAuditOutcomeDependentCohort` is an audit trail **not** valid operational validation. `targetOutcomeCompositionRetrospective` describes observed wins/losses; it never sets eligibility. Residuals are converted from source fractions to percentage points for coefficients and scores.
- `selection.json.selectedOperationalFreshmanEffectPP` is nullable and currently null, with explicit gate values and no-bonus restriction. `analysis-input-contract.json` and `analysis-manifest.json` pin the corrected analysis inputs, dependent code and outputs. No operational freshman effect is exposed to the application.
## Stage10 replacement-candidate output family

`data/processed/models/replacement-candidate/` extends rather than rewrites Stage7–9 evidence. `inventory.json.records` contains immutable source/target occurrence IDs; party, seat, election and boundary contracts; source winner status; name contrast; identity class and method; separate inherited versus adjudicated source/target occurrence confidence; supporting source IDs, person/occurrence evidence, historical fact/publication/retrieval dates; career profiles and unknown-safe prior electorate/list flags; source/target residuals on additive, proportional and log-odds scales; and explicit exclusion reasons. `primaryEligible` requires a held same-party unchanged-boundary **general** source-winner event with supported continuation or distinct-person replacement from pre-result occurrence evidence, valid residuals and no by-election succession. A target victory is never a predictor or eligibility condition. `identityDependsOnTargetResult` and `identityDependsOnLaterOutcomeCoverage` label excluded retrospective cases.

The original pre-fit `specification.json` and its first zero-replacement inventory checkpoint remain historical. `post-review-amendment.json` records the reviewed identity/source-winner correction and pins the revised inventory commit. `identity-review.json` audits all 182 predeclared comparable general source-winner cases, with 20 bounded priority cases and accepted/unresolved evidence. `person-links.json` extends the shared person layer for 20 adjudicated occurrences, reusing inherited IDs where available and storing separate occurrence confidence, person-existence method, source, historical fact date, source publication/retrieval and unknown-safe career-history status; it was added after the corrected fit as metadata only, as disclosed in `postfit-selection-audit.json`. `maori-winner-overlay.json` contains 21 exact official winner occurrences with source IDs, published candidate votes and majorities; it never asserts cross-election person identity. `input-contract.json` and `manifest.json` hash Stage10 consumed artifacts and code. The Stage10 identity source plan and 24-record Māori snapshot enforce stage-specific metadata/raw-byte provenance without coupling older stages to unrelated source additions.

`analysis.json.primaryTransitionCounts` and `cohortBreakdown` report treatment/comparator, party, scope, outgoing status and identity-confidence counts. `chronologicalFittedComparison` holds earlier-election-only replacement, independently fitted no-replacement, retention-sensitivity, zero and carry-forward scores on identical holdout rows for each normalization. `strictSourceAnchorSensitivity`, `fullSampleDescriptions` and `descriptiveBenchmarks` remain separate from operational selection. `cohort-audit.json` rebuilds identity after removing target/later winner flags while preserving candidacies and the acquired historical facts; its zero unstable-primary count is computational, not proof of unbiased acquisition. `postfit-selection-audit.json` documents the indirect acquisition-selection path found after the corrected fit. `selection.json.selectedOperationalReplacementEffectPP` is **null** because the original no-outcome-dependent-cohort gate fails despite numerical gates passing. `analysis-input-contract.json` and `analysis-manifest.json` pin the final results. No Stage5–9 numerical artifact was regenerated or changed.

## Stage11 historical split-ticket output family

`data/processed/models/historical-split-ticket/` records an evidence checkpoint before the frozen specification and later diagnostics. `evidence.json.tableCoverage` audits general local matrices, named candidate columns, Māori supporting coverage, cancellation and reviewed discrepancies. `applicability.json.records` has one row per target candidate with source/target year, seat/scope, target and mapped source party, exact-chain versus unresolved candidate mapping, matched local-source status, unmatched target party group labels, geography and explicit exclusion reasons. These fields use candidacy and party participation, never target winner flags or target candidate votes. `conditionalPartialApplicability` means a source party candidate and some source rows exist; `conditionalLocalApplicability` requires every target party group and is false throughout the current comparable set. `input-contract.json` and `manifest.json` pin its consumed processed bytes and code. The 384-record stage-specific raw source snapshot is in `data/source-plans/stage11-local-split-sources.json`.

`specification.json` was frozen before `predictions.json` was calculated. Each `predictions.json.records` observation identifies a target/source candidate occurrence, matched party rows, target party-ballot total, unmatched ballot mass, reported exact candidate votes for **evaluation**, and source-local, pooled and party-only matched vote **intervals**. Fraction strings are exact rational endpoints; no local joint count is asserted. `actualMatchedVotes` comes from target split percentages solely for scoring. `fullCandidateVoteBounds` adds [0,unmatched mass] to the source-local matched interval. `publishedCandidateShareBoundsEvaluationOnly` divides those bounds by observed valid candidate votes, a different denominator from party ballots; it is not a pre-election share forecast. `jointAccounting` separates matched target-candidate destinations, destinations without a target candidate, non-candidate categories and unmatched party ballots. `transitionScores`, `partyScoresAtLeastFive` and `candidateMappingScores` contain bounded MAE/RMSE/bias in pp of target party ballots, with small-party groups unscored rather than presented as stable subgroup results.

`party-input-sensitivity.json` substitutes retained Stage5 local valid-party share intervals, using observed national party support and observed target valid-party turnout; its scores are conditional sensitivities, not a complete forecast or a Stage5 method selection. `identity-diagnostics.json` labels retrospectively acquired Stage10 identity classes without using them for eligibility. `outcome-audit.json` records the target/later winner-flag counterfactual. `selection.json.selectedOperationalSplitView` is nullable and currently null because unmatched ballot mass and unvalidated candidate transfer prevent a complete view. `analysis-input-contract.json` and `analysis-manifest.json` pin the final numerical outputs.

## Stage 13 identity evidence records

`data/processed/checkpoints/identity-evidence-pass/final/occurrence-evidence.json` has one row per fixed sampled candidature. `primaryOccurrenceConfidence` is confirmed only from an independently checked primary candidate-seat source, probable for an unresolved alias bridge, otherwise unresolved. `personEvidenceClaimId` identifies an occurrence-specific person claim; `personId` remains null until a cross-election relation is supported. `inheritedEvidence` and `inheritedReassessedConfidence` preserve earlier retrospective support separately. `inheritedCareerHistory` retains dated service evidence without asserting career completeness. `historicalFactDate`, `factKnownByDate`, `publicationDate` and `retrievalDate` are distinct, and `strictPreTargetCutoffAvailability=unknown` is explicit. `acquisitionState` is the historical search-ledger state, while `finalAdjudicationCompleted=true` marks a resolved review decision, including unresolved evidence. `relations.json` contains same-party source/target pair candidates, not verified same-person/different-person links. `coverage.json` groups post-adjudication confidence by transition, scope, role and observed official result; it also excludes the four preflight deviations in a sensitivity denominator.
