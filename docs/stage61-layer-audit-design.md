# Stage61: layer calibration audit, frozen pre-registration

**Status: frozen before any component ratio, PIT or coverage was computed by this stage.** This file and [design-contract.json](../data/processed/layer-audit/design-contract.json) are committed as a frozen checkpoint; the code reads every rule from the JSON. Later edits are a dated amendment with a reason, never a silent rewrite.

**What the author had seen before freezing (disclosed).** Stage46's stored seat coverage of the earlier-only Gaussian, the Stage47 interval tables (candidate National/Labour 90% coverage 0.956, composed widths) and the Stage47 nine-seat ablation. While drawing up the design the author also read the saved Stage45 descriptive moments for the 2023 candidate fold (seat variance 0.0615 balance, 0.1796 mass, 0.2217 within against fold seat SDs 0.309, 0.379, 0.591). No component ratio had been computed or tabulated and no PIT or share coverage had been recomputed. The rules below are fixed from the layer's structure, not tuned to those figures. Because every election was already used in development, this audit is descriptive; it adopts nothing.

**Māori seats (James, 2026-10-06 11:30).** Excluded by electorate type (`scope = maori`), never by party. The consumed frames hold general electorates only (321 party and 257 candidate records); the pipeline asserts this and reports the 35 Māori frame rows it does not score.

## The one question

> Besides the candidate National/Labour balance term, which uncertainty layers are too conservative, too tight or about right, and which is the next-best narrowing target?

Stage47 showed that removing candidate balance leaves about 21pp of composed National 90% width. This audit asks where that remainder is justified. It is diagnostic: there is no refit, no new scale, no national MCMC, no new source and no new pipeline.

## What is scored

The Stage45 tree has three independent Gaussian components per layer: N/L balance (`a`), major-versus-remainder mass (`b`) and within-remainder allocation (`u`), each with a seat scale and an election-shared scale, both estimated on earlier elections only. Layers: local party (conditional on the true national result; 2011–2023) and candidate (conditional on the true local result; 2014–2023). Scoring each coordinate separately isolates every layer component the harness defines, including candidate mass and within ("candidate excluding balance") and the shared parts.

For balance and mass the exact marginal law is logistic-normal, so the audit evaluates it analytically with the operational location, with no draws. The residual is `e = v - location(p, total_sd)` with `total_sd = sqrt(shared^2 + seat^2)`. Within each election the mean `h` is the shared effect and the leftover is the seat part. The seat ratio is the leftover second moment divided by the frozen seat variance: below 1 the frozen scale is larger than the data support. Within-remainder uses the Stage46 per-option residual records on the Stage45 estimator's own definition. The first fold of each layer (2011 local, 2014 candidate) is prior-only and is reported separately from the headline, which pools estimated folds with equal election weight.

Three views per component: (1) seat-scale ratio R with a seat bootstrap (2,000 draws, seed 61, 90% interval); (2) total-law PIT central 50/80/90 coverage and a ten-bin histogram; (3) the shared part per election against a chi-square reference band. Share-level coverage uses the stored Stage47 intervals for local party, candidate and composed (national, Labour and other options) with a seven-bin PIT from the stored bounds.

## Rules (frozen; details in the JSON)

- **Seat scale:** conservative if the 90% interval for R lies below 1 and R <= 0.95; too tight if above 1 and R >= 1.05; otherwise calibrated.
- **Shape flag:** reported when central-50 coverage is clearly above or below 0.5 even if R is near 1 (a heavy-tailed shape with a narrow centre looks conservative in the middle and tight in the tails).
- **Shared parts:** only four or five election replications exist. They are compared with a model reference band and never labelled calibrated or conservative.
- **Share coverage:** over-covers if the interval for 80% coverage lies entirely above 0.80.
- **Next-best target:** among components that are conservative and map to a Stage47 ablation policy, the largest approximate cut to the composed National 90% width at the point R and at the interval's upper end. The arithmetic is the plan's own, `W(m) = sqrt(W_full^2 - (1-m^2)(W_full^2 - W_without^2))`, from the nine-seat ablation, so it is indicative and non-additive.

## Limits recorded in advance

- Seats within an election share a common effect, so seat-bootstrap intervals understate uncertainty about the shared part, and three or four elections cannot calibrate a shared scale. The cheapest way to isolate a shared effect better is more elections, which no existing frame supplies; nothing new is acquired here.
- Composed coverage uses 512 cached national scenarios, so its coverage and widths carry finite-bank noise (Stage47).
- Stage47's ablation covers nine seats; mapping a component to a width effect is bracketed, not measured. The cheapest direct isolation is to extend the existing ablation harness to all 193 composed seats, which is a new simulation run and is not done here.
- The national layer is not scored. All elections were used in development: nothing here is out-of-sample.

## Not done

No adoption, no scale change (that is Stage60's separate question for balance), no variance predictor, no replacement or Māori work, no composed refit, no `data/sources.json` edit, no CI registry change.
