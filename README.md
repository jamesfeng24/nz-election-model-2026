# NZ Election Model 2026

An independent, transparent web application for a **nowcast** of the 2026 New Zealand general election: what would happen if an election were held under current political conditions ([D106](DECISIONS.md)).

**Current state:**
- historical data and the offline Python stages are in place, through Stage71;
- a live 2026 national poll fit exists (Stage62);
- the Māori seat layer, a verified MMP allocator and per-draw seat layer (Stages 49 and 65), and a versioned export contract with a synthetic dry run all exist;
- the live 2026 chain is **not assembled**, and no nowcast or probability is published.

What the product is and how its parts connect: [docs/nowcast-specification.md](docs/nowcast-specification.md). What remains before publication: [docs/release-checklist.md](docs/release-checklist.md). Stage-by-stage history: [PROJECT_STATE.md](PROJECT_STATE.md).

## Resume a new session

GitHub is canonical. Clone this repository, inspect `git status`, and read [AGENTS.md](AGENTS.md), [PROJECT_STATE.md](PROJECT_STATE.md) with any pending `handoff.d/` fragments, [docs/nowcast-specification.md](docs/nowcast-specification.md), [docs/release-checklist.md](docs/release-checklist.md), [DECISIONS.md](DECISIONS.md), [METHODOLOGY.md](METHODOLOGY.md) and [DATA_SOURCES.md](DATA_SOURCES.md). The original [statistical specification](docs/statistical-specification.md) is the Stage 1 design intent, kept as history. Follow the exact next task only after the user authorizes it. No prior conversation is needed.

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
npm run build     # the public site, static output in site/
npm run preview   # inspect the production build locally
npm run check     # frontend gates
npm run check:all # frontend + Python tests + source file integrity
```

## Structure

- `src/app/`: accessible navigation, pages and snapshot views (shown only when a validated snapshot is published).
- `src/models/mmp/`: verified MMP allocator and per-draw seat layer (Stages 49 and 65). `src/models/simulation/`: DOM-free pipeline interfaces, PRNG, worker protocol and the snapshot exporter (synthetic dry run only so far). The other `src/models/` directories are reserved.
- `src/types/`: runtime provenance and draft domain schemas, inferred TypeScript types and serializable worker message contracts.
- `src/utils/`: shared utility boundary.
- `data/raw/`, `data/processed/`: immutable inputs and reproducible stage outputs. `data/sources.json` is the frozen historical source register: new acquisitions go to standalone dated registries (AGENTS.md).
- `scripts/`: offline Python stages (one package per stage), source-file integrity validation and Python tests.
- `docs/`: the canonical nowcast specification and release checklist, plus per-stage design and findings records (historical).
- `.github/workflows/ci.yml`: tests, typecheck and production build on pushes and pull requests.

## Public site

The public site is a static React/Vite build with no server, database, secrets or runtime APIs: `npm run build` writes `site/` (one HTML file per page, relative paths, and the published `forecasts/` archive copied from `public/forecasts`). `npm run check:dist` checks the build. The publish workflow copies `site/` as it is; see [docs/stage84-public-site.md](docs/stage84-public-site.md).
