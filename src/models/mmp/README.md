# Qualification, Sainte-Laguë, list seats and overhangs

`allocate.ts` implements Electoral Act 1993 ss 191–193 (as at 1 January 2026): qualification by 5% of valid party votes or one constituency win, Sainte-Laguë over the highest 120 quotients less independent winners, list seats as entitlement minus constituency seats, overhang, and list exhaustion. Pure TypeScript with plain-object input and output (Web Worker safe); exact integer comparisons; exact ties return `tie-at-cutoff`. Validated against official 2008–2023 results in `allocate.test.ts`.

See [docs/mmp-allocation-core.md](../../../docs/mmp-allocation-core.md) and [docs/mmp-rules-verification.md](../../../docs/mmp-rules-verification.md). Not forecasting logic: it takes party votes and electorate winners as given.

`seatLayer.ts` (Stage65) wraps the allocator per simulation draw: party-vote shares plus general and Māori electorate winners in; seats, Parliament size, overhang and threshold outcomes out; mergeable summaries with configurable blocs. `seatLayerStage.ts` adapts it to the pipeline's `MmpStage`. Internal only and not wired into any forecast; see [docs/stage65-seat-layer-design.md](../../../docs/stage65-seat-layer-design.md).
