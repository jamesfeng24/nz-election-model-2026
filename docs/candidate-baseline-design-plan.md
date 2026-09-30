# Stage 17 candidate-baseline design checkpoint: implementation plan

**Scope:** preserved-evidence audit, deterministic inventory, one proposed complete-share design, synthetic accounting tests and a validation protocol. No source acquisition, historical forecast/score, fitted parameter, 2026 prediction or integration.

PR #23 merged as `47c782f`, containing reviewed Stage 16 head `2251f6b`. This branch starts from that fetched merge with a clean checkout. Prior operational nulls remain historical decisions.

## Preserved inputs and inventory rule

Read the validated 2023→2026 crosswalk and synthetic notional **party** bounds, all 2023 Stage 7 election-local candidate occurrences, Stage 8 occurrence links/history and the separate Stage 13 primary-evidence sample. Verify all 72 registered official 2023 candidate voting-place files against their raw SHA-256 and the existing parser, including the cancelled Port Waikato table. Pin only these consumed raw source records; unrelated registry additions must remain admissible. Match source seats by official scope and electorate number, then use crosswalk predecessor codes. Never equate a target's newly numbered code with a source code or link people by a name.

For every one of the 64 general and seven Māori target seats, list predecessor seats, official unchanged/changed status, exact or bounded synthetic party rows, and every predecessor candidate occurrence as a **historical lead**. Label a 2023 candidate count geographically supported on the target boundary only if the crosswalk certifies identity membership and the source contest was held. A voting-place address cannot stand in for voter-residence geography; special and small-place rows are not allocatable to 2026 meshblocks. Keep inherited and Stage 13 identity tiers separate and do not infer a 2026 nomination or current career state. Inventory the missing 2026 slate, party-support scenario, turnout/validity and dated cutoff inputs explicitly.

## Design decision and synthetic proof

Compare no more than three approaches: geographic candidate-count transport, Stage 15 joint ballot routing and a direct party-anchored candidate-share composition. Propose the simplest complete-share rule that can represent every standing candidate, including independents, without treating absent personal evidence as zero. Freeze its equation, training-only nuisance parameter, shared input scenarios, abstentions and benchmark before a later scoring stage. Synthetic tests demonstrate nonnegative simplex totals, a replacement with unknown personal strength, an independent/entrant, changed geography, missing inputs, ballot denominator separation and outcome-field invariance. They are never historical results.

## Reproduction and stop

Store a machine-readable 71-seat inventory, consumed-source snapshot, contract and hashes under a Stage 17 checkpoint. A `--check` command must regenerate exact bytes from preserved inputs. Run focused Python/source/provenance checks and verify prior raw, model, identity and operational outputs have no diff from merged main. Record exact next implementation and abstention gates; open an unmerged PR for review. Stop before scoring or live forecast work.
