# Stage84: the public site

One question: can the existing TypeScript app become the public forecast site, reading only published export files, and be handed to the publish step as a plain static folder? Nothing statistical changes. No forecast is published here.

## What it is

- **Pages**, each its own static HTML file so links are relative and no server rewrite is needed: `forecast/` (the home page, also reached from `index.html`), `methodology/`, `archive/`, plus `404.html`. The placeholder pages of the foundation shell (Electorates, Polls, MMP, Data, About) are removed; their useful parts moved to `forecast/` and `methodology/`.
- **Forecast page** (`src/app/ForecastViews.tsx`): the "Forecast if the election were held today, as of <refresh date>" banner (D114 copy rule; the word "nowcast" stays in internal names), party vote and seats with 50/80/90 ranges, seats and majority chance for each configured group, the hung-parliament scenarios, Parliament size and overhang, and an electorate table (two most likely candidates; seats with wider uncertainty are marked). Probabilities are shown as whole percents. Before a first release, or if anything fails validation, it says "No forecast published yet" and shows no numbers.
- **Methodology page** (`src/app/MethodologyView.tsx`): what the forecast means, how to read the ranges, the build in plain language, the data sources, limits.
- **Archive page** (`src/app/ArchiveView.tsx`): the append-only index, newest first, with a link to each raw snapshot file and corrections shown as such.
- **Footer on every page:** "Free to share with credit (CC BY 4.0)", linked to the licence text (James, 2026-10-09: no LICENSE file in the public repository).
- **Data:** the pages read `../forecasts/index.json` and the snapshot it names, through the existing validating loader (`src/data/loader.ts`: index, content hash, schema v2, index agreement). Synthetic snapshots are refused in a production build. Only `public/forecasts` (the release publisher's archive path) feeds the site; rehearsal output is never written under `public/`.

## Build and checks

- `npm run build` (Vite, base `./`) writes `site/`: four HTML files, one JS and one CSS file, `404.html`, and `forecasts/` when present. `site/` is not committed.
- `npm run check:dist` runs the synthetic-content scan and `scripts/validate/check_site.mjs`, which fails if a page is missing, a path is root-absolute, a source map or README is present, an unexpected file type is present, or any file mentions the tooling that wrote the code or has a generator tag.
- The `react-router-dom` dependency is removed: pages are separate files, not client routes.

## Publishing

This stage does not publish. The research-repository workflow that holds the publish token builds the site, writes the release archive into `public/forecasts` first, and copies `site/` to the public repository's `main` branch (served from the root by GitHub Pages) with James as author and committer. The public repository is never read or written by Claude sessions.

## Not done

A map, charts, a polls page, per-seat pages and a feed. The publish step itself. The CI guard in `ci.yml` is unchanged: its `check:dist` step now checks `site/` because the package script does (`docs/ci-validation.md` still says `dist`; that file is CI policy and is not edited here).
