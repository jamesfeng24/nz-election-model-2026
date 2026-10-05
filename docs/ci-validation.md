# Bounded dependency-aware validation

2026-10-05. The user authorized local resumable commits instead of routine intermediate pushes, one conservative historical CI reuse path, and full main/manual validation. This changes validation orchestration, not statistical contracts, tolerances or results.

## What remains mandatory

`check` and `python` retain their names and read-only permissions. Frontend checks, **full standard unittest discovery**, source validation, and every standalone pipeline outside Stage39 still run. No behavioural test is omitted. No national inference, hosted model cache, whole-run cache or schedule is introduced. Main pushes and `workflow_dispatch` always run full. PR concurrency cancels only superseded runs in the existing PR/event group. The first PR changing this workflow/selection/registry runs full.

The semantic registry identifies one inspected Stage24 pure archival regeneration method, **kept full because its dependency closure is unregistered**. It explicitly identifies Stage39's bounded saved-conditional compatibility test as behavioural, despite `reproduce` in its name. Classification is based on inspected bodies and source fingerprints, not test names or timings. New tests default to behavioural; changing or adding any test forces full standalone validation. Ordinary `python3 -m unittest discover -s scripts/tests -v` is unchanged. This is a small semantic foundation, not a classification of the whole historical suite.

## The only safe subset: Stage39

The five existing Stage39 `--check` commands remain the unchanged full path. A routine PR can replace those commands with `python3 -m scripts.validate.ci_stage39 --check` only when:

1. The PR base commit and a merge base are available; comparison uses that merge base, with missing/disconnected history forcing full.
2. The reviewed fingerprint matches all prior code, exact Stage39 consumed/protected/output files and Python environment contracts.
3. Prior successful Linux evidence remains intact, including the tested head and completion markers.
4. Every changed path belongs to an explicitly reviewed unaffected scope. Unknown paths, raw/required output changes, shared code, dependency files, CI/registry/checkpoint-policy changes, and changed/new tests force full.

The dependency list is deliberately a conservative superset: every Python file in the validated historical tree, exact Stage39 input/preservation contracts and outputs, Python version/requirements, and the deterministic Stage39 report. Reuse also requires the attested Linux x86-64/Ubuntu 24.04/Python 3.12.2 runtime; a different runtime forces full. New Stage45 code/output paths are explicitly separate consumers; modifications to previously validated shared helpers still force full. Other unknown/new pipelines are not assumed independent. Unrelated source registrations may conservatively force full; no old consumed-source contract is changed.

The reuse attestation refers to actual successful Linux Verify runs [37275901476](https://github.com/jamesfeng24/nz-election-model-2026/actions/runs/37275901476) and [37275906724](https://github.com/jamesfeng24/nz-election-model-2026/actions/runs/37275906724), head `5283e7c85bab23d31176c2160964672b5e0cca3f`, Python 3.12.2/Ubuntu 24.04.5. The preserved full first-run log is checksummed; dependency hashes were reconstructed from that Git tree. A freshly generated output manifest is **not** evidence that reconstruction previously passed.

The lightweight path checks those exact bytes, consumed/protected sources, construction/evaluation seals, construction signature, all six case/sample/fit/schema contracts, all 48,000 complete fine national vectors, complete candidate-share simplexes/intervals, and present optional runtime-cache hashes. It requires no runtime cache. It does not regenerate candidate draws or claim new independent arithmetic. Missing/stale/corrupt fingerprints fail closed. No registry entry can silently turn an unchecked pipeline into reusable output.

## Bounded savings and use

The saved Linux log places Stage39 construction at 07:13:42→07:16:05: approximately **143 seconds**. Verification has additional bounded reconstruction cost. The new integrity path took **1.697 seconds locally** (different hardware; not a matched Linux benchmark). Stage39 unit tests do not contain that full 8,000-draw hotspot and remain always-on. Other slow historical stages still run; this is a limited saving, not a promise of fast complete CI.

- Full: ordinary main push or manual **Verify** dispatch; PRs touching protected/unknown scopes automatically receive it.
- Explicit full selection: `python3 -m scripts.validate.ci_selection --full`.
- Selection explanation: `python3 -m scripts.validate.ci_selection --base <available-base-sha> --event pull_request`.
- Lightweight sealed check: `python3 -m scripts.validate.ci_stage39 --check`.
- Full reconstruction: existing `python3 -m scripts.polling.candidate_integration.{inventory,construction,evaluation,verification,report} --check` commands, individually in workflow order.

Versioned selection/attestation files belong to review. New dependency closure support requires inspecting actual producers and inputs and an observed successful full Linux run; it is not inferred from a new manifest assertion. This stage does not optimize other pipelines or weaken their preservation checks. Local uncommitted work is not a remote handoff: checkpoint state must distinguish local commits from pushed commits, and pushes occur at review/final validation or an explicitly requested remote checkpoint.
