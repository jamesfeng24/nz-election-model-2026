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
npm run build     # static output in dist/
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

## Cloudflare Pages (future deployment)

This is a static React/Vite SPA, with no server, database, secrets or runtime APIs. Configure the repository root as the project root, build command `npm run build`, output `dist`, and Node 22.17.0. No deployment is performed in stage 1. BrowserRouter uses clean URLs; keep Cloudflare Pages' default SPA fallback (do not add a top-level `404.html`). Test direct entry and refresh for every route after deployment.

References: [Vite setup](https://vite.dev/guide/), [Cloudflare Pages Vite guide](https://developers.cloudflare.com/pages/framework-guides/deploy-a-vite3-project/), [Pages SPA behavior](https://developers.cloudflare.com/pages/configuration/serving-pages/).

## Contributing

Follow [AGENTS.md](AGENTS.md): fetch latest main, work on the authorized branch, keep each change to one bounded question, record shared-document updates as a `handoff.d/` fragment, and reach main only through a reviewed PR. Read [reproducibility](docs/reproducibility.md) and [future work](docs/future-work.md).

## Licensing

No open-source licence has been selected yet. Public availability does not grant an open-source licence. A future maintainer should choose the code licence explicitly; external data retains its own rights and restrictions.

## Offline Python setup

Use Python 3.12.2, pinned in .python-version and pyproject.toml. The stages need the pinned numerical packages in `requirements-boundaries.txt` (numpy, scipy, shapely, matplotlib), which is what CI installs; the external national model has its own lock (`requirements-external.lock`, never run in CI). Create an isolated environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-boundaries.txt
python3 -m unittest discover -s scripts/tests -v
python3 scripts/validate/source_files.py
```

On Windows activate with `.venv\Scripts\Activate.ps1`. Ensure `python3 --version` matches the pin (or use the corresponding Python executable). This is a script workspace, not an installable Python package. Do not run `pip install -e .`. Add scientific packages only when needed, with exact versions and a committed lock including transitive dependencies. The website never requires Python. Future fitted outputs are versioned JSON/GeoJSON.

The original foundation was published directly to main before the expanded workflow was supplied. This correction preserves that history and submits the missing requirements separately; it does not retroactively turn the original commit into a PR.
