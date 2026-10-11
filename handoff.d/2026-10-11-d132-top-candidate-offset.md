<!-- fold: changelog -->
## D132 — TOP candidate-weight offset, 2026-10-11

- Every TOP candidate's log-weight in the general-seat candidate step is lowered by 0.35 (about ×0.70) in every seat except Mt Albert (`nz-general-2026-boundary-025`). Config `candidate.partyExponentOffsets.opportunity`, validated in `scripts/nowcast_config/validate.py`; applied by `general.exponent_offsets` and `general.weights` in the assembly and the Stage79 readout.
- Config `2026-10-11.1` (decisions list gains D132). The development gate, synthetic fixture and Stage79 readout are regenerated. Scales, means, multipliers, the Māori layer and MMP are unchanged.
- Descriptive evidence: `scripts/top_candidate_offset/evidence.py` writes `data/processed/top-candidate-offset/evidence.json`. Write-up: `docs/d132-top-candidate-offset.md`; specification section added.

<!-- fold: state -->
# D132 TOP candidate-weight offset — review-ready, 2026-10-11

Branch `claude/project-thread-lzew9d` from main `898f25c`. Requested and decided by James on 2026-10-11 (offset −0.35, Mt Albert exempt, after the model-versus-NZ First/ACT/Greens comparison below).

**What changed.**
- A manual TOP-only offset on the candidate log-weight (D132); config `2026-10-11.1`.
- The development gate, synthetic fixture and Stage79 readout are regenerated. No other number is a deliberate change.

**What did not change.** The fitted S+R coefficients, kappa, scales, D107/D121 multipliers, local-party layer (proportional swing, Stage81), Māori layer, MMP, `data/sources.json`, frozen pipelines, the public site.

**Evidence and effect.** See `docs/d132-top-candidate-offset.md`. Outside flagged seats and seat wins, 2017–2023 candidate-to-party ratios are ACT 0.51, NZ First 0.83, Greens 0.87, and a party's candidate vote moved about 0.5–0.6 as much as its party vote between elections; TOP's own clean history (party vote mostly 2–3%) cannot test the 6–13% range. Prototype (1,024 draws): Christchurch Central TOP median 11.9% to 8.5% and win chance 4.5% to 1.2%; TOP expected electorate wins 0.36 to 0.14; chance of at least one 24% to 11%; National and Labour expected seat wins move by 0.1–0.2.

**Limits.** The −0.35 is James's judgement, the middle of 0.8×, 0.7× and 0.5× readings, not fitted or backtested. Flagged seats stand in for two-tick campaigns, which are not recorded. The Epsom, Wellington North and Wellington Bays TOP odds stay driven by TOP's proportionally scaled local party vote (Stage81 kept proportional; not reopened). Other third parties show the same overstatement in the candidate step (ACT most); not changed, as earlier work found party offsets unstable between elections.

**Exact next action.** The coordinator merges on James's go. The seat-poll change (use of polls where National and Labour are not the top two) ships as its own PR and will rebase on this config version.

<!-- fold: decisions -->
## D132 — 2026-10-11 — TOP candidate-weight offset −0.35, Mt Albert exempt (James)

James judged that TOP's electorate vote will not rise as much as its party vote (TOP runs a party-vote-only campaign everywhere except Mt Albert), and asked that TOP be compared with NZ First, ACT and the Greens in seats where they are not running two-tick campaigns. Outside flagged seats and seat wins, 2017–2023 candidate-to-party ratios are ACT 0.51, NZ First 0.83 and Greens 0.87, and a party's candidate vote moved about 0.5–0.6 as much as its party vote between elections, so TOP's roughly ×2.9 party-vote rise is a ×1.7–1.9 candidate rise. James chose an offset of −0.35 on every TOP candidate's log-weight (about ×0.70), the middle of the NZ First/Greens (×0.8), pass-through (×0.7) and ACT (×0.5) readings; Mt Albert is exempt. It is a manual override with no fit or backtest behind it; it changes TOP's own seat odds and the odds of the leaders in about four seats (Christchurch Central, Epsom, Wellington North, Wellington Bays), not the national seat totals. Not done: a general third-party ratio adjustment (earlier work found party offsets unstable between elections), a change to TOP's proportional party-vote scaling (Stage81, D119). [Write-up](docs/d132-top-candidate-offset.md).
