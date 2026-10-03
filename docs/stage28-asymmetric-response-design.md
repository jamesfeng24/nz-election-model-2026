# Stage28 — asymmetric response: definition and baseline feasibility

**Design checkpoint only.** PR34 was verified merged at `cb1ca8f`, containing reviewed `15baafc`. The plan/proposed specification was committed at `46b48d3` before this inventory and synthetic implementation. No historical anchor/response coefficient, regime label, prediction or error score is calculated. [Machine proposal](../data/processed/checkpoints/stage28-asymmetric-response-design/specification.json), [inputs/folds](../data/processed/checkpoints/stage28-asymmetric-response-design/input-inventory.json), and [plan](stage28-implementation-plan.md) are supplemental; original contracts and all operational nulls remain unchanged.

## Adopted development preference, with preserved evidence

The user now prefers **S-only for complete-share development**, prioritizing share MAE over deterministic winner counts. Baseline is a mandatory comparator. This is a **post-result development decision**: Stage27's all-fold screen still fails, its thresholds/results stay unchanged, and 2023 winner/margin deterioration remains a required diagnostic. Neither this preference nor a null operational selection estimates a real-world zero effect. Constructed-party-input testing, dated replay and joint probability validation remain necessary before deployment. Do not stack response/persistence/incumbency/replacement terms onto S.

## What the original preserved record establishes

The synchronized project `sources/` directory is empty. A bounded text audit of repository specifications/notes found no original conversation or passage choosing an asymmetric anchor, 50%, or a historical 51% crossing. That conversation cannot be verified locally. The present user prompt is authoritative; its two interpretations must remain distinct.

Preserved exact passages:

- [Stage1 intended estimator](statistical-specification.md), “Three independent candidate-vote estimators”: “Response of candidate/electorate vote to party-vote movement, including different National and Labour resilience”. This establishes a response question, not asymmetric recovery or a parity threshold.
- [Stage6 architecture audit](audits/stage6-architecture.md), “Viable2026 dependency and effect map”: “A transported seat-level premium is an assumption, not automatically a person's persistent effect.” It illustrates `C1=P1*+u0*+(β−1)(P1*−P0*)`, not an accepted strength anchor.
- [Stage7 specification](../data/processed/models/candidate-overperformance/specification.json), `interpretation`: “Descriptive residual, not candidate quality, persistent personal vote, causal effect or forecast bonus.”

A stable parity crossing does **not** imply asymmetric recovery. Even `C=a+βP` with a constant β below one has `C−P=a+(β−1)P`, potentially crossing zero. Both directional slopes can remain the same β. The synthetic check uses arbitrary β=0.6 and crossing 0.45 solely to demonstrate this algebra; neither number is a historical estimate or proposed fixed anchor.

## Compare the two mechanisms

| Interpretation | Quantity and classifier | Evidence/identification limitation | Decision |
|---|---|---|---|
| **A: candidate/seat support baseline B** | Initially toward if `ΔP(B−C0)>0`; B must represent a separately justified reference candidate/party-seat support state. | No preserved independently validated B exists. Setting B=C0 makes every starting state a tie. A historical mean, 50%, or normalized premium would introduce an unvalidated anchor. `C0` enters both `C1−C0` and `B−C0`: measurement, regression-to-mean and turnover can produce mechanical associations. | Defer. Stage26 links support identity research, not personal strength or complete careers. Replacements/unknown identity cannot inherit a person's B. A party-seat B would be a different population, requiring an explicit reference environment. |
| **B: party-level national parity environment A** | A national support environment where an explicitly defined expected **general-held aggregate candidate-minus-party share** is zero; classify national movement relative to A. | Only six election snapshots per party, at most five before a current holdout. Aggregate composition changes, slope/root instability and shared regimes limit interpretation. Local and national movements can disagree. | **Recommended primary proposal** because controls can be inventoried without an invented personal baseline and the classifier does not directly split on local C0. It tests a party-level environment hypothesis, not personal recovery. Adoption and fitting require separate authorization. |

