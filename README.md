# NZ Election Model 2026

An independent, transparent web application for modelling the 2026 New Zealand general election. **Historical election data, offline Python statistical stages (to Stage 46, Stage 47 in review) and a placeholder website exist; MMP seat allocation, the live forecast and any published probability do not.** The Stage 1 description that used to be here is obsolete: current state is in PROJECT_STATE.md.

## Resume a new session

GitHub is canonical. Clone this repository, inspect `git status`, and read [AGENTS.md](AGENTS.md), [PROJECT_STATE.md](PROJECT_STATE.md), [DECISIONS.md](DECISIONS.md), [METHODOLOGY.md](METHODOLOGY.md) [DATA_SOURCES.md](DATA_SOURCES.md) and [statistical specification](docs/statistical-specification.md). Follow the exact next task only after the user authorizes it. No prior conversation is needed.

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
npm run check     # frontend gates
npm run check:all # frontend + Python tests + source file integrity
```

## Structure

- `src/app/`: accessible navigation and seven pages, plus unknown-route handling.
- `src/models/`: reserved polling, electorates, regressions, split-voting, candidate-effects, simulation and mmp modules; no implementations.
- `src/types/`: runtime provenance and draft domain schemas, inferred TypeScript types and serializable worker message contracts.
- `src/utils/`: shared utility boundary.
- `data/raw/`, `data/processed/`, `data/sources.json`: immutable inputs, reproducible outputs and currently empty provenance register.
- `scripts/`: ingest/transform/analysis boundaries, read-only source-file integrity validation and Python tests.
- `docs/`: architecture, data dictionary, reproducibility and staged backlog.
- `.github/workflows/ci.yml`: tests, typecheck and production build on pushes and pull requests.

## Cloudflare Pages (future deployment)

This is a static React/Vite SPA, with no server, database, secrets or runtime APIs. Configure the repository root as the project root, build command `npm run build`, output `dist`, and Node 22.17.0. No deployment is performed in stage 1. BrowserRouter uses clean URLs; keep Cloudflare Pages' default SPA fallback (do not add a top-level `404.html`). Test direct entry and refresh for every route after deployment.

References: [Vite setup](https://vite.dev/guide/), [Cloudflare Pages Vite guide](https://developers.cloudflare.com/pages/framework-guides/deploy-a-vite3-project/), [Pages SPA behavior](https://developers.cloudflare.com/pages/configuration/serving-pages/).

## Contributing

Fetch latest main, confirm the remote, then create the authorized stage branch before editing. The current correction branch is `stage/01-foundation`; its changes must reach main only through a PR that the user merges. Push meaningful checkpoints periodically. Keep changes scoped to the authorized stage, document assumptions, add meaningful tests, run all checks and update the handoff documents before committing and pushing. Read [reproducibility](docs/reproducibility.md) and [future work](docs/future-work.md).

## Licensing

No open-source licence has been selected yet. Public availability does not grant an open-source licence. A future maintainer should choose the code licence explicitly; external data retains its own rights and restrictions.

## Offline Python setup

Use Python 3.12.2, pinned in .python-version and pyproject.toml. Foundation scripts use only the standard library, so no pip install is required and the complete third-party dependency set is empty. Optionally create an isolated environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m unittest discover -s scripts/tests -v
python3 scripts/validate/source_files.py
```

On Windows activate with `.venv\Scripts\Activate.ps1`. Ensure `python3 --version` matches the pin (or use the corresponding Python executable). This is a script workspace, not an installable Python package. Do not run `pip install -e .`. Add scientific packages only when needed, with exact versions and a committed lock including transitive dependencies. The website never requires Python. Future fitted outputs are versioned JSON/GeoJSON.

The original foundation was published directly to main before the expanded workflow was supplied. This correction preserves that history and submits the missing requirements separately; it does not retroactively turn the original commit into a PR.
