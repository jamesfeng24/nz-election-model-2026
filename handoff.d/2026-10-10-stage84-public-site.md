<!-- fold: changelog -->
## Stage84 — public static site, 2026-10-10

- The app becomes the public site: `forecast/` (headline seat chart in James's party order, a trend chart that switches on after three releases), `electorates/` (searchable seat view), `methodology/` and `archive/` pages plus `404.html`, built by `npm run build` into `site/` with relative paths and the published `forecasts/` archive. Optional `electorateDetail[].evidence` added to the v2 export (seat polls; producers not built). Placeholder pages and `react-router-dom` removed; CC BY 4.0 footer on every page.
- New `scripts/validate/check_site.mjs`; `npm run check:dist` now checks `site/`. No statistical, Python, export-schema or data change; nothing published.

<!-- fold: state -->
# Stage84 public site — review-ready, 2026-10-10

Branch `claude/stage84-public-site-9y5788` from main `9d2c8f1`. Requested by James on 2026-10-09 (outline shown first; no LICENSE file, CC BY footer instead).

**What changed.** The TypeScript app is now the public site (`docs/stage84-public-site.md`): three pages and a 404, built into `site/`, reading only `forecasts/` through the existing validating loader. New loader function `loadArchiveIndex`, `scripts/validate/check_site.mjs`, tests in `src/app/App.test.tsx` and `src/data/loader.test.ts`.

**What did not change.** The model, the export schema, the release publisher and gate, Python, data, `data/sources.json`, `ci.yml`. The public repository was never accessed.

**Limits.** An electorate map, the publish step and the Python/bank producers of seat-poll evidence are not built; seat pages say no poll information is attached until they are. Methodology wording is plain-language and should be read by James before the first release.

**Exact next action.** The publish step (research-repo workflow, James's token) builds `site/`, copies it to the public repository and is rehearsed without synthetic data; the first real release follows the release checklist.

<!-- fold: decisions -->
## D122 — 2026-10-10 — The public site is a static multi-page build of the existing app (Stage84)

The public site lives in the research repository and is built into `site/` (one HTML file per page, relative paths) for a later publish step to copy as it is. It reads only the published snapshot archive (schema v2) through the validating loader and shows "No forecast published yet" otherwise. The licence notice is a footer line on every page ("Free to share with credit (CC BY 4.0)"), not a LICENSE file in the public repository (James, 2026-10-09). Site output must not contain synthetic content, source maps, extra documents or any mention of the tooling that wrote the code. The number is provisional until the coordinator confirms it.

<!-- fold: roadmap -->
| Stage84 | Public static site from the published export | review-ready |
