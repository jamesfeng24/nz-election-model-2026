# The public site

The TypeScript app is the public forecast site. It reads only the published export files and is handed to the publish step as a plain static folder. Nothing statistical changes here, and no forecast is published by this code.

## Pages

Each page is its own static HTML file (`<page>/index.html`, listed in `src/app/pages.ts`), so links are relative and no server rewrite is needed. `index.html` opens the Forecast page and `404.html` covers unknown addresses.

- **Forecast** (`src/app/ForecastViews.tsx`). One banner line: "Forecast if the election were held today · Updated <date>" (a date, never a time; "nowcast" stays in internal names). Then the expected-seats section, chance of a majority, party vote, the support trend and an odds-over-time chart (after three releases). Electorates are on their own page, not repeated here.
  - **Expected seats:** a parliament chart (`SeatChart.tsx`, `hemicycle.ts`) with one dot per seat in the order TPM, Greens, Labour, TOP, NZ First, National, ACT; dots are mean seats rounded by largest remainder to the mean Parliament size, with any remainder shown as Others. Below it a seats-by-party table (`SeatBars.tsx`) with one plain party-coloured bar per party at the median and the numbers (median, 80% range, electorate, list, chance of overhang), then an Overhang paragraph.
  - **Chance of a majority:** the four configured groups plus one "No majority" row.
  - **Ranges:** the 80% range only on this page; seat pages also show the 50% range. Probabilities are whole percents.
  - **Support trend** (`SupportTrend.tsx`): the national model's weekly estimate from the 2023 election result to the last week with poll data, a 90% band and each used poll as a faint dot, drawn from the saved fit.
  - **Odds over time** (`TrendChart.tsx`, `loadReleaseHistory`): chance of a majority for each group and of no majority at every current release. It appears once three verified releases exist and is dropped if any release fails its hash check.
- **Electorates** (`src/app/ElectoratesView.tsx` and `src/app/electorates/`). A search box with its own list of matching names, filters, a sort, the map, and the seat list. Selecting a seat opens its page (`#seat=<id>` is shareable). The list of all 71 seats shows the most likely winner, their chance and the expected margin (the winner's median vote share minus the runner-up's, in percentage points); the incumbent appears in the map's hover card and on the seat page, not in the list.
  - **Filters:** projected winner's party, incumbent's party (shown only when the export has incumbency), general or Māori, and two tick boxes: close contests (most likely winner under 70%) and projected flips (the sitting MP is standing but is not the favourite). Sort is alphabetical or closest contest first. Filters apply to the list and grey out the other seats on the map; flip seats carry a "Flip" tag in the list.
  - **Seat page:** each candidate's win chance, a median vote share, and a bar on one shared percentage axis (solid = 50% range, pale = 80% range, both with the median on hover), the seat's polls, the incumbent badge, and a note on seats with wider uncertainty.
- **Polls** (`src/app/PollsView.tsx`, `src/app/polls/`). National polls and electorate polls in the same one-line table format (the electorate table adds an Electorate column), the 10 newest first under month headings with a "See more" button for the rest. Only polls the model used are listed (the model uses every poll; one it could not use is left off the page rather than marked). Polls carry their full Wikipedia names ("Taxpayers' Union–Curia"), the party figures as published (a dash for a party not reported, `~` for an approximate figure) The limit of ten is display only. The source is stated on the page: Wikipedia revision and retrieval date as the aggregator, with a publisher's page where a registry holds the address.
- **Methodology** (`MethodologyView.tsx`): what the forecast means, how to read the ranges, how the build works, the data sources and the weekly update. If manual adjustments exist it adds an "adjustments" section (see below).
- **Archive** (`ArchiveView.tsx`): the append-only index, newest first, with a link to each raw snapshot; withdrawn and replaced entries stay listed and say so.
- **About** (`AboutView.tsx`, addresses in `siteLinks.ts`): who runs the site and how to get in touch. Each link shows its name above the address and a short note. A link with no address is not shown.
- **Footer on every page:** "Licensed under CC BY 4.0", linked to the licence text. There is no LICENSE file in the public repository.

