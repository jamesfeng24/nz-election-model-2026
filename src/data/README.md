# Validated website data boundary

`loader.ts` loads the latest published forecast snapshot from the versioned archive (`<base>/forecasts/index.json`), verifying the index schema, the snapshot's SHA-256 and the snapshot schema (`src/types/export.ts`). Any failure returns `unavailable`; pages never render unverified or partial data. Synthetic fixtures are accepted only when the caller passes `allowSynthetic` (development). Never import raw data or synthetic fixtures into the website. See `docs/export-contract.md`.
