# Architecture

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
