# Stage76: a faster, numerically identical assembly

**Question.** Can the Stage73 assembly run fast enough for routine refreshes without changing any result or touching a frozen stage? At production size it needed about 5 core-hours.

**Answer.** Yes. The live assembly is now about **3.8× faster per seat**, and its outputs are unchanged to floating-point rounding (≤ 5e-15). Requested by James on 2026-10-07.

## Where the time went

Almost all of the assembly's time is the frozen Stage47 conditional-location solve (`scripts/uncertainty_expectation/integration.py`). For every simulated election and seat, it finds the offsets that keep the expected party or candidate shares equal to their conditional means under the Gaussian noise. It does this with Newton steps on a quasi-Monte-Carlo average over 512 to 16,384 nodes in up to 14 dimensions (one per minor party), plus two larger independent reference checks.

On the live inputs every row fails the frozen accuracy check at 512 and 2,048 nodes and passes at 8,192, so the 8,192- and 16,384-node evaluations take about 80% of the time. Inside them, the cost is the Gaussian-softmax expectation:
- an unoptimised `einsum` for the Jacobian;
- SciPy's softmax;
- reductions along the short party axis.

Altogether this was about 35 ms per draw per general seat: around 5 hours single-core at 8,192 draws × 64 seats.

## What changed

`scripts/nowcast_assembly/fastmath.py` computes the same expectation and Jacobian with:
- BLAS matrix products in place of the `einsum`;
- an in-place softmax with an upper-bound stabilising shift. Softmax is exactly invariant to the shift; the bound prevents overflow just as the per-element maximum did.

The assembly substitutes this function for the frozen one only while it runs (`fastmath.accelerated()`), the same module-level pattern Stage63 used. Unchanged:
- the frozen solver, its node schedules, tolerances, references and audits;
- the frozen file itself, which is untouched;
- every frozen pipeline, which keeps its attested CI reuse.

| | Frozen kernel | Accelerated |
|---|---|---|
| One seat, 128 draws (local party layer) | 4.46 s | 1.17 s |
| Development gate, 64 draws, 4 workers | 34 s | 17 s (includes the Māori fit and fixed overhead) |
| Production estimate, 8,192 draws × 64 seats | about 5 core-hours | about 1.3 core-hours (about 20 minutes on 4 cores) |

**Equivalence.**
- Expectation and Jacobian agree with the frozen function to below 1e-13, including near-zero shares (`scripts/tests/test_stage76_assembly_speed.py`).
- One seat's simulated local-party draws agree to below 1e-12.
- The Stage73 development gate and the Stage74 synthetic bank both reproduce under the existing `--check` comparisons.

## Not done

- **No change to the algorithm.** The node escalation, tolerances, Newton steps and reference checks are all as frozen. Skipping the 512/2,048 levels, or warm starts, would change results within solver tolerance, so they are not used.
- **No float32 arithmetic.**
- **No frozen stage, CI or registry change.**
