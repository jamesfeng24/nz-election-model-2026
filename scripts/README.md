# Processing scripts

No ingestion or modelling scripts implemented in stage 1. The standard-library `validate/source_files.py` checks registered local raw files without downloading or changing them; `tests/` contains synthetic integrity tests. Future scripts must document inputs, outputs, invocation and dependency versions; preserve raw bytes and fail clearly on missing inputs. See ../docs/reproducibility.md.

### Stage37 companions (no inference or candidate runner)

- `.venv/bin/python -m scripts.polling.category_interface.run --check`
- `.venv/bin/python -m scripts.polling.category_interface.verification --check`
- `.venv/bin/python -m scripts.polling.category_interface.report --check`
- `.venv/bin/python -m unittest scripts.tests.test_stage37_category_interface -v`

`--construction-only` checks/saves allocations and external point inventory without scoring.32 compressed scenario/system archives retain fine category/ballot keys and paired national draw identities. Frozen source/preservation contracts allow unrelated registry additions. The future external proposal defaults to an offline manifest; its `--execute` route was not run or authorized in Stage37.

`python -m scripts.polling.category_interface.handoff --check` verifies the proposed saved-fit/common-sample replay references only; no candidate prediction or fitting occurs.
