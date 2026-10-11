# Publish workflow

`.github/workflows/publish.yml` ("Publish") turns the newest merged poll refresh into a published forecast: it adopts the refresh, reruns the forecast, runs every release gate, builds the static site and, only when told to, pushes the result to the public site repository (`jamesfeng24/jamesfeng24.github.io`, GitHub Pages from `main`, `/`). Decision D130 (provisional; the coordinator confirms the number). Requested by James, 2026-10-10. The site code is the Stage84 work (D122, PR #108), which must be on main first: the workflow's first check fails if it is not.

## The weekly chain

1. Monday 00:00 NZDT the Poll refresh workflow opens a refresh pull request when either kind of poll is new: national polls, electorate (seat) polls, or both. With neither it opens nothing.
2. **James merges it. This is his only manual step.**
3. The merge changes `data/processed/polling/weekly-refresh/index.json` (or the electorate index), which starts Publish on main.
4. Publish adopts the newest refresh, runs the forecast and gates, builds the site and pushes it, or stops with a red run and pushes nothing.

## Two kinds of publish: a new forecast, or the site only

| Kind | When | What it adds to the public repository |
|---|---|---|
| **Release** (a new forecast) | the newest refresh's release date is not yet in the archive, which happens exactly when the refresh brought new national polls or new electorate polls; or a manual correction | one archive entry (`forecasts/`), one **frozen copy of the whole site as it is that week** at `archive/<data cutoff date>/`, and the live root rebuilt |
| **Site only** | no new polls, but the site code on main changed (a design fix) or Publish is run by hand | the live root rebuilt from the current site code and the existing archive. **No new forecast, no archive entry, and no frozen copy is touched.** It commits only if the built files differ |

How it is decided (`plan.decide_work`): the release date is the later of the newest national refresh's data cutoff and the newest electorate-poll run's date, and the release id is `nowcast-<release date>`. If that id is not in the published archive, it is a release; if it is, the run is site-only. A Monday with neither new national nor new electorate polls has no refresh pull request, so nothing releases. A Monday with only electorate polls is a release: the adoption (`weekly_refresh.adopt`) keeps the national input of the newest national refresh (no refit is needed or run) and pins the new electorate-poll run, and sets `seatPolls.pollCutoff` to the run's date, so the seat polls are read up to that date and aged from it; the forecast, the archive entry, the frozen site folder and the banner date are all that date. The national vote shares are unchanged; only the seat layer moves. The snapshot's national basis says `electorate polls to <date>`.

**Frozen copies.** Each release builds the site twice from the same code and archive: the live site, and an archived-mode copy (`SITE_ARCHIVE_DATE=<cutoff> SITE_OUT_DIR=site-archived npm run build`: banner "You're viewing the forecast from <date>", a link back to the live site, its own `forecasts/` as published up to that week). The second goes unchanged to `archive/<cutoff>/`. Later publishes never rewrite it: the public tree is rebuilt around the existing dated folders, a digest of every dated folder is taken before and after, and any difference aborts the push (a correction replaces only its own date's folder). Every current archive entry must have its folder, and no folder may exist without a current entry. Two current forecasts with the same data cutoff date fail the run.

**Starting it.** A push to main that changes a refresh index starts a release run; a push that changes the site code (`src/` except tests and `src/release/`, `public/`, the page `index.html` files, `vite.config.ts`, the package files, `data/processed/site-map/`) starts a site run (or a release run, if new polls are waiting). A push that touches neither does not start Publish. A push-started run publishes only while the repository variable `PUBLISH_AUTO` is `true`; without it a push builds nothing. Because the choice is by state (is the newest cutoff archived?), two queued pushes cannot lose a release: the later run sees the same newest refresh.

## Two keys before anything is pushed

| Run | Pushes to the public repository only if |
|---|---|
| Manual (`workflow_dispatch`) | the **publish** box is ticked and the run is on `main` |
| Push to main (step 3 above) | the repository variable `PUBLISH_AUTO` is exactly `true` and the run is on `main` |

Every other run is not allowed to publish. A **manual** run without the box ticked is a **dry run**: it rehearses a release (everything up to and including the built site, the frozen copy and the final checks), never contacts the public repository, never uses the token and writes nothing outside the runner. A **push** to main while `PUBLISH_AUTO` is unset builds nothing at all (the run ends in a minute with a notice), so merging a refresh or a design fix before the first publish costs almost nothing. The first publish is a manual run James approves; he sets `PUBLISH_AUTO` to `true` afterwards to make the weekly chain hands-off, and unsets it to stop publishing (dry runs continue).

## Steps and gates

| Step | What it does | Stops the run when |
|---|---|---|
| Decide the run mode | `plan mode` | publish is asked for on a ref other than `main` |
| Check the site code is on this ref | the Stage84 files exist | the site pull request is not merged |
| Check the public repository (publish mode) | clone, confirm branch `main`, list the top-level entries, dry-run a push with the token, copy the existing `forecasts/` archive | the token cannot write, the branch is not `main`, or the repository holds entries a publish does not own (for example a `LICENSE` file; the site's own top-level files are known from `public/` and the page folders) |
| Decide what to build | release date = data cutoff of the newest national run; id `nowcast-<cutoff>`; **release**, **site only** or **nothing** (see above) | the cutoff is on or after election day (7 November); a correction names something other than a release of the newest cutoff |
| Switch the configuration to the newest refresh | `weekly_refresh.adopt --date <national>` (it pins the newest electorate-poll run itself), `nowcast_config.validate --require-complete`, then one local commit of `config/nowcast-2026.json` whose SHA is the snapshot's `codeRevision` | the configuration is not complete |
| Development gate | `nowcast_assembly.run` (64 draws) | it is not publishable |
| Site evidence and incumbents | `site_evidence.build --refresh <national run>`, `site_incumbents.build --check` | either fails or does not reproduce |
| Production run | `nowcast_assembly.run --require-complete` at 4,096 national draws × 16 replicates (65,536 rows): the Python publication gate | any gate check fails (about 35 minutes on the hosted runner) |
| Release gate and archive | options from the configuration; `release:publish` (TypeScript release gate: MCSE ≤ 0.01 on every published probability, model provenance, append-only archive); `verify archive` re-reads the files | refused by the gate; an earlier archive entry changed or disappeared; anything but exactly one new model release; a synthetic or stray release |
| Put the published archive in place (site-only) | copies the public archive to `public/forecasts` and checks it is unchanged | any archive difference |
| Build the site and check the tree | `npm run build`, `npm run check:dist` (no synthetic content, relative paths), `verify tree` | a page is missing, or a source map, README, synthetic file or rehearsal path is present |
| Build the frozen copy of the site (release) | `SITE_ARCHIVE_DATE=<cutoff> SITE_OUT_DIR=site-archived npm run build`, then the no-synthetic and site checks and `verify tree` on it | any check fails |
| Push the adoption branch (publish mode) | pushes the adoption commit to `publish/<id>-run<run>-<attempt>` in this repository so the snapshot's `codeRevision` resolves | the push fails |
| Push to the public repository (publish mode) | replaces the working tree with the built site, `README.md` and `.nojekyll`, keeps every existing `archive/<date>/` folder, adds the new frozen copy (release), commits as James, pushes to `main` without force | the public repository changed since it was read (nothing is pushed; run again); a frozen copy would change; a current forecast lacks its frozen folder; the commit does not carry James's identity and the plain message |
| Open the adoption pull request (publish mode, after the push, only when the repository variable `ADOPTION_PR` is `true`) | regenerates the development gate, the synthetic fixture and the Stage79 readout, adds one handoff fragment, pushes the same branch and opens a PR into main | never fails the run: the forecast is already public |

## What is pushed

The public repository holds the built site (one HTML file per page, assets, fonts, icons and share card, `404.html`), the `forecasts/` archive (`index.json` and one `snapshot.json` per release; earlier releases are never rewritten), one frozen site copy per forecast at `archive/<data cutoff date>/` (written once) and a short `README.md` (`scripts/publish_workflow/public-README.md`), plus an empty `.nojekyll`. Commit author **and** committer are `jamesfeng24 <233003834+jamesfeng24@users.noreply.github.com>`, the message is `Update forecast <data cutoff date>` for a release or `Update site <date>` for a site-only run, and there are no trailers. A run that changes nothing pushes nothing.

## The adoption, and why main lags

The refresh routine still never edits `config/nowcast-2026.json` (Stage70). The Publish workflow adopts inside the runner, which is how the 10 October refresh and every later one reach the forecast with no manual step. Main's configuration therefore trails what was published. If the repository variable `ADOPTION_PR` is `true`, the workflow opens an **adoption pull request** after each publish; merging it is bookkeeping (it keeps main equal to what was published and keeps the development-gate, fixture and readout checks in step). It is **off by default** because it costs about 15 minutes of regeneration plus a Verify run on the pull request each week; the next publish adopts the newest refresh again either way, and the published snapshot's `codeRevision` (the adoption commit on a `publish/` branch) records exactly what was run. The Stage77 rehearsal report is not regenerated by the workflow (about 30 minutes) and may be stale.

## Releases and ids

- One release per data cutoff: `nowcast-<cutoff>`. The id is never reused.
- A correction: run Publish manually (publish box ticked) with the `supersedes` id of the release it replaces; it must be a release of the newest data cutoff. It publishes `nowcast-<cutoff>-r2` (then `-r3`, ...), the archive marks the old one as replaced, and the frozen folder `archive/<cutoff>/` is rebuilt as the corrected week. This is the only way a frozen copy changes.
- Releases stop at election day: a data cutoff of 7 November or later is refused.

## Public logs

This repository is public, so run logs and artifacts are public. The workflow prints ids, dates and pass/fail only, never seats or probabilities. A dry run keeps the built site as an artifact only if "preview" is ticked; that artifact is downloadable by anyone with a GitHub account, so tick it only when that is acceptable.

## What James sets up (nothing else touches the public repository)

1. The `POLL_REFRESH_TOKEN` secret already exists in this repository. For publishing it must also be able to **write contents on `jamesfeng24/jamesfeng24.github.io`**: a fine-grained token with both repositories selected and Contents: read and write (and Pull requests: read and write for this repository), or a classic token with `repo`. Set the expiry after 7 November 2026 (the last refresh is 2 November) or put a reminder before it expires.
2. Public repository: Settings, Pages, "Deploy from a branch", branch `main`, folder `/ (root)`. Leave the default branch named `main`. The repository may be empty; if it holds anything besides the files above (for example a `LICENSE`), the first run stops and names them, then James removes them.
3. Merge the site pull request (#108), then run Publish manually once **without** the publish box ticked, to check the build (it rehearses a release, frozen copy included), then once with it ticked for the first publish.
4. After the first publish looks right: Settings, Secrets and variables, Actions, Variables, add `PUBLISH_AUTO` = `true`. From then on a merged refresh with new polls publishes a new forecast by itself, and a merged site-code change republishes the live root by itself (with it unset, a push builds nothing). Optionally add `ADOPTION_PR` = `true` for the bookkeeping pull request.

## Checks

`python3 -m unittest scripts.tests.test_publish_workflow` (mode, ids, options, archive and tree checks, the push against a local bare repository, and the shape of the workflow: no force, the token only in publish-mode steps, public repository never touched on a dry run). The workflow itself runs only on GitHub; the first dry run on main is its first full execution.

## Limits

- The site's polls page reads the preserved Stage66/Stage70 seat-poll files, not the weekly Stage82 live file (`scripts/site_evidence/build.py`, PR #108), so a new electorate poll moves the forecast but appears on the polls page only once that builder reads the live file.
- An electorate-poll-only change with no new national run keeps the data cutoff, so it is not a new forecast; publish it as a correction of that week's forecast if it matters.
- A site-only run needs the published archive, so it exists only in publish mode; a dry run rehearses a release and, on a push, builds nothing.
- The frozen copies are as good as the build on the day: a bug in the site code on that day stays in that week's copy (a correction release rebuilds it).
- The hosted runner is assumed to match the 4-core runner of the production run (about 35 minutes); the job limit is 150 minutes.
- The first publish cannot be rehearsed against the real public repository without touching it; the push logic is tested against a local bare repository only.

## Hosted minutes (for when the repository is private: 2,000 free Linux minutes a month)

A site-only run is about 6 minutes (checkout, `npm ci`, build, checks, clone and push). Publish runs only what the release gates need: no Verify, no Full replay, no frozen-pipeline replay. Expected per weekly run, on the 4-core hosted runner: environment install about 4, adoption and development gate about 1, site evidence about 1, production run about 35 (24 minutes measured on 3 local workers; 34 recorded earlier on 4 cores), release gate and archive about 2, site build and checks about 1, clone and push about 1, so **about 45 to 50 minutes** (the frozen build adds about 1); add about 15 and a Verify run if `ADOPTION_PR` is on. A run for an already-published date ends in under 2 minutes, and a failed gate stops early. Around each weekly refresh the other costs are the Poll refresh workflow (about 20 to 40 minutes), the Verify run on its pull request and the Verify run on the merge to main (each roughly 20 to 40 billed minutes when frozen-pipeline reuse applies; a full replay is about 170 and is not triggered by data-only pull requests). That is roughly 150 minutes per Monday, about 600 for the four remaining Mondays, plus about 100 for the first dry run and first publish: well inside 2,000.
