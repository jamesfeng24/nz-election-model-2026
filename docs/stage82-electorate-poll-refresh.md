# Stage82 — electorate polls in the automatic poll refresh

Authorised by James (project thread, 2026-10-10); decision D120. A data-collection stage: it reads the "Electorate polling" tables of the Wikipedia opinion-polling page (the page the national refresh already captures) into a dated, append-only live-inputs file. **Nothing reads that file yet.** Applying general-seat polls is the separate Stage79 question; wiring the Māori seat polls is a separate change to how the Māori layer reads its poll input. A new electorate poll is therefore a data change only: no refit, no change to any estimate, no pinned stage file edited. Not touched: Verify, the frozen-pipeline selector and registry, `scripts/polling/weekly_refresh/`, `config/nowcast-2026.json`, `data/sources.json`, Stage66/71/78 files.

## What the page looks like (checked 2026-10-09 and 2026-10-10)

Section "Electorate polling" with "General electorates" and "Māori electorates", one small table per seat (seat name only in the heading). Each poll is two rows, "Party Vote" and "Electorate vote"; the date, pollster and sample cells are merged across both rows, so the raw electorate row has fewer cells than the header. Party columns differ per table (NAT/GRN/LAB… in one, LAB/NAT/GRN… in another, TPM first in Māori tables) and are parties, not candidates; independents appear as `IND`, the Opportunity Party as `OPP` (stored as `TOP`). Cells may hold `~30`, `-`, `—` plus hidden "N/a" text, blanks, a "Lead" column with numbers or "Tie", and footnote markers. Sample sizes 400 to 821.

## Reader (`scripts/polling/electorate_refresh/parse.py`)

1. Expands every merged cell into a rectangular grid, then reads each cell under its header column, so a number cannot land under the wrong party.
2. Requires: header `Date, Polling organisation, Sample size, (blank), <party columns>, Lead` with only known party labels (`NAT LAB GRN ACT NZF TPM OPP TOP IND Others`); rows in pairs labelled "Party Vote" then "Electorate vote" with identical merged date, pollster and sample cells; every row the header's width; the seat's heading under a "General electorates" or "Māori electorates" subsection.
3. Keeps only electorate-vote shares for use. The party-vote row is read and validated but stored unused (it overlaps the national and local-party layers; the draft Stage79 design forbids using it). The Lead column is ignored.
4. Cleaning: `~30` becomes 30 with an `approx` flag; `-`, `—`, `—N/a` and blank are missing (never zero); footnote markers dropped, each footnote's first external URL recorded; sample `1,001` becomes 1001, blank becomes missing; fieldwork `22–29 Jul 2026`, `21 Sep – 1 Oct 2026` or a single date becomes ISO start and end.
5. Anything else raises `Block` and the run stops for a human: unreadable cell or date, unknown party column, changed header, unpaired or ragged rows, shares totalling more than 100 plus 0.5 per cell, missing or empty section, unknown subsection.

Verified against the live page (12 polls in 11 tables) and against the Stage70 Part C press transcriptions (Mt Albert 21–28 Sep, Wellington Bays 4–10 Sep): the values agree.

## Rules (`rules.py`)

Seat names resolve against the official 2026 electorate list (newest `data/processed/nominations-2026/*/official-table.json`; only the labels are read), ignoring accents and treating "Mount" as "Mt": Wikipedia's "Mount Albert" and "Kāpiti" become the official "Mt Albert" and "Kapiti". A poll's identity is seat, fieldwork dates and pollster (punctuation and spacing ignored); `contentSha256` covers its shares, sample size and flags.

- **Blockers:** unknown seat; section type disagreeing with the official seat type; fieldwork ending after the run date or outside 2026; two rows with one identity; a published poll whose content changed on Wikipedia (revised); a published poll that disappeared (removed).
- **Review flags (published, a human looks):** a pollster new to the file (not flagged on the first run); an approximate (`~`) cell; an independent column share; a cited page that is a sponsored story; listed parties totalling under 60%.
- **Info:** primary-release verification pending (every row is `aggregator_only`; nothing was checked against a primary page), blank sample, late addition.

## Outputs (never edited once written)

`data/processed/polling/electorate-live/<date>/`: `polls.json` (cumulative: the previous file plus the additions, sorted), `changes.json`, `review.json`, `source-registry.json` (the schema of the Stage40/52 registries; `data/sources.json` is untouched), `seats.json` (the official labels used), `manifest.json`; `index.json` lists the runs. A byte copy of the capture is kept under `data/raw/polling/electorate-live/<date>/` (page, response headers, fetch log). One handoff fragment per run. Blocked runs write only `blocked.json`, `review.json`, the registry, the seat list and the capture copy, and are not in the index. If nothing changed the run writes nothing.

`python3 -m scripts.polling.electorate_refresh.run --check` (stdlib) re-derives every run from its preserved capture: hashes, the append-only chain (an earlier poll never changes), identical polls and additions.

## First run (2026-10-10, Wikipedia revision 1379243489)

12 polls: 8 general (Auckland Central, Hutt South, Kapiti, Mt Albert × 2, Waitaki, Wellington Bays, West Coast-Tasman) and 4 Māori (Hauraki-Waikato, Te Tai Hauāuru, Te Tai Tonga, Waiariki). Review flags: Hutt South NAT `~30`; West Coast-Tasman cites a sponsored story; Te Tai Tonga lists an independent at 18%. Hutt South and Kapiti are one Labour-aligned source (James, 2026-10-09; Stage79 handles the allowance, this file does not). The 1–5 Oct Mt Albert poll (Taxpayers' Union–Curia) was not in Stage70 Part C.

## Using the file later (not done here)

A consumer reads `polls.json` of the latest index entry at run time with every fitted parameter fixed, so a new poll needs no refit; the nowcast assembly must still be rebuilt for its numbers to move (whether only the changed seats can be rebuilt has not been checked). The Māori layer's calibration set stays frozen and never contains 2026 polls; 2026 polls are application data, not fitting data. Each is a separately authorised stage.

## Limits

Volunteer-edited aggregator: a one-cell edit to a 400-person poll passes every sum check, which is why every change goes through a reviewed pull request and revised or removed rows block. The page layout has already changed within a week (the section did not exist on 7 October); the reader blocks on the first change it does not understand, which means an occasional red run needing a reader fix. Candidate names are not in the tables, so an `IND` share cannot be tied to a person without a human.
