# Stage52 — 2026-cycle national poll acquisition (raw only)

Branch `claude/project-thread-qp68zt` (continues `claude/project-thread-1g68p4`). One question: what published 2026-cycle national party-vote polls exist since the 14 October 2023 election, preserved as dated, checksummed raw files? No national MCMC, fit, average or panel change. Stage35 files are untouched.

## Primary capture (second pass, wider network)

The first pass below reached only GitHub. A second pass from an environment with wider network access preserved **41 raw files with SHA-256** (37 fetched, with response headers, and 4 Taxpayers' Union–Curia browser prints supplied by James) in `data/raw/polling/current-2026-primary/` (`fetch-log.tsv` records every attempt; `acquisition-ledger.json` the checksums). Code: `scripts/polling/primary_capture.py` (`--check` verifies byte-for-byte). Outputs: [`primary-capture-audit.json`](../data/processed/polling/current-cycle-acquisition/primary-capture-audit.json) (every fact checked as verbatim text in the preserved bytes) and the dated registry `source-registry-primary.json`. The older `data/raw/polling/current-2026` snapshots, the Stage35 panel and `data/sources.json` are unchanged.

Captured: the Wikipedia REST HTML table (revision 1378752122); RNZ–Reid (2–9 Jul, 14–21 Aug, 24 Sep–1 Oct); 1News–Verian (23–27 Sep article; June and August reports as Scribd uploads by 1News); Roy Morgan (three monthly releases); The Post–Freshwater data tables (5–11 Jun, 4–11 Sep, with sample sizes and fieldwork); Talbot Mills/Anacta (Herald for Jun, Jul, Aug, Sep 2026 and 1–10 Nov 2024); Curia blog pointers; and the Whakaata Māori–Curia pages below.

Findings:
- **RNZ–Reid 6 Oct confirmed:** fieldwork 24 Sep–1 Oct 2026, n=1000 online quota sample, published 6 Oct 2026 06:27 NZDT. labo49's dates were right and danylmc's 4–11 Sep were wrong.
- **Talbot Mills 1–10 Nov 2024 recovered** from the Herald: NAT 34, LAB 33, GRN 10, ACT 10, NZF 7, TPM 3.3; no n published (3.1% margin).
- **Talbot Mills 1–10 May 2024 not recovered:** The Post page is a JavaScript shell, web.archive.org is denied, and nothing else was found in one bounded pass. Wikipedia (NAT 35, LAB 32) remains the only evidence.
- **Talbot Mills 2026 sample sizes** are not published in the articles (dates and a 3.1% margin only). **Anacta Consulting is the rebranded Talbot Mills.**
- **Taxpayers' Union–Curia (Jun–Sep 2026)** pages sit behind a Cloudflare challenge (HTTP 403) and were not bypassed. James supplied Chrome print-to-PDF captures of all four (not original server bytes; text extracted with `pdftotext -layout` into `tu-curia-pdf-text/`): fieldwork 4–8 Jun, 1–5 Jul, 1–4 Aug, 1–3 Sep, n=1000 phone and online, ±3.1%, shares and undecided rates match Wikipedia.
- Fieldwork and sample sizes for all Roy Morgan, RNZ–Reid, Verian, Freshwater and Anacta polls since 1 June match Wikipedia.

**Māori seats, 3 of 7 published.** Whakaata Māori–Curia (Whakatau 2026), n=500 each (420 phone, 80 online), ±4.5%: Te Tai Tonga (14–24 Sep), Te Tai Hauāuru (14–24 Sep) and Hauraki-Waikato (21 Sep–1 Oct; Maipi-Clarke TPM 45, Kiriona LAB 26, undecided 17, published 6 Oct). Waiariki, Ikaroa-Rāwhiti, Tāmaki Makaurau and Te Tai Tokerau have no published poll and no source announces one; "all seven will be polled" is not confirmed (three polls in nine days is consistent with it; election 7 Nov 2026). Raw only, not modelled.

**Live-fit input (James: use only the most recent polls).** No data are dropped here. The frozen design uses older polls to centre house effects, start the trend at the 2023 result and scale shared polling bias; a recent window is a candidate sensitivity for the live-fit stage, not the default.

Nothing further is wanted from James. The Talbot Mills 1–10 May 2024 row (NAT 35, LAB 32 only) was a Stage35 parser gap, not a 2026 input; it is immaterial to a 2026 fit, so it is not chased further.

Reproduce: `python3 -m scripts.polling.primary_capture --check`; `python3 -m unittest scripts.tests.test_primary_capture`.

## First pass (GitHub snapshots only)

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

## Māori electorate polls (recorded, not modelled)

**Cross-check of "all seven Māori seats will be polled": not confirmed from published sources.** Te Pāti Māori's one-tick strategy is confirmed by several reports (Waatea 5 October: electorate vote to TPM, party vote to Labour or the Greens, a one-person party list). But no readable source states that all seven seats will be polled or announces commissioning for the other four.

What has been published, as leads (summaries from a lossy reading tool; no raw bytes could be captured, no figures are treated as data):

| Seat | Source | Reported detail |
|---|---|---|
| Te Tai Tonga | Whakaata Māori–Curia, 29 Sep | fieldwork 14–24 Sep, n=500 (420 phone/80 online), ±4.5%; candidate vote Ramsden (LAB) 30, Murch (TPM) 17, Te Morenga (GRN) 16, Ferris (IND) 15; party vote also reported |
| Te Tai Hauāuru | Whakaata Māori–Curia, 30 Sep, "Whakatau 2026" series | same fieldwork and sample; Ngarewa-Packer (TPM) 38, Kātene (LAB) 27, Raukawa 10, undecided 18 |
| Hauraki-Waikato | NZ Herald headline only | Maipi-Clarke "well ahead"; nothing else retrievable |

A separate Whakaata Māori–Curia poll of the Māori and general rolls overall (17 Sep, n=1,000) measured no individual seat. Nothing found for Waiariki, Ikaroa-Rāwhiti, Tāmaki Makaurau or Te Tai Tokerau. The pattern, a Whakatau 2026 Curia series released seat by seat, fits the expectation that all seven will be polled, so the fallback baseline stays deferred. Capture each seat's poll as raw bytes when the network allows; the same question, denominator, dates, n and dependence fields the roadmap lists apply later.

## Capture still needed

Superseded by the primary capture above; the remaining items are listed there.

## Reproduce

`python3 -m scripts.polling.current_cycle --check` verifies checksums, the ledger and the audit byte for byte. `python3 -m unittest scripts.tests.test_current_cycle_polls` runs the 9 focused tests. `data/processed/polling/current-cycle-acquisition/source-registry.json` is a dated Stage40-style registry (data/sources.json schema, checked by `verify_source_files`); `data/sources.json` is untouched.
