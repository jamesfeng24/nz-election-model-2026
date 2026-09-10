# Methodology

## Current implementation

Historical design note: Stage 1 contained only the application shell, provenance contracts and documentation. Current state: validated 2008–2014 ingestion and integration are merged; 2017 ingestion is complete for review using a source-format-specific adapter (D018). No polling aggregation, regression, electorate reconstruction, effect estimation, simulation or MMP allocation is implemented. Empty states are not forecasts.

## Intended scope (not yet methods)

Estimate current national party support from multiple pollsters; reconstruct 2023 results on 2026 electorate boundaries; model every 2026 electorate using party vote, candidate vote and split-ticket evidence; distinguish National and Labour electorate-vote resilience; normalize candidate overperformance for national conditions; estimate first-term incumbency and candidate replacement effects; model Opportunity separately from 2023 TOP; simulate joint outcomes, qualification, Sainte-Laguë, list MPs and overhangs; explain individual electorate forecasts.

## Requirements for each future component

Before implementation record: research question and estimand; source IDs and coverage; units and missingness; assumptions; mathematical specification; uncertainty treatment; interactions with other components; validation and sensitivity tests; outputs and limitations. Cite verified electoral rules before implementing MMP. Do not hard-code unverified thresholds, seat counts or boundaries.

## Prevent overlapping effects

Resilience, split voting, national-environment normalization, incumbency and replacement can explain overlapping variation. Maintain an effect-dependency table when specifying models. State baseline, conditioning variables, residual effect and integration order; do not sum separately fitted effects without justification and validation. No integration order is chosen yet.

## Validation principles

Future work should document suitable historical holdouts, calibration and sensitivity checks without leaking outcome information. Distinguish evidence gaps, sampling uncertainty, parameter uncertainty and model uncertainty. Record seeds for stochastic runs, intervals and their interpretation. Never substitute fabricated data to produce a complete-looking forecast.

## Detailed intended specification

Read [docs/statistical-specification.md](docs/statistical-specification.md) for the full pipeline, independent estimators, historical normalization, candidate personal-vote persistence, exclusion rules and configurable government scenarios. These are design constraints, not implemented methods or sourced observations. The source registry was empty after the Stage 1 correction; current acquired coverage is recorded in DATA_SOURCES.md and PROJECT_STATE.md.

## Revised sequencing constraint — 2026-09-08

The authoritative implementation order is recorded in [docs/future-work.md](docs/future-work.md). It supersedes earlier proposed ordering without changing estimands. Current 2026 polling and Opportunity-specific modelling must not influence historical model selection or ensemble weights. Freeze the historical backtesting design and ensemble weights before Opportunity-specific modelling or current 2026 polling ingestion. Each later task requires explicit authorization.