National classification avoids the direct `ΔP(B−C0)` split but is not statistically independent of earlier candidate outcomes: its anchor would be learned from aggregates containing those outcomes. Generated anchors, overlapping transitions and repeated seats induce dependence. No causal or uniquely personal interpretation is available.

## Exact national-parity quantity and population

For party q/election t:

- `N[q,t] = official nationwide party votes / official nationwide valid-party votes`, including general and Māori electorates and valid specials. This is the **supplied national environment**, not the general-electorate party aggregate.
- `G[t]` contains **every held general contest** in the preserved election table, requiring one unique NAT and LAB candidate and ballot-party row in every contest. Missing/ambiguous evidence abstains on the aggregate; do not replace missing candidacy with zero or select the exact-seat subset.
- `C_G = Σ_G candidate votes / Σ_G valid-candidate votes`.
- `P_G = Σ_G party votes / Σ_G valid-party votes` on exactly the same contests.
- `g=C_G−P_G`; **not** `C_G−N`. Separate denominators are intentional. Neither is an average of local share percentages.

This is a ballot-weighted aggregate premium within each election, followed by **equal-election** anchor fitting. It differs from Stage7's matched general+Māori whole-contest leave-out normalization. No Stage7 offset is relabelled as strength.

General held coverage is **63/63/64/64/65/64** across 2008/2011/2014/2017/2020/2023, for both parties. In 2023 Port Waikato's cancelled candidacies are excluded from G. The matching party denominator omits **42,399** valid party votes from that contest; national N still includes them. The inventory records both denominators and the omitted mass rather than substituting the all-general or national total. Māori votes enter N but Māori candidate outcomes do not enter the proposed general premium or response. This different covariate population is explicit, not a denominator identity.

The twelve records are raw preserved aggregate **inputs**, represented as exact count/fraction identities, not anchor estimates. They reference election-local contest/occurrence IDs and official source records. Election fact year is known; exact fact dates are not newly ingested, publication by the historical forecast cutoff is unverified, and retrieval metadata remains separate in the pinned registry.

## Pre-fit chronology clarification

Initial proposal `46b48d3` allowed anchor snapshots through the source under both protocols while separating response training. The subsequent dependency audit, before any historical estimation, applies the stricter before-source cutoff to **learned anchor preprocessing** as well. This is explicitly recorded in the machine amendment history, not represented as the initial rule. Primary IDs/counts and the hypothesis are unchanged; separated anchor counts become0/1/2/3/4. No outcomes/scores were used to choose the change.

## Proposed earlier-only anchor and uncertainty gates

For each party/holdout, primary expanding-window uses all completed snapshots through its source election (strictly before target). The more-separated sensitivity uses snapshots strictly before the source election, so every learned anchor parameter respects its longer gap. Fit the same small relationship:

`g[t] = a + b (N[t] − mean_training_N) + error[t]`, with `A=mean_training_N−a/b`.

Use one equal-weight row per election, separate parties, unrestricted a/b, exact-rational OLS with an independent numerical check. **No estimation happens here.** No fixed 50%, full-sample crossing, threshold search, smoothing or external baseline.

Require at least **four completed election snapshots**, a rank-two column-scaled design with condition ≤1e6, national variation and observed premiums of both signs. Full and each leave-one-election-out fits must have finite, nonzero same-sign b (`1e−12` is only a computational zero guard), and crossings inside [0,1] and each fit's retained observed national-support range. Reject extrapolated crossings rather than using an unstable ratio. Three-snapshot delete-one fits are stability diagnostics, not separately passing the four-snapshot primary count gate.

The full/delete-one roots form one finite **anchor stability set**. It is not a confidence interval, exhaustive uncertainty set or calibrated predictive interval. Every training and holdout regime must agree across all roots, otherwise the whole party-fold comparison abstains. Five snapshots cannot establish reliable statistical root precision; even passing these conservative checks only supports a bounded development test.

