# Architecture

> **Current architecture (6 October 2026): see [nowcast-specification.md](nowcast-specification.md) §3.** The model is a hybrid: offline Python stages produce the national, local-party, candidate and Māori draws, and the TypeScript Stage49/65 MMP seat layer and the snapshot exporter run on a draw bank. The statement below that all model directories are placeholders, and the plan for TypeScript-only Monte Carlo, are Stage 1 history.


The browser loads the static Vite bundle, React renders the shared shell, and React Router selects a page. Stage 1 makes no data requests. There are no server functions, credentials or databases.

Future flow: immutable raw source → documented processing script → validated processed dataset → pure model modules → versioned output → UI. Keep large offline computation in reproducible scripts if required; choose browser execution versus precomputed static outputs in a later recorded decision, based on performance evidence.

Module boundaries:

| Directory | Intended responsibility |
| --- | --- |
| polling | Poll validation, pollster effects and national support |
| electorates | Boundary reconstruction and local contests |
| regressions | Shared fitting specifications and diagnostics |
| split-voting | Local party/candidate relationships |
| candidate-effects | Resilience, normalization, incumbency and replacement |
| simulation | Joint uncertainty propagation and seeded draws |
| mmp | Electoral rules, allocation, list seats and overhangs |
| types / utils | Shared contracts / pure helpers |

All model directories are placeholders. Avoid circular imports and importing UI code into models. Define integration contracts and dependency direction before linking components. Opportunity requires a distinct evidence-based treatment rather than automatic TOP carryover.

The shell supports keyboard navigation, a skip link, active route indicators, responsive layout, route titles and explicit unknown-route handling. Unit integration tests cover all routes. Hosting refresh behavior requires a deployment check later.

## Offline research and Web Worker boundary

Python handles future ingestion, transformations, geographic processing, fitting and backtesting only when authorized. Use pandas/numpy/scipy/statsmodels/geopandas/shapely only as needed, with exact locked dependencies. Export validated versioned JSON/GeoJSON into the processed/model boundary and then explicitly publish approved artifacts; never deploy Python or a database.

Future Monte Carlo computation belongs in pure TypeScript modules with no window, document or React dependencies. A module Web Worker will receive a request ID, immutable validated inputs/artifact references and seeded run configuration, and return serializable progress, result or error messages. The UI owns cancellation/worker termination and discards messages for stale request IDs. Reproducible run metadata must capture seed, PRNG/version, draw count, input hashes and code revision. No worker or numerical implementation is added now; the contract in src/types/domain.ts defines the message boundary.

Keep the existing src/app and src/models names and colocated tests rather than moving working code purely to match an illustrative tree. src/components and src/data are reserved for future shared UI and validated loaders. The detailed data/script subdirectories now exist.

## Export contract and dry run (draft v1)

Website data now has a versioned, validated boundary: forecast snapshots and an append-only archive index (`src/types/export.ts`), loaded by `src/data/loader.ts`, with a DOM-free pipeline skeleton and Web Worker protocol in `src/models/simulation`. A dry run on labelled synthetic fixtures exercises it; synthetic data is blocked from production. See [export-contract.md](export-contract.md).
