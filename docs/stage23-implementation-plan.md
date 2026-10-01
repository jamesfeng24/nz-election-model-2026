# Stage 23 implementation plan (before construction or scoring)

This stage uses the three independently validated unchanged-boundary transitions
2008→2011, 2014→2017 and 2020→2023. The existing 213-contest candidate frame
defines the interface; party-vote reconstruction also includes its 21 Māori
seats and Port Waikato's 2023 party ballot. No candidate result enters the
party-vector construction.

1. Reuse Stage 5's pinned official election-local party tables, national
   controls and category continuity, and the validated frame IDs. Inventory
   every party ballot category and all target electorates before prediction.
2. Freeze a single compositional rule and its benchmark, information boundary,
   abstentions and metrics in a separately committed specification. Do not
   normalize Stage 5's saved marginal predictions.
3. Implement a deterministic construction artifact containing complete local
   vectors conditional on supplied target national party shares. Produce it
   before reading evaluation-only target local party results.
4. Evaluate party shares by holdout and scope, then document coverage,
   national accounting, category errors and limitations. Preserve all earlier
   model files and operational null selections.

The source dependency contract pins exactly the preserved Stage 5 inputs and
the fixed frame, continuity and alliance records consumed here. Input hashes
are checked before generation. All outputs use sorted keys/IDs and stable JSON.
Python standard-library arithmetic is sufficient; no optimizer or new external
dependency is planned. Conservation tolerance is 1e-12. Invalid/ambiguous
category joins, nonpositive denominators and nonfinite shares abstain with a
reason rather than yielding a fabricated point vector.

This is a conditional historical diagnostic using observed target national
valid-party support. It is not a national forecast, candidate prediction,
2026 baseline or operational selection.
