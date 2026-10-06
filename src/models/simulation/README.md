# Seeded joint probabilistic forecasts

Pipeline skeleton only (see `docs/export-contract.md`): stage interfaces (`pipeline.ts`), seeded per-draw PRNG (`prng.ts`), aggregation, snapshot export (`exporter.ts`) and Web Worker protocol (`worker.ts`, `simulation.worker.ts`). The only stage implementations are `syntheticStages.ts`, labelled placeholders for fixtures; no project model is implemented here. Keep statistical logic independent of React and the DOM. Document inputs, outputs, estimands, uncertainty, validation and overlap with other effects before implementing a real stage.
