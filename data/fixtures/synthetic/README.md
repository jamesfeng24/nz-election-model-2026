# Synthetic fixtures (not data)

Invented inputs for the end-to-end dry run of the export pipeline (polls → national draws → local party → candidate → MMP → website). Every party, electorate, candidate and poll here is fictional and carries source id `synthetic-fixture`. Nothing here is a real poll, forecast or political observation and nothing is fitted.

Rules (AGENTS.md): never copy these files into `data/processed/`, `public/` or any application result; snapshots built from them have `provenance.kind = "synthetic-fixture"` and an id starting `synthetic-`, which the loader refuses in production and a test rejects in `public/` and `dist/`.

Files: `dry-run-inputs.json` (validated by `PipelineInputsSchema`), `dry-run-boundaries.geojson` (unit squares, not geography). See `docs/export-contract.md`.
