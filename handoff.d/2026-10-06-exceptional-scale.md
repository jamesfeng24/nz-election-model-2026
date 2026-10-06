<!-- fold: changelog -->
## Diagnostics: exceptional-seat balance scale, 2026-10-06

- Added `scripts/exceptional_scale/run.py`, `data/processed/exceptional-scale/summary.json`, `scripts/tests/test_exceptional_scale.py` and `docs/exceptional-scale-diagnostic.md`. These are a development diagnostic of the frozen audit flags against the Stage48 balance likelihood. Nothing is adopted; no CI, model, mean, scale or forecast change.

<!-- fold: state -->
# Diagnostics: exceptional-seat balance scale — review-ready, 2026-10-06

Branch `claude/cool-dirac-mq8787` from main `3a136c9`. One question: do the frozen 38/257 exceptional-uncertainty flags (2026-10-06 read-only audit) support separate ordinary and exceptional candidate N/L balance seat scales? This reuses the Stage48 loader and Gaussian likelihood unchanged, with an unpenalised two-group seat multiplier.

**Results.** The one-scale fit is 0.79 of the frozen seat scale (90% bootstrap 0.68–0.90). Ordinary seats are 0.60 (0.54–0.65), stable at 0.59–0.63 per election and in leave-one-election-out fits. Exceptional seats are 1.46 (1.09–1.80); the ratio is 2.41 (1.80–3.08), 1.23 in 2020, and 1.69 without the five largest cases. LR 70.2 on 1 df; permutation 0/400. Held-out likelihood improves in all four elections (2020 only slightly). Even-seat 90% N/(N+L) width: frozen about 30–32pp, ordinary about 21–23pp, exceptional about 40–44pp.

**Limits.** The flags are not fully blind (21 of the 38 came from a residual-ranked list); this is in-sample development evidence with the shared scale untouched. Nothing is adopted.

**Checks.** `python3 -m unittest scripts.tests.test_exceptional_scale` 4 PASS; `python3 -m scripts.exceptional_scale.run --check` PASS (about 1m40, local Python 3.13 with pinned numpy 2.2.6/scipy 1.16.0). Not run: the full suite and frontend (no shared code changed). CI was not modified; the separate pending CI fix remains separate. New test files force full hosted validation under the existing selector.

**Exact next action.** James decides whether to authorize a pre-registered ordinary/exceptional uncertainty design (ideally chronological with blind flags). Leave this PR for coordinator review; do not adopt.