Apply that **fold-frozen** set to both training and evaluation. Rolling historical anchors would change the meaning across rows and lose early labels; they are not another searched variant. A 2023 anchor may use completed 2020 evidence to label a 2011 training transition retrospectively. That is allowed earlier-only fitting for the 2023 conditional experiment, not evidence that the label existed before the 2011 election. No target candidate aggregate may estimate its own holdout anchor.

## Classification, including edge cases

Let `ΔN=N1−N0` and `x=ΔP_local`. The **initial direction** is primary:

`T=1` if `ΔN(A−N0)>0`; `T=0` if negative. Starting exactly at A and moving away is T=0.

- **Zero national movement:** neutral, exclude from the identical three-model common sample and report abstention, even if local support changes. No arbitrary neutral regime coefficient.
- **Zero local movement:** retain under an identified national regime; x and xT are zero, supplying intercept information only.
- **Overshoot:** initially toward remains T=1 after crossing A, even when the end is farther away. Crossing is a diagnostic flag. Ending-closer is explicitly a different, unused classifier.
- **Opposite local/national signs:** retain the national regime and flag disagreement. Do not silently reclassify by local movement. Any fitted relationship would concern local response in a national environment, not local motion back toward a candidate baseline.
- **Missing/unstable anchor or conflicting stability labels:** explicit whole-party-fold abstention on all three restrictions. No midpoint, zero anchor, imported coefficient or model-specific trimming.

Labels are shared within a party-transition environment. Many seat rows do not multiply regime replication.

## Proposed minimal future three-model comparison

Use identical permitted Stage25 two-sided exact general party-seat IDs, all winners/losers and candidate changes, without identity/status filtering. The core hypothesis is `ΔC=β_away x+δxT`, `β_toward=β_away+δ`, with expected ordering `0<β_away<1<β_toward`.

One **common party intercept α** is a declared nuisance adjustment in each restriction, preserving the slope question while accommodating average candidate-versus-party movement. Independently refit it in each model, on identical training IDs:

| Restriction | Equation for ΔC | Free parameters |
|---|---|---|
| β=1 control | `α+x` | α |
| Existing constant response | `α+βx` | α, β |
| Asymmetric interaction | `α+β_away x+δxT` | α, β_away, δ |

This is a new proposed experiment, not Stage6/27's original zero-intercept contract or a rewrite of their results. There is no source-victory interaction, status term, extra threshold or imposed slope ordering. OLS coefficients are unrestricted. Raw linear predictions would remain unclipped, with explicit out-of-range diagnostics; these are partial-party outcomes, not coherent full-slate shares or winner probabilities.

Each party fits equal party-seat rows, with at least five rows per free coefficient, **five nonzero local movements per regime** and **two distinct transition environments per regime**, a rank-three asymmetric design and column-scaled condition ≤1e6. Separately fit all restrictions from scratch with registered rational elimination; independently check OLS parameters/predictions within1e−8. Gate failure is abstention, not political evidence for/against the mechanism. Do not force two slopes from one regime.

### Coverage and chronology feasibility, per party

| Target | Exact evaluation seats | Primary training rows / environments | Separated training rows / environments | Primary / separated anchor snapshots |
|---|---:|---:|---:|---:|
| 2011 | 63 | 0 / 0 | 0 / 0 | 1 / 0 |
| 2014 | 20 | 63 / 1 | 0 / 0 | 2 / 1 |
| 2017 | 64 | 83 / 2 | 63 / 1 | 3 / 2 |
| 2020 | 34 | 147 / 3 | 83 / 2 | 4 / 3 |
| 2023 | 64 | 181 / 4 | 147 / 3 | 5 / 4 |

Primary expanding-window permits completed training targets ≤holdout source; more-separated requires <source. Both remain <target. IDs are copied/checked against Stage25; no new geography or approximate transport. All356 geography targets and35 Māori coverage-only seats remain visible. There are490 response records overall; no regime has been assigned and actual fit readiness is **not established**.

