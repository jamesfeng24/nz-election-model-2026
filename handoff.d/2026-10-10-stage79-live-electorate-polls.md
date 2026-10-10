<!-- fold: changelog -->
## Stage79 follow-up — new general-electorate polls are data-only (D123), 2026-10-10

- `scripts/seat_polls/live.py` now reads the newest run of the Stage82 live-inputs file (`data/processed/polling/electorate-live/`, hash-checked against `index.json`) instead of the pinned transcription, which still serves the historical scoring. A new electorate poll needs no refit and no stage regeneration; the fitted inflation, half-life, cap and allowance are fixed.
- Pollsters in one seat combine by inverse variance (age-discounted relative to the freshest source); an older poll of one source beyond 14 days is superseded; same-source polls within 14 days merge as before.
- `data/source-plans/seat-polls/sponsor-groups.json` holds the Labour-aligned sponsor list as data.
- On the current cutoff the inputs equal the pinned ones; only poll ids in the seat records change, so the development gate, synthetic fixture, rehearsal report and the 2026 readout were regenerated for those ids. Config unchanged.

<!-- fold: state -->
# Stage79 follow-up: live electorate polls — review-ready, 2026-10-10

Branch `claude/project-thread-nzkrgh`, restarted from main `e56d487` (Stage79 #110 merged, Stage82 #95/#109 merged). Authorised by James on 2026-10-10 ("finish the follow up for general electorate polls"); combining rule left to the assistant by James ("use the combining rule you prefer"): inverse variance.

**What changed.** The 2026 poll source for the seat-poll layer, the combining rule across pollsters, the sponsor mapping as data, 6 new tests. **What did not.** The fitted parameters, the frozen design and scoring artifacts, the config, the Māori layer, Stage82 files (read only).

**Limits.** Review flags in the Stage82 `review.json` (new pollster, approximate cell, sponsored-story source) are published but do not block the layer; every row is Wikipedia aggregator evidence. Pollster identity is the text after the last dash in the published name; a new naming scheme would split a source in two (so it would be treated as independent). A late-added poll with fieldwork before the cutoff makes the development gate and the fixture stale until they are regenerated; a partial rebuild of only the changed seat has not been checked.

**Exact next action.** The coordinator reviews and merges; the next refresh adds polls to `electorate-live/` and the layer reads them. Not started: showing polls on the site.

<!-- fold: decisions -->
## D123 — 2026-10-10 — Stage79 follow-up: new general-electorate polls are data-only, read from the Stage82 live file; pollsters combine by inverse variance

The seat-poll layer reads the newest Stage82 electorate-live run instead of the pinned transcription. A new poll changes only its seat's input at run time: the inflation (5.3), half-life (6 weeks), cap (0.60) and the 0.12 SD Labour-aligned allowance stay as fitted, and nothing is refitted. Within a seat, polls of one source (the pollster behind the fieldwork) within 14 days merge as in the frozen design; an older poll of one source beyond that gap is superseded by the newer one. Different sources combine by inverse variance with each source's own allowance, a source older than the freshest having its variance divided by the square of its relative age factor; the combined poll takes the freshest source's age. James chose the rule on 2026-10-10 ("use the combining rule you prefer"). The frozen scoring evaluates each historical poll on its own, so the combining rule is a development choice, not an estimate. Number provisional (allocated by the coordinator).

<!-- fold: methodology -->
## Combining several general-seat polls (Stage79 follow-up, D123)

For a seat with polls from several sources, each source's polls merge as in Stage79 (within 14 days, later poll at 1.5 times the variance; an older poll beyond that gap is superseded). Source `s` then has value `y_s`, variance `v_s` (inflated sampling variance plus its sponsor allowance squared) and age factor `rho_s = 0.5^(age_s/6)`. With `rho_f` the freshest source's factor, the combined poll is `y = sum(a_s y_s) / sum(a_s)`, `v = 1 / sum(a_s)` with `a_s = (rho_s / rho_f)^2 / v_s`, and it enters the unchanged update with age and `rho_f`. One source reduces exactly to the Stage79 form.

<!-- fold: sources -->
## Electorate poll file read by the seat-poll layer (D123)

`scripts/seat_polls/live.py` reads `data/processed/polling/electorate-live/<newest run>/polls.json` (Stage82; Wikipedia aggregator evidence; hash and count checked against `index.json`). Sponsor groups for the poll-error allowance are in `data/source-plans/seat-polls/sponsor-groups.json` (Victor Consulting and Community Engagement Limited: Labour-aligned, from James, 2026-10-09). `data/sources.json` is untouched.
