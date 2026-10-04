# Processing scripts

No ingestion or modelling scripts implemented in stage 1. The standard-library `validate/source_files.py` checks registered local raw files without downloading or changing them; `tests/` contains synthetic integrity tests. Future scripts must document inputs, outputs, invocation and dependency versions; preserve raw bytes and fail clearly on missing inputs. See ../docs/reproducibility.md.

### Stage37 companions (no inference or candidate runner)

- `.venv/bin/python -m scripts.polling.category_interface.run --check`
- `.venv/bin/python -m scripts.polling.category_interface.verification --check`
- `.venv/bin/python -m scripts.polling.category_interface.report --check`
- `.venv/bin/python -m unittest scripts.tests.test_stage37_category_interface -v`

`--construction-only` checks/saves allocations and external point inventory without scoring.32 compressed scenario/system archives retain fine category/ballot keys and paired national draw identities. Frozen source/preservation contracts allow unrelated registry additions. The future external proposal defaults to an offline manifest; its `--execute` route was not run or authorized in Stage37.

`python -m scripts.polling.category_interface.handoff --check` verifies the proposed saved-fit/common-sample replay references only; no candidate prediction or fitting occurs.

### Stage38 external national comparison

Frozen pre-inferencefa08640 and pre-score archiveeff424a. No MCMC in deterministic checks or CI:

```sh
python -m scripts.polling.external_comparison.archive --check
python -m scripts.polling.external_comparison.evaluation --check
python -m scripts.polling.external_comparison.numerical_audit --check
python -m scripts.polling.external_comparison.verification --check
python -m scripts.polling.external_comparison.report --check
```

All historical inference is already completed/cached. If resuming this stage, use its exact `.venv-external` lock/environment and `python -m scripts.polling.external_comparison.batch`; accepted cases reuse signatures, not refit. New incompatible code/settings fail. Pin/extract the preserved raw upstream tar under `.cache/stage38/upstream` if restoring a workstation; rawcode remains GPL separate from candidate code. Local raw-cache numerical audit was completed once; CI checks its recorded coordinates and sealed archives. `prepare --check` and focused actual upstream adapter tests require the isolated parsing environment, while general CI uses ordinary dependencies and explicitly skips those isolated cases. Detailed [contract](../docs/stage38-execution-contract.md) includes caps, seeds, exactscoring, attribution and source differences.

Stage38 cache enforcement companion: supervisor validates actual extracted source and configuration-root/environment before each resume, then compares complete accepted/failure signatures. Direct `inference` is an internal numerical module; use `batch` or `guarded --year YEAR --attempt N` as the supported execution entry points. Frozen numerical source, signatures and archived forecasts are unchanged; execution-guard-amendment.json records the original and guarded supervisor hashes. Cache-only batch resume is tested without MCMC.

### Stage39 cached national-to-candidate replay

`python -m scripts.polling.candidate_integration.inventory --check` verifies the frozen64/34/64-contest inputs.
`python -m scripts.polling.candidate_integration.construction --check` reproduces six raw-schema/scenario national and candidate transforms without inference; ordinary construction reuses only an exact compatible signature. Large per-draw candidate gzipJSON lives under ignored `.cache/stage39/candidate-draws/`; fine national archives, expected-share/conditional-interval summaries and cache checksums are versioned. Missing local caches are reconstructible.
`python -m scripts.polling.candidate_integration.evaluation --check`, `verification --check` and `report --check` verify held-out arithmetic and findings. All parameters/means/features are saved Stage33 primary fits; no fitting entry point is invoked. Intervals are national-input-only conditional, never calibrated candidate probabilities. Inputs, policies, metadata and horizon are frozen in the Stage39 contract.