Only **2023 primary**, 64 seats per party, could meet the count gates. All other party-folds fail known counts. Even2023 might fail crossing/stability/regime/rank gates; no model is declared runnable. The more-separated sensitivity cannot meet the two-environments-per-regime count requirement on this panel. No two fitted holdouts can be promised, so a stable chronological mechanism claim is presently unsupported. Do not relax counts or acquire earlier elections automatically.

### Frozen proposed reporting and stopping

MAE/RMSE/bias use pp, equal party-seat records; RMSE takes the square root after the mean squared error. Pool by actual row counts, never give a20-seat election64-seat weight. Report each party/fold, common/added samples, coverage/abstentions, both slopes/ordering, out-of-range predictions and all-observation leave-one-contest-out score influence. No new subgroup search. Historical equations, party-input scenarios and samples stay separate from complete-share S.

Retain0.25pp MAE as a development diagnostic: pooled gain versus constant response, positive gain in every identifiable fold, no≥0.25pp RMSE deterioration, and at least two fitted holdouts for a consistency claim. Report against β=1 too; nuisance fairness applies. The present feasibility limit already prevents that two-holdout claim. Ordering without predictive improvement is insufficient; predictive gain without ordering does not confirm this mechanism. Nothing selects an operational response, causal effect or calibrated uncertainty.

## Executable scope, preservation and exact next decision

`stage28_design` reproduces only aggregate input/coverage/fold/provenance records. The small `asymmetric_response/design.py` contains classifier and supplied-estimate/rank **guards**, no fit/prediction routine. Synthetic fixtures demonstrate constant slopes with a parity crossing, initial direction/overshoot, shared-C0 dependence of interpretation A, unknown anchors, regime rank and outcome independence. They cannot validate the historical hypothesis.

**Decision for review:** adopt or reject the explicitly party-level national-parity mechanism and its guarded three-model contract. If adopted, separately authorize one gate-first earlier-only anchor/asymmetric test, limited to this existing exact panel; it may end with all fitted comparisons abstaining. Do not substitute a personal baseline or promise multi-fold validation. If the intended mechanism is specifically personal/seat recovery, clarification must specify an independent defensible B and replacement policy; no such evidence is currently identified.

Finite revised sequence:

1. This definition/feasibility checkpoint and independent review.
2. Separately authorized frozen asymmetric test if its definition/gates are defensible.
3. Expanded normalized-residual persistence with Stage26 broad primary and strict sensitivity, separately designed; no queue reopening.
4. Expanded Stage23 party vectors and baseline/S substitution, with each model's parameters fixed within substitution.
5. One small prespecified joint comparison once outputs/inputs are compatible. Individual failure is not an automatic veto, but all included coefficients must be jointly estimated; do not add separately fitted effects.
6. Dated replay, national reconciliation and parsimonious joint uncertainty, counting upstream national error once.

Earlier-election feasibility, full split-matrix expansion, V, tenure and replacement expansion remain deferred without a concrete decision benefit. All elections are reused development evidence; overlapping transitions and shared references remain dependent. No broad search or automatic salvage variant.

Reproduce:

```sh
python -m scripts.checkpoints.stage28_design --check --verify-preservation
python -m unittest scripts.tests.test_stage28_design -v
python -m unittest discover -s scripts/tests -v
python scripts/validate/source_files.py
```

Stage28 pins660 required registry records/raw bytes and required processed/design inputs. Unrelated registry additions are allowed; missing/altered/duplicate records and changed raw bytes fail. The separate stage-boundary preservation audit protects all1,377 earlier tracked data files, including Stage27 results and Stage25/26 contracts. It is distinct from historical stage-specific source dependencies. No source registration or historical adjudication changes. Final test/CI/PR state is in PROJECT_STATE.md and the PR.