Site name: "NZ Election Forecast". Look: white page, dark masthead with an orange accent (`#f08a24`), square corners, Libre Franklin headings and IBM Plex Mono figures (both SIL OFL, self-hosted as latin and latin-ext woff2 files in `public/fonts/` with their licences; no third-party font request). The stylesheet is `src/styles.css`, arranged by section.

## Data and loading

The pages read `../forecasts/index.json` and the snapshot it names through the validating loader (`src/data/loader.ts`: index, content hash, schema v2, index agreement). A forecast that fails any check is never shown, and synthetic snapshots are refused in a production build. Two different messages: "No forecast published yet" when the archive has no forecast (a 404 for the index or an empty index), and "The forecast could not be loaded" when one exists but cannot be loaded or verified (`LoadResult.cause` is `none-published` or `failed`). A newer forecast that is later withdrawn never reinstates the one it superseded; publish a new entry to restore it.

Only `public/forecasts` (the release publisher's archive path) feeds the site; rehearsal output is never written under `public/`.

## Export fields the site reads

Schema v2, plus optional additions so snapshots without them stay valid:

- `evidence`: `source`, `nationalPolls` and the weekly `trend`. Per seat, `electorateDetail[].evidence`: `basis` (plain text from the draw bank's seat source and class) and `polls` (pollster, client, dates, sample, margin, per-candidate percent, `usedInModel`, sources). Seat polls are matched to seats by electorate name. Without evidence the page says no poll information is attached.
- `directory.candidates[].incumbent` (only ever `true`, at most one per seat) and top-level `incumbency` (`label`, `url`, `asOf`), present together.
- `electorateDetail[].candidates[].winProbabilityInflation {p, mcse, ess}`, on the polled Māori seats only (every candidate of the seat, or none). Where present, the site shows the chance of winning as a range between `winProbability` and this figure (for example `61–84%`) in the seat table, the hover card, the accessible labels and the electorate list, with a short note on the seat page and a sentence on the methodology page. Seats without it show their single figure as before. The most likely winner, the margin, the close-contest filter and the map shading still use `winProbability`, the figure the seat totals use.
- `adjustments` (`by`, `items[{what, why}]`): when manual adjustments exist the site shows only the adjusted forecast, a forecast-page note says "includes manual adjustments by <name>", and the methodology page lists what was changed and why. Absent while there are none.

## Producers

- **Evidence:** `scripts/site_evidence/build.py` reads the preserved weekly-refresh `panel.json`, `estimate.json`, `dataset.json` and the preserved seat-poll files and writes `data/processed/site-evidence/<refresh date>/evidence.json` (inputs hashed inside, byte-reproducible; `--check`). Which national polls the fit used is derived by matching the panel to the fit's dataset by pollster and fieldwork midpoint and must equal the fit's own count. Poll names come from the preserved Wikipedia capture (hash-checked) by matching panel record ids; a poll the table no longer carries keeps the panel's pollster name. `npm run release:publish` takes it with `--evidence PATH` and fails closed on a seat poll whose electorate is not in the directory or a poll dated after the data cutoff. Known gap: most national polls have no recorded client and none has a publisher address, because the preserved panel records only the aggregator; the page says so rather than guessing. The seat-poll list uses the preserved Stage66/Stage70 files, not the Stage82 live file. Only the polled Māori seats feed the model; the Wellington Bays and Mt Albert polls are shown but not used.
- **Incumbents:** `scripts/site_incumbents/build.py` reads the preserved official current-MP index (`data/raw/identity-parliament-current.html`, retrieved 2026-09-23) and the Stage50 nominations (`data/processed/nominations-2026/2026-10-10/features-raw.json`) and writes `data/processed/site-incumbents/2026-10-10/incumbents.json` (hashed inputs, `--check`). A candidate is the incumbent when they are a sitting electorate MP (not a list MP) standing under the same name (same surname, first name equal or a prefix, accents ignored) in the 2026 seat whose largest predecessor is the electorate they hold, so renamed or redrawn seats are covered. 62 incumbents are matched; 9 sitting electorate MPs are not in their successor seat's nominations as of that file (Duncan Webb, Chris Penk, Paulo Garcia, Andrew Bayly, Brooke van Velden, Maureen Pugh, Shane Reti, Megan Woods, Greg O'Connor) and are listed in the file for review, never guessed. `buildNowcastSnapshot` takes an optional `incumbents` option joined on the candidate id (the nominations `targetOccurrenceId`); the release CLI takes `--incumbents PATH`. Display only: no model input changes.
- **Map:** `scripts/site_map/build.py` (needs shapely from `requirements-boundaries.txt`). The formal Stats NZ electorate polygons run out to sea, so the map is built from the preserved 2025 meshblocks: only meshblocks with land area are kept, dissolved by general and by Māori electorate, simplified together with a 300 m shared-border tolerance, islets under 1 km² and lakes under 8 km² dropped, and written to `data/processed/site-map/2026/map.json` (about 275 KB, lazily loaded by the electorates page; inputs hashed inside). A seat on several islands (Auckland Central: Waiheke, Great Barrier and others) is one shape with several parts. Re-deriving takes about two minutes and 280 MB of meshblocks, so `--check` is run by hand; the unit tests check the saved file and its recorded input hashes.

## Party names and the map

- **Names** (`src/app/partyNames.ts`): the names NZ media use, one form each: National, Labour, Greens, ACT, NZ First, TOP, Te Pāti Māori. A party with no override keeps the export's name.
- **Map** (`src/app/ElectorateMap.tsx`, `src/app/map/`): static SVG of the 2026 electorates with a General (64) / Māori (7) toggle, land only, on a pale sea tint (a tiled street basemap would need a third-party tile service). Each seat links to its seat page. Colour is the party of the most likely winner, paler for closer contests (opacity from 0.2 at a 40% win chance to 1 at certain). Seats where the sitting MP is standing but is not the favourite are striped diagonally in the seat's colour. Seats are matched to the snapshot by name (case, macrons and hyphens ignored); a seat with no forecast is grey. Four enlarged windows (Auckland, Hamilton, Wellington, Christchurch) show the seats too small to click nationally. The Chatham Islands are not drawn, and outlines are simplified for drawing only.
- **Hover:** hovering or focusing a seat opens a small card beside the pointer (nothing on the page moves; it flips left or up near the map's edge) listing the favourite and every candidate's chance, median share and incumbent tag. The SVG `<title>` and accessible label keep a shorter winner-plus-incumbent line.

## Source layout

`src/app/` holds the page components. Larger pages are split into folders: `electorates/` (rows and filters, search, filter controls, seat list, seat detail, range bars), `map/` (types, shapes, hover card) and `polls/` (national and electorate tables, month rows, poll names). Shared helpers: `partyColours.ts`, `partyNames.ts`, `intervals.ts`, `format.ts`. `App.tsx` chooses between the unavailable, loading and snapshot states.

## Build and checks

- `npm run build` (Vite, base `./`) writes `site/`: one HTML file per page, one JS and one CSS file, the map data, fonts, `404.html`, and `forecasts/` when present. `site/` is not committed.
- `npm run check:dist` runs the synthetic-content scan and `scripts/validate/check_site.mjs`, which fails if a page from `pages.ts` (or `404.html`) is missing, a path is root-absolute (only `404.html` may link to pages from the site root), a source map or README is present, an unexpected file type is present, or any file mentions the tooling that wrote the code or has a generator tag.
- `npm run format` and `npm run format:check` run Prettier over the site code only (`.prettierignore` leaves the research code alone). No ESLint: typescript-eslint does not yet support TypeScript 7, so `tsc`'s unused-variable checks stand in as the lint.
- Tests: `src/app/*.test.tsx`, `src/data/loader.test.ts`.

## Publishing

This code does not publish. The research-repository workflow that holds the publish token builds the site, writes the release archive into `public/forecasts` first, and copies `site/` to the public repository's `main` branch (served from the root by GitHub Pages) with James as author and committer. The public repository is never read or written by Claude sessions.

## Not done

A feed, a byline, the publish step itself, and a backcast of past weeks' seat odds. The About page's Ko-fi link, which stays hidden until `siteLinks.ts` has an address. The CI guard in `ci.yml` is unchanged: its `check:dist` step checks `site/` because the package script does (`docs/ci-validation.md` still says `dist`; that file is CI policy and is not edited here).
