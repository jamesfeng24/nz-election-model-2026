# NZ Election Model 2026

An independent, transparent web application for modelling the 2026 New Zealand general election. **Stage 1: foundation only. No election data or statistical model is included, and no forecast is published.**

## Resume a new session

GitHub is canonical. Clone this repository, inspect `git status`, and read [AGENTS.md](AGENTS.md), [PROJECT_STATE.md](PROJECT_STATE.md), [DECISIONS.md](DECISIONS.md), [METHODOLOGY.md](METHODOLOGY.md) and [DATA_SOURCES.md](DATA_SOURCES.md). Follow the exact next task only after the user authorizes it. No prior conversation is needed.

## Local setup

Use Node 22.17.0 (`nvm install && nvm use`, if using nvm) and npm 10.9.2. Versions are locked in package-lock.json; use `npm ci` for repeat installations.

```sh
git clone https://github.com/jamesfeng24/nz-election-model-2026.git
cd nz-election-model-2026
npm ci
npm run dev
```

Open the local URL printed by Vite. Other commands:

```sh
npm run test       # Vitest, single run
npm run test:watch # interactive tests
npm run typecheck # strict TypeScript
npm run build     # static output in dist/
npm run preview   # inspect the production build locally
npm run check     # all three stage gates
```

## Structure

- `src/app/`: accessible navigation and seven pages, plus unknown-route handling.
- `src/models/`: reserved polling, electorates, regressions, split-voting, candidate-effects, simulation and mmp modules; no implementations.
- `src/types/`: runtime provenance schemas and inferred TypeScript contracts.
- `src/utils/`: shared utility boundary.
- `data/raw/`, `data/processed/`, `data/sources.json`: immutable inputs, reproducible outputs and currently empty provenance register.
- `scripts/`: future processing commands, currently documentation only.
- `docs/`: architecture, data dictionary, reproducibility and staged backlog.
- `.github/workflows/ci.yml`: tests, typecheck and production build on pushes and pull requests.

## Cloudflare Pages (future deployment)

This is a static React/Vite SPA, with no server, database, secrets or runtime APIs. Configure the repository root as the project root, build command `npm run build`, output `dist`, and Node 22.17.0. No deployment is performed in stage 1. BrowserRouter uses clean URLs; keep Cloudflare Pages' default SPA fallback (do not add a top-level `404.html`). Test direct entry and refresh for every route after deployment.

References: [Vite setup](https://vite.dev/guide/), [Cloudflare Pages Vite guide](https://developers.cloudflare.com/pages/framework-guides/deploy-a-vite3-project/), [Pages SPA behavior](https://developers.cloudflare.com/pages/configuration/serving-pages/).

## Contributing

Keep changes scoped to the authorized stage, document assumptions, add meaningful tests, run all checks and update the handoff documents before committing and pushing. Read [reproducibility](docs/reproducibility.md) and [future work](docs/future-work.md).

## Licensing

No open-source licence has been selected yet. Public availability does not grant an open-source licence. A future maintainer should choose the code licence explicitly; external data retains its own rights and restrictions.
