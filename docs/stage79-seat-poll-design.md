# Stage79: general-seat candidate polls in the nowcast, frozen pre-registration

**Status: frozen before any Stage79 error, fit or score was computed.** This file and [design-contract.json](../data/processed/seat-polls/design-contract.json) are the frozen checkpoint; the code reads every number from the JSON. Later edits are a change of design and must be recorded as a dated amendment with a reason.

**Authorization.** James approved the design on 2026-10-09 after the brief of the same day. Stage and decision numbers were allocated by the coordinator (Stage79, D117).

## The one question

> How far should a published general-seat candidate-vote poll move the model's candidate National/Labour balance for that seat, and by how much should it narrow that seat's uncertainty, given the historical error of such polls?

## What James approved, and what changed before scoring

James approved the design in the 2026-10-09 draft. Writing the code showed four points the draft did not settle. They are recorded here before any score exists.

- **A1. The model reference is the current model state.** The draft compared the poll with the model at the fieldwork week. Only the latest national state is saved (D106), so the earlier state does not exist. The poll is compared with the current model; the 6-week half-life carries the rest.
- **A2. Only polls led by National and Labour move a coordinate.** The model has one poll-sensitive coordinate, the National/Labour balance. A poll whose top two candidates are not those two (Auckland Central and Wellington Bays in 2026, Green-led) says little about that coordinate, and the Green-versus-Labour contest has no matching coordinate. These polls stay context. Eligibility depends on the poll, not on the result.
- **A3. Weight, decay and variance come from one rule.** The draft stated them separately. The seat deviation is treated as a stationary AR(1) in time with half-life 6 weeks, so the decay `rho` multiplies the weight and the posterior variance follows by the same formula. At `rho = 1` it equals the usual precision-weighted update.
- **A4. A seat poll never narrows the shared shift.** The seat's total SD is floored at the shared candidate-split SD (0.181). For an ordinary seat the cap-0.60 weight would otherwise cut the total SD below the shared part, which one seat's poll cannot identify.

Also fixed here: `p = share / 100` and `n` as published in the sampling variance; an assumed sample size of 400 where none is published, flagged and dropped in sensitivity S1; the Labour-aligned allowance of 0.12 SD (James 2026-10-09: Hutt South and Kāpiti are one Labour-aligned operator, one source); Mt Albert's two Curia polls three days apart merge into one before use.

## Inputs

- **Polls.** The general-electorate candidate-vote rows of the Wikipedia opinion-polling pages for 2014, 2017, 2020, 2023 and 2026, preserved unchanged in `data/raw/polling/seat-polls/2026-10-09/` and hand-transcribed to `data/source-plans/seat-polls/polls.json` (22 polls; every number is verified against the preserved table text by `scripts.seat_polls.data`). Rows are `aggregator_only`: James confirmed on 2026-10-09 that the 2026 numbers match the articles. The 2011 page was rate-limited and is not needed (the out-of-sample replay starts in 2014).
- **Model.** For historical seats, the Stage44 inventory record's out-of-sample candidate mean (conditional on the observed local party vote, so a strong reference), the Stage45 fold scales and the Stage67 primary flags with the D107 multipliers. For 2026 seats, the bank itself.
- **Sources.** A new standalone registry, `data/processed/seat-polls/source-registry.json`. `data/sources.json` is untouched.

## Scoring and the adoption rule

Leave one seat-election out: the inflation `c` is fitted on the other seat-elections' eligible polls and each held-out poll is scored on its own against the actual balance, for the model alone and for model plus poll. Adopt the layer only if the total log score gain is at least 1.0 nat and the model-plus-poll 80% coverage lies in [0.65, 0.95]. Otherwise the finding is `not_established`, the 2026 layer is left disabled and the polls stay context (they can still justify an exceptional flag or `extraSdPp`, not both).

## What is not done

No party-vote crosstabs; no Māori seat change; no D107 multiplier change; no house or sponsor lean fitted and no directional shift; no published probability; no frozen stage changed; `data/sources.json` untouched.

## Disclosure

Before the freeze the author had computed, from the same tables, a rough balance error for 12 historical polls (root mean square 0.28 against a sampling floor of about 0.12 at n=400) and seen the Stage67 flags. No model-versus-poll comparison had been computed. The fitted `c` will therefore agree with that crude figure; the evidence is the leave-one-out comparison. With about nine eligible polls in seven seat-elections, power is low and the adoption rule is deliberately strict.
