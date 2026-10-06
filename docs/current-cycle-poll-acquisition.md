# 2026-cycle national poll acquisition (acquisition only)

Branch `claude/project-thread-1g68p4`, base main 109794f. One question: what published 2026-cycle national party-vote polls exist since the 14 October 2023 election, preserved as dated, checksummed raw files? No national MCMC, fit, average or panel change. Stage35 files are untouched.

## Result

**No primary pollster, news or Wikipedia bytes could be fetched.** Outbound HTTPS in the cloud environment allows only GitHub; Wikipedia, Roy Morgan, 1News, Taxpayers' Union, RNZ, The Post, NZ Herald, Te Ao Māori News, The Spinoff and elections.nz all return a proxy 403 (`data/raw/polling/current-2026/reachability-probe.tsv`, 10 hosts). The reading tool's summaries of those pages were stale or inconsistent, so they are leads only, never data.

What was reachable and is now preserved (9 files, SHA-256 in `data/raw/polling/current-2026/acquisition-ledger.json`, each pinned to a commit):

| Source | Commit | Content |
|---|---|---|
| labo49/nzpolls | da33cf52 | Wikipedia 2026 table parsed daily, per-poll source URLs, scraped 2026-10-06T00:33Z, 122 rows to fieldwork end 2026-10-01 |
| danylmc/nz-polls | 25c58bc9 | Independent Wikipedia scrape with fieldwork start/end, scraped 2026-10-05T19:37Z, 122 rows |

Both are derivative copies of the Wikipedia table (no licence file; preserved for provenance, figures originate from Wikipedia CC BY-SA and the pollsters). They add no independent poll evidence. Upstream HEADs of the three Stage35 GitHub sources (Arie, Nixinova, Ellis) are unchanged from their pins.

## What this changes relative to the Stage35 panel (120 waves, to 2026-09-27)

[`gap-audit.json`](../data/processed/polling/current-cycle-acquisition/gap-audit.json) compares keys (fieldwork end plus NAT/LAB/GRN/ACT/NZF, 0.1pp):

- All 119 distinct Stage35 2026-cycle keys appear in both snapshots with identical shares. No value conflict.
- **One poll is newer than the Stage35 snapshot:** RNZ–Reid Research, published 2026-10-06, n=1000, NAT 25.9 LAB 30.8 GRN 14.8 ACT 9 NZF 10.6 TPM 2 TOP 5.5. labo49 lists fieldwork 24 Sep–1 Oct; danylmc lists 4–11 Sep with identical shares. A 6 October report quoting the RNZ article compares it with the August poll, which fits the later dates, but the primary page is unreachable: dates, mode and publication time stay unverified.
- **Two Talbot Mills rows are in Wikipedia but not the Stage35 panel:** 1–10 May 2024 (NAT 35, LAB 32 only) and 1–10 Nov 2024. The Stage35 Wikipedia parser drops rows with a blank or "1,000+" sample cell (11 such rows); nine are recovered through Nixinova, these two are not.
- Stage35 holds two waves for the same Talbot Mills 16 April 2026 result (a Nixinova row with a day-00 start and a Wikipedia row); the frozen design screens same-pollster overlap at cutoff, so nothing is changed here.

Whether to repair the parser gap or add the October poll belongs to the later authorised current-cycle ingestion stage; none of it is done here.

## Māori polls (recorded, not modelled)

Leads only, in the ledger: a Whakaata Māori poll (Curia, 1,000 Māori voters, published 17 September 2026) of the Māori and general rolls overall, reported as not measuring individual seats, and an NZ Herald headline for a Te Tai Tonga electorate poll. Neither was retrievable as raw bytes, so no figures are recorded. No poll for the other six seats was found. The roadmap's fallback baseline stays deferred until a seat is shown unpolled.

## Capture still needed from an unrestricted network

Fresh raw bytes for: the Wikipedia table (`https://en.wikipedia.org/api/rest_v1/page/html/Opinion_polling_for_the_2026_New_Zealand_general_election`), the RNZ–Reid, 1News–Verian, Taxpayers' Union–Curia, Roy Morgan, Post–Freshwater and Talbot Mills releases, and the Whakaata Māori and Te Tai Tonga poll articles. Register them by adding entries to `RESOURCES` in `scripts/polling/current_cycle.py` after fetching with curl, then `python -m scripts.polling.current_cycle`.

## Reproduce

`python3 -m scripts.polling.current_cycle --check` verifies checksums, the ledger and the audit byte for byte. `python3 -m unittest scripts.tests.test_current_cycle_polls` runs the 7 focused tests.
