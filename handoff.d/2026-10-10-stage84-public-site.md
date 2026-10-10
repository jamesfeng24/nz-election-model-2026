<!-- fold: changelog -->
## Stage84 — public static site, 2026-10-10

- The app becomes the public site: `forecast/` (headline seat chart in James's party order, a trend chart that switches on after three releases), `electorates/` (searchable seat view), `polls/` (every poll cited), `methodology/` and `archive/` pages plus `404.html`, built by `npm run build` into `site/` with relative paths and the published `forecasts/` archive. Optional `evidence` (national polls, weekly support trend) and `electorateDetail[].evidence` (seat polls) added to the v2 export; new producer `scripts/site_evidence/build.py` writes `data/processed/site-evidence/2026-10-07/evidence.json` from preserved inputs, and `release:publish` takes `--evidence`. Placeholder pages and `react-router-dom` removed; CC BY 4.0 footer on every page.
- Party display names (National, Labour, ACT, New Zealand First, The Greens, The Opportunity Party, Te Pāti Māori; short forms NZ First, Greens, TOP, TPM in charts) and a clickable electorate map on the electorates page (general/Māori toggle, four zoom windows) drawn from `data/processed/site-map/2026/map.json`, produced by `scripts/site_map/build.py` from the preserved 2025 boundaries. The optional snapshot field `adjustments` and its methodology section appear only when manual adjustments exist.
- Review changes (James): one set of party names (National, Labour, Greens, ACT, NZ First, TOP, Te Pāti Māori; registered names once on methodology); main page shows only the 80% range; group table is the chance of a majority for the four groups plus "No majority"; seat shares in party colours; polls listed one per line under their full Wikipedia names; parliament chart layout reworked. Poll names come from the preserved Wikipedia capture in `scripts/site_evidence/build.py`.
- Round two (James): polls list shows the 10 newest under month headings with "See more"; seat tables, chart key and an Overhang section separate electorate from list seats and state overhang; the map is rebuilt from the preserved 2025 meshblocks (land only, `scripts/site_map/build.py`, shapely) so islands hover as their seat and city seats are legible.
- New `scripts/validate/check_site.mjs`; `npm run check:dist` now checks `site/`. No statistical or frozen change; nothing published.
- Round three (James): an incumbent marker (map: hover text and diagonal stripes where the sitting MP is not the favourite; seat page badge and list column) from a new producer `scripts/site_incumbents/build.py` (62 sitting electorate MPs matched; 9 unmatched listed), optional export fields `directory.candidates[].incumbent` and `incumbency`, release CLI `--incumbents`; and a new expected-seats layout (seats chart, seats-by-party table with one plain coloured bar per party and the numbers, overhang, then chance of a majority). Hovering a seat on the map shows a card with every candidate's chance, median vote share and incumbent tag. Site name "NZ Election Forecast"; seat bars are plain coloured bars. Display only.

<!-- fold: state -->
# Stage84 public site — review-ready, 2026-10-10

Branch `claude/stage84-public-site-9y5788` from main `9d2c8f1`. Requested by James on 2026-10-09 (outline shown first; no LICENSE file, CC BY footer instead).

**What changed.** The TypeScript app is now the public site (`docs/stage84-public-site.md`): three pages and a 404, built into `site/`, reading only `forecasts/` through the existing validating loader. New loader function `loadArchiveIndex`, `scripts/validate/check_site.mjs`, tests in `src/app/App.test.tsx` and `src/data/loader.test.ts`.

**What did not change.** The model, the draw bank, the release gate, frozen stages and their data, `data/sources.json`, `ci.yml`. The release publisher gains only an optional `--evidence` argument. The public repository was never accessed.

**Limits.** The publish step and the backcast of the seat odds and a national-poll publisher address (none is held) are not built. Methodology wording is plain-language and should be read by James before the first release.

**Exact next action.** Re-run `python3 -m scripts.site_evidence.build --refresh data/processed/polling/weekly-refresh/<date>` after each adopted refresh and pass the file to `release:publish --evidence`. The publish step (research-repo workflow, James's token) builds `site/`, copies it to the public repository and is rehearsed without synthetic data; the first real release follows the release checklist.

<!-- fold: decisions -->
## D122 — 2026-10-10 — The public site is a static multi-page build of the existing app (Stage84)

The public site lives in the research repository and is built into `site/` (one HTML file per page, relative paths) for a later publish step to copy as it is. It reads only the published snapshot archive (schema v2) through the validating loader and shows "No forecast published yet" otherwise. The licence notice is a footer line on every page ("Free to share with credit (CC BY 4.0)"), not a LICENSE file in the public repository (James, 2026-10-09). Site output must not contain synthetic content, source maps, extra documents or any mention of the tooling that wrote the code. The number is provisional until the coordinator confirms it.

<!-- fold: roadmap -->
| Stage84 | Public static site from the published export | review-ready |
