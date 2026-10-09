# Stage84: the public site

One question: can the existing TypeScript app become the public forecast site, reading only published export files, and be handed to the publish step as a plain static folder? Nothing statistical changes. No forecast is published here.

## What it is

- **Pages**, each its own static HTML file so links are relative and no server rewrite is needed: `forecast/` (the home page, also reached from `index.html`), `electorates/`, `methodology/`, `archive/`, plus `404.html`. The placeholder pages of the foundation shell (Polls, MMP, Data, About) are removed; their useful parts moved to `forecast/` and `methodology/`.
- **Headline graphic** (`src/app/SeatChart.tsx`, `hemicycle.ts`): expected seats per party as a parliament chart, one dot per seat, in James's order TPM, Greens, Labour, TOP, NZ First, National, ACT (2026-10-09); dots are the mean seats rounded by largest remainder to the mean Parliament size, with the 80% range beside each party and any remainder shown as Others.
- **Model only** (James, 2026-10-09): the site shows the model's snapshot and nothing else. If manual adjustments are ever made, the site shows only the adjusted version; no "Model + James" labelling is built.
- **Electorates page** (`src/app/ElectoratesView.tsx`): a search box with dropdown and a sort (name, closest contest, widest uncertainty); a seat view with each candidate's win chance, vote share with the 50% (dark) and 80% (light) ranges and a median tick, the polls attached to the seat, and a note for wider-uncertainty seats; an all-seats list. A seat has a shareable link (`#seat=<id>`).
- **Trend chart** (`src/app/TrendChart.tsx`, `loadReleaseHistory`): chance of a majority for NAT+ACT+NZF and LAB+GRN+TPM and of a hung parliament at each current release; it appears only once three verified releases exist and is dropped if any release fails its hash check.
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

## Export addition

`electorateDetail[].evidence` (optional, so schema v2 snapshots stay valid): `basis` (plain text) and `polls` (pollster, fieldwork dates, sample size, per-candidate percent, `usedInModel`, note). The page uses it when present and otherwise says no seat poll information is attached. The producers are not built here: the Python assembly (`scripts/nowcast_assembly/maori.py`, and the general-seat code after Stage79) must write the polls into each bank seat, and `drawBank.ts` and `fromBank.ts` must pass them through. Today only the polled Māori seats feed the model; the Wellington Bays and Mt Albert polls exist but are not used.

## Not done

An electorate map, a polls page and a feed. The site name and byline are still to be chosen by James. The publish step itself. The CI guard in `ci.yml` is unchanged: its `check:dist` step now checks `site/` because the package script does (`docs/ci-validation.md` still says `dist`; that file is CI policy and is not edited here).
