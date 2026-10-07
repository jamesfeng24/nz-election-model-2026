# Stage73: the live nowcast draw bank (Python side of the assembly)

**Question.** Can the live 2026 chain produce one deterministic draw bank in which every row carries the national party vote and all 71 winners from a single national draw, and refuse to run when an input is missing?

**Answer.** Yes for the engine. On today's live inputs, the bank is correctly **blocked**:
- **General seats:** all 64 are unavailable, because the roster is pending (Stage50) and the classification file does not exist.
- **Māori seats:** four are unavailable because they are unpolled (James's decision is pending).
- The three polled Māori seats are simulated.

Approved by James on 2026-10-07. That approval covered:
- the plan;
- splitting "Other" by each seat's own 2023 mix;
- Stage74 as a separate PR.

## What it builds (`scripts/nowcast_assembly/`)

| Step | Module | Behaviour |
|---|---|---|
| National adapter | `national.py` | Reads only `lastDataSupport` from the configured fit and checks the fit's status, cutoff and file hash. It maps the eight categories to 2026 groups through `national.categoryMap`; "Other" stays one national bucket. A seeded permutation selects a power-of-two subset of the 8,000 draw ids. Naming `electionDay`, or not forbidding it, fails. |
| 2026 layer noise | `streams.py` | Uses the Stage46 key structure (shared election keys plus seat keys) and a scrambled Sobol bank over a **2026 registry built from the 2026 rows**, seeded from `simulation.seedNamespace`. The frozen historical registry is not touched. The bank is substituted the way Stage63 does it, so the Stage47 inversion runs unchanged. |
| Local party layer | `general.py` | `local_vectors` → `invert`, with the Stage72 2026 local-party scales and the configured baseline (population-flat Stage41/64 now, Stage69 later). The fine national vector gives core parties their own category share. "Other" is split by 2023 national shares, so inside each seat it follows that seat's own 2023 mix. 2023 parties with no documented 2026 continuation keep their local mass but have no candidate destination. |
| Candidate layer | `general.py` | `candidate_inputs` → `candidate_vectors` → `invert`. It uses the Stage42 continuous S/R features of the configured roster and the latest saved S+R joint fit. The Stage72 candidate scales apply, with **only the balance seat scale multiplied** by the D107 class multiplier (0.60 / 1.00). The winner is the per-draw argmax. |
| Māori seats | `maori.py` | Re-runs the Stage66 registered default (fit + simulate) at the bank's draw count. Polls are mapped to 2026 boundary ids. Party codes map to 2026 groups; IND is an independent, and an unknown code fails. Unpolled seats are `unavailable` while `maori.unpolledSeats` is pending. Draws are independent of the national draw, as in the Stage66 default. |
| Bank and gate | `assemble.py`, `run.py` | Lists all 71 seats in frame order, each either `simulated` (one winner per row) or `unavailable` with a reason. The gate checks are listed below. Seats can run in forked workers; output is identical for any worker count. |

The gate checks:
- `configComplete`
- `provenanceLive`
- `nationalStateKey`
- `oneDrawIdPerRow`
- `partyVoteSimplex`
- `universe71`
- `everySeatSimulatedOrExplicitlyUnavailable`
- `allWinnersPresent`
- `classificationMultipliers`

**National uncertainty enters once.** Row *i* of the bank is national draw *i* for the MMP party vote and for every general seat. The shared layer keys are common to all seats, so a row is one simulated election.

**Runner.**
- `python -m scripts.nowcast_assembly.run [--check]` writes or reproduces the development gate report `data/processed/nowcast-assembly/development-gate.json` at 64 draws. The report contains statuses, blockers, checks, the reconciliation diagnostic and the bank digest, but never the bank or a forecast.
- `--require-complete --draws N --bank PATH` is the production path. It refuses unless the config is complete and every gate check passes.

## Results on live inputs (64 development draws)

- **Gate:** not publishable.
  - **Failed:** `configComplete` (6 pending fields) and `allWinnersPresent` (68 unavailable seats).
  - **Passed:** every structural check.
- **Blockers:**
  - 64 general seats: roster pending (Stage50);
  - 4 Māori seats: unpolled, waiting on James.
- **Reconciliation diagnostic.** The party-vote-weighted mean of the general-seat local party means differs from the national mean by at most **0.37pp** (National +0.37, Green −0.25, Labour −0.17; the others are within 0.09pp). The baseline is population-flat and is replaced by Stage69. The tolerance is set with the publication gate in Stage74.
- **Determinism:** the bank digest is identical for 1 and 4 workers and on reproduction.

## Decisions, limits and things not done

- **Candidate mean parameters.** No S+R joint fit includes 2023 in its training. The config points at the latest saved fold (`primary`, target 2023, trained 2014–2020, fit `aca80252…`), which matches the feature centring Stage42 used for the 2026 features. A refit including 2023 was not made: it would be a new estimate with new centring, so it is a separate question.
- **Runtime.** The frozen Stage47 within-remainder location solve dominates: about 35ms per draw per general seat on one core. At 8,192 draws that is about 5 hours single-core, so production runs need workers. Precision (Stage63) sets the draw count.
- **Not done:**
  - no snapshot or forecast;
  - no classification entries (a draft for James is in `docs/general-seat-classification-2026-draft.md`);
  - no Stage69/70 cutover;
  - no draw count, blocs or rules version;
  - no Stage56 output B;
  - no change to frozen stages or the historical noise registry.
- **Stage74** (TypeScript, separate PR) reads the bank into the Stage65 seat layer. It adds the 80% seat intervals, effective-sample Monte Carlo SE and the export v2 completion.

## Reproduction

```
python3 -m scripts.nowcast_assembly.run --check
python3 -m unittest scripts.tests.test_stage73_nowcast_assembly
```
