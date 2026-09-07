# Statistical specification — intended design, not an implemented model

Stage 1 / 2026-09-07. No data has been collected, coefficients estimated or electoral rules verified. This document records the requested research design; it is not a set of empirical findings. Read it before major work alongside PROJECT_STATE, METHODOLOGY, DECISIONS and DATA_SOURCES.

## Intended final pipeline

1. Reconstruct 2023 election results on official 2026 electorate boundaries and quantify reconstruction uncertainty.
2. Estimate current national party support using multiple major pollsters, documenting fieldwork, pollster effects and uncertainty.
3. Project national party movement into individual electorates using validated local baselines.
4. Independently estimate candidate outcomes using several empirically testable models.
5. Normalize historical local over/underperformance against national election conditions wherever possible.
6. Estimate candidate-status effects historically, including personal-vote persistence, first re-election and replacement effects.
7. Combine overlapping models through out-of-sample historical backtesting, rather than stacking correlated bonuses.
8. Propagate input, parameter, reconstruction and model uncertainty, including correlations.
9. Simulate all electorate winners. The requested coverage target is all 71 electorates; verify the official boundary inventory before treating that count as data.
10. Determine electorate qualification for sub-5% parties under verified rules. The threshold is a requested design requirement, not yet an implemented or independently verified rule.
11. Perform exact Sainte-Laguë allocation with independently checked examples and edge cases.
12. Calculate list MPs, overhangs and Parliament size, handling list availability and eligibility under verified rules.
13. Calculate outcomes for configurable government combinations. User-selected combinations are scenarios, not predictions of political agreements.

## Three independent candidate-vote estimators

| Estimator | Proposed estimand | Evidence and validation needed |
| --- | --- | --- |
| Split-ticket model | Candidate vote conditional on local party votes and joint party/candidate voting patterns | Source denominators, coverage, identifiability and temporal transferability |
| Party/electorate elasticity model | Response of candidate/electorate vote to party-vote movement, including different National and Labour resilience | Historical panel, boundary comparability, national conditions and out-of-sample stability |
| Normalized candidate-premium model | Candidate over/underperformance after accounting for party and national election conditions | Explicit national normalization, candidate histories, persistence and status effects |

Keep these estimators independent initially: separate predictions, configurations, diagnostics and historical validation outputs. Final combination weights must be learned from historical out-of-sample backtesting, not subjective judgement. Define election holdouts before fitting and avoid leakage from later candidacies, revised boundaries or outcomes. Weight fitting itself needs held-out evaluation. Do not choose coefficients, blend weights or a normalization formula in this stage.

## Explicit modelling constraints

- Historical split-ticket behaviour for National, Labour, Green, ACT, NZ First and Te Pāti Māori may be used when source quality and coverage support it. This permission is not evidence that a dataset exists.
- Do not extrapolate 2023 TOP electorate splitting directly into 2026 Opportunity. Opportunity gets a separate model; party identities and any relationships require explicit evidence and do not authorize behaviour transfer.
- Regional swing is outside the central model without adequate regional polling.
- Generic ministerial bonuses, MRP, turnout effects and tactical-voting feedback are not central assumptions unless later evidence supports them.
- Chris Bishop must not receive a generic freshman-incumbency bonus: the project instruction identifies him as having previously represented Hutt South. Verify candidate history from sources before creating a data record. Do not encode this as a name-based exception in model code.
- Normalize relevant historical overperformance metrics against national-level over/underperformance wherever possible; document exceptions and sensitivity.
- Do not count overlapping manifestations of personal vote multiple times. Persistence, incumbency, resilience, split voting, normalized premium and replacement effects may overlap.
- Distinguish established continuing, first-term, returning/former incumbents, replacement candidates, returning challengers, completely new and list-only candidates. Party leadership is an orthogonal flag; uncertain classification remains explicitly unknown. Prior tenure excludes automatic first-term status merely because the current spell is new.

## Required design record before implementing each component

Record the estimand, units, denominator, input source IDs, boundary vintage, missingness, equations, conditioning variables, uncertainty, validation plan, outputs and limitations. Maintain an effect-overlap table showing baseline, residual contribution and where each effect enters. Document whether a decision is permanent infrastructure or subject to backtesting. Reject fake precision and fabricated missing observations.

## Runtime boundary

Offline Python may perform ingestion, geographic transformation, regression and backtesting. Export versioned JSON/GeoJSON with provenance, coefficients and uncertainty metadata for the website; Python must not be required on Cloudflare Pages. Pure TypeScript simulation modules must accept serializable inputs and seeded configuration so they can run in a module Web Worker. No model, worker execution or simulation is implemented in stage 1.
