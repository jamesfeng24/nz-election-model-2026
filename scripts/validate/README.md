# Validate

`source_files.py` checks file containment, existence and SHA-256 against the registry, without fetching or transforming data. Run `python3 scripts/validate/source_files.py` from the repository. Further validators require explicit stage authorization. No statistical analysis is implemented. Preserve raw inputs; see ../../docs/reproducibility.md.

`ci_selection.py`/`ci_stage39.py` (Stage39) and `ci_frozen.py` (Stage45/46, registry `.github/validation/frozen-pipelines.json`) decide whether a pull request may reuse an earlier fully validated Linux run for a frozen pipeline; main and manual runs are always full and full is the default for anything unproved. See ../../docs/ci-validation.md and D081.
