# Stage36 implementation plan — 2026-10-04

Verified reviewed9f4ff02 and merge19be252 in main; clean checkout and branch `stage/36-national-polling-backtest`. No new political sources or candidate calculations.

1. Freeze the mathematical implementation contract and input/coverage manifests before inference. Preserve Stage35; explicitly resolve changing category coordinates, observation operators, cycle endpoint roles and benchmark projection.
2. Isolate the pinned NumPyro/JAX environment, lock actual dependencies, and validate runtime, stable interval arithmetic, compositional transforms, gradients and synthetic information flow.
3. Implement one generative model and one benchmark. Save exact run signatures, independently seeded four-chain attempts, complete diagnostics and joint current/election-day draws before evaluation. Resume exact compatible completed attempts; never rerun MCMC for tables.
4. Run eight primary cases and two one-factor sensitivities; verified-only is a separate coverage audit/fit only with usable current-cycle evidence. Apply only the one frozen numerical retry. Keep failures visible.
5. Independently verify deterministic post-processing and scoring; preserve all earlier bytes. Report every attempted case, uncertainty/availability limitations and national-only findings, then unmerged PR/final CI. No candidate replay, fine Other allocation, new model family or live2026 output.

The objective/priors/inference gates are unchanged. The implementation contract, rather than accuracy, decides remaining mathematical details. Candidate alternatives remain separate under D067.
