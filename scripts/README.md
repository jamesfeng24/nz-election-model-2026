# Processing scripts

No ingestion or modelling scripts implemented in stage 1. The standard-library `validate/source_files.py` checks registered local raw files without downloading or changing them; `tests/` contains synthetic integrity tests. Future scripts must document inputs, outputs, invocation and dependency versions; preserve raw bytes and fail clearly on missing inputs. See ../docs/reproducibility.md.
