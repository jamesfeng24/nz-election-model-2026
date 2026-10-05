# Stage43 continuous S versus S+R comparison

Contract e9e93f6 was committed before calculation; predictions c7748a1 were committed before scoring. PR49 merge613ec78 and reviewedc75a4c4 ancestry verified from a clean checkout. No uncertainty work existed locally. No fitting, acquisition, new flow, MCMC or live predictions.

## Inputs and independent saved fits

Fixed primary expanding-window Stage33 constructed-input-trained fits, applied to observed target local party support. Every predecessor uses the frozen Stage42 party mass; supported source features are centered before weighting. Unsupported mass stays in the denominator, contributing neutral exponent. No outgoing residual transfer. All complete slates and ID orders reproduce Stage42; broad and strict joint predictions agree within1e-12.

| Election | Model | Training contests | Own kappa | Own theta S[,R] | Mean S | Mean R |
| --- | --- | --- | --- | --- | --- | --- |
| 2014 | S | 63 | 0.0123713559 | 1.53652676 | 0.5631932252 | 0.0083542282 |
| 2014 | joint | 63 | 0.0096754973 | 1.18944554, 3.32619913 | 0.5631932252 | 0.0083542282 |
| 2020 | S | 147 | 0.0111700054 | 1.16427713 | 0.5855241014 | 0.0097563410 |
| 2020 | joint | 147 | 0.0087855250 | 0.78195270, 2.93723435 | 0.5855241014 | 0.0097563410 |

Means are shared within each saved fold, verified explicitly. The models have independently fitted floors and S coefficients. S is never formed by setting joint R to zero. Strict changes R evidence only in the broad-trained joint fit; the S prediction remains identical. All selected fits are interior, numerically agreed Stage33 fits; no new optimum is estimated.

## Full-slate paired results

Errors in percentage points. **Joint-minus-S is negative when joint is better.** RMSE is the square root of mean contest MSE, not mean contest RMSE.

| Election | Model | Contests/candidates | MAE | RMSE | Candidate-equal MAE | Joint−S MAE | Unique correct | Actual-top-two margin MAE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2014 | S | 64/451 | 3.08799 | 5.42997 | 3.04674 | — | 49/64 | 15.27346 |
| 2014 | joint | 64/451 | 2.71727 | 4.84691 | 2.65580 | -0.37071 | 56/64 | 12.72562 |
| 2014 | joint_strict | 64/451 | 2.74832 | 4.91525 | 2.69118 | -0.33967 | 56/64 | 13.00304 |
| 2020 | S | 65/561 | 1.98530 | 3.52412 | 1.93870 | — | 52/65 | 9.04061 |
| 2020 | joint | 65/561 | 2.13245 | 3.62152 | 2.06144 | +0.14715 | 55/65 | 9.91397 |
| 2020 | joint_strict | 65/561 | 2.17520 | 3.70072 | 2.09877 | +0.18990 | 54/65 | 9.90619 |

All129 held general contests/1012 candidates constructed; zero general abstentions. The seven Māori seats per election remain coverage-only, preserving separate candidate-model requirements. No predicted ties in these samples; tie tolerance1e-12 and tied-set inclusion remain explicit in the machine output. Full-slate signed bias is essentially zero by conservation, an accounting check. Margins use predicted shares of the actual winner and runner(s), averaging tied runners without ID tie-breaking. Predicted-top-two gap errors are separately saved.

| Model | Contest-pooled MAE | Contest-pooled RMSE | Equal-election MAE | Equal-election RMSE |
| --- | --- | --- | --- | --- |
| S | 2.53237 | 4.57010 | 2.53664 | 4.57734 |
| joint | 2.42259 | 4.27361 | 2.42486 | 4.27831 |
| joint_strict | 2.45954 | 4.34591 | 2.46176 | 4.35058 |

Contest pooling weights elections64/129 and65/129; equal-election view weights each1/2 and takes root mean election MSE for RMSE. Joint pooled MAE gain over S is0.10977pp; strict0.07283pp. Equal-election gains0.11178/0.07488pp. These two MAEs and their dispersion cannot estimate future robustness.

## Frozen geographic strata

| Election | Band | Contests | S MAE | Joint MAE | Strict joint MAE | Joint−S |
| --- | --- | --- | --- | --- | --- | --- |
| 2014 | exact | 20 | 3.06242 | 2.69826 | 2.67844 | -0.36416 |
| 2014 | approximate_95 | 8 | 4.17528 | 4.24077 | 4.24077 | +0.06548 |
| 2014 | approximate_90 | 9 | 2.06495 | 1.69206 | 1.66759 | -0.37290 |
| 2014 | fallback | 27 | 3.12577 | 2.62169 | 2.71811 | -0.50408 |
| 2014 | cumulative95 | 28 | 3.38038 | 3.13898 | 3.12482 | -0.24140 |
| 2020 | exact | 34 | 2.25376 | 2.34245 | 2.39780 | +0.08869 |
| 2020 | approximate_95 | 7 | 1.72691 | 2.04183 | 2.00268 | +0.31492 |
| 2020 | approximate_90 | 6 | 1.48020 | 1.73963 | 1.86827 | +0.25942 |
| 2020 | fallback | 18 | 1.74706 | 1.90196 | 1.92414 | +0.15490 |
| 2020 | cumulative95 | 41 | 2.16381 | 2.29112 | 2.33034 | +0.12732 |

approximate95 and90 are exclusive added bands (95–100 and90–95 under guaranteed two-sided bounds); fallback denotes below90 or unresolved dominance, not a continuous-rule rejection. Cumulative95 includes exact. Comparisons are paired within each band, not transport-effect contrasts between different samples.

## Category diagnostics

One weight per member candidate; original valid-candidate denominator. Groups are not additive to whole-slate contest metrics. Bias is prediction minus actual. All models use the same category IDs.

| Election | Category | Candidates | S MAE/RMSE/bias | Joint MAE/RMSE/bias | Strict joint MAE/RMSE/bias |
| --- | --- | --- | --- | --- | --- |
| 2014 | national | 64 | 7.7369/9.3394/+7.6418 | 6.4970/8.3705/+6.0809 | 6.6016/8.4419/+6.1963 |
| 2014 | labour | 64 | 6.5764/8.1427/-5.8287 | 5.7092/6.7197/-4.8515 | 5.8885/7.0194/-5.0129 |
| 2014 | other_mapped | 289 | 1.4953/3.6347/-0.4805 | 1.3658/3.3769/-0.3350 | 1.3581/3.3721/-0.3248 |
| 2014 | affirmative_no_party_group | 34 | 0.7614/0.8037/+0.6711 | 0.6431/0.7443/+0.5330 | 0.6431/0.7449/+0.5330 |
| 2020 | national | 65 | 5.3216/6.4936/-4.7318 | 6.3837/7.3015/-6.0680 | 6.5329/7.4357/-6.0545 |
| 2020 | labour | 65 | 3.7009/4.7576/+2.3747 | 4.0726/5.2029/+2.8581 | 4.0499/5.1725/+2.8226 |
| 2020 | other_mapped | 376 | 1.2462/2.7671/+0.3360 | 1.1984/2.2842/+0.5051 | 1.2317/2.3966/+0.5084 |
| 2020 | affirmative_no_party_group | 55 | 0.5923/0.6523/+0.4884 | 0.4766/0.5501/+0.3402 | 0.4802/0.5528/+0.3438 |

Joint improves National and Labour in2014, while both worsen in2020; other mapped/no-group errors improve in both primary folds. Winner counts improve49→56 and52→55, but actual-top-two margin MAE improves15.27→12.73 in2014 and worsens9.04→9.91 in2020. Share accuracy remains primary; winners do not override the2020 share loss.

## Supported mass and no-history effects

| Election | Feature | Candidates | Contests | Candidate mean supported mass | Contest mean supported mass |
| --- | --- | --- | --- | --- | --- |
| 2014 | S | 330 | 64 | 0.69099 | 0.70645 |
| 2014 | R | 146 | 63 | 0.28826 | 0.29396 |
| 2014 | RStrict | 130 | 62 | 0.25884 | 0.26473 |
| 2020 | S | 318 | 65 | 0.53505 | 0.54265 |
| 2020 | R | 113 | 60 | 0.18484 | 0.18408 |
| 2020 | RStrict | 94 | 57 | 0.15249 | 0.15005 |

| Election | Contest R group | Contests | Broad joint−S | Strict joint−S |
| --- | --- | --- | --- | --- |
| 2014 | R_any | 63 | -0.37292 | -0.34138 |
| 2014 | R_none | 1 | -0.23174 | -0.23174 |
| 2014 | RStrict_any | 62 | -0.37741 | -0.34251 |
| 2014 | RStrict_none | 2 | -0.16295 | -0.25166 |
| 2020 | R_any | 60 | +0.12268 | +0.16899 |
| 2020 | R_none | 5 | +0.44076 | +0.44076 |
| 2020 | RStrict_any | 57 | +0.11535 | +0.15194 |
| 2020 | RStrict_none | 8 | +0.37370 | +0.46037 |

| Election | Fixed broad candidate group | Candidates | S MAE/RMSE/bias | Joint MAE/RMSE/bias | Strict joint MAE/RMSE/bias |
| --- | --- | --- | --- | --- | --- |
| 2014 | R_supported | 146 | 4.79599/7.24383/-0.54329 | 3.83799/5.97888/-0.21299 | 3.97141/6.19722/-0.23671 |
| 2014 | R_unsupported | 305 | 2.20940/4.43708/+0.26007 | 2.08990/4.23472/+0.10196 | 2.07834/4.21248/+0.11331 |
| 2020 | R_supported | 113 | 3.96633/5.94490/-1.31373 | 4.31244/5.73674/-1.21187 | 4.48157/5.93260/-1.21897 |
| 2020 | R_unsupported | 448 | 1.42726/2.63938/+0.33136 | 1.49366/2.78890/+0.30567 | 1.49775/2.80794/+0.30746 |

R candidate groups remain fixed to broad support for all branches; strict coverage is separately reported. Unsupported candidates can gain or lose through complete-slate normalization. Even a contest with no usable R can differ between S and joint because their own fitted floors and S coefficients differ. This comparison tests independent saved models, not an isolated R coefficient intervention.

## Individual gains, losses and influence

| Election | Direction | Contest | Joint−S MAE |
| --- | --- | --- | --- |
| 2014 | largestFiveGains | Mt Albert | -2.88210 |
| 2014 | largestFiveGains | Wellington Central | -2.83729 |
| 2014 | largestFiveGains | Rimutaka | -2.38352 |
| 2014 | largestFiveGains | Waimakariri | -2.24579 |
| 2014 | largestFiveGains | West Coast-Tasman | -2.15642 |
| 2014 | largestFiveLosses | Papakura | +1.50634 |
| 2014 | largestFiveLosses | Maungakiekie | +1.42566 |
| 2014 | largestFiveLosses | Rodney | +0.70532 |
| 2014 | largestFiveLosses | Rangitīkei | +0.63264 |
| 2014 | largestFiveLosses | Waitaki | +0.61242 |
| 2020 | largestFiveGains | Epsom | -3.61054 |
| 2020 | largestFiveGains | Taupō | -1.26176 |
| 2020 | largestFiveGains | Maungakiekie | -1.19756 |
| 2020 | largestFiveGains | Wellington Central | -0.75486 |
| 2020 | largestFiveGains | Waimakariri | -0.66841 |
| 2020 | largestFiveLosses | Napier | +1.91163 |
| 2020 | largestFiveLosses | West Coast-Tasman | +1.22128 |
| 2020 | largestFiveLosses | Taranaki-King Country | +1.20548 |
| 2020 | largestFiveLosses | Ōhāriu | +1.13962 |
| 2020 | largestFiveLosses | Ilam | +0.99322 |

2014: joint improves40, worsens24 contests; fixed-fit leave-one-contest-out mean-difference range [-0.4005050265322541, -0.33084721727442185]. All observations remain in primary scores.

2020: joint improves24, worsens41 contests; fixed-fit leave-one-contest-out mean-difference range [0.11957919574959075, 0.20586317080224964]. All observations remain in primary scores.

## Recommendation and limits

**Retain S+R preferred and S active.** Continuous transport does not establish consistent superiority: joint gains0.37071pp in2014 but loses0.14715pp in2020, and strict preserves this direction. The modest pooled gain and RMSE improvement support keeping the existing preference without discarding the simpler S alternative.2020 major-party/margin losses remain substantive. No new threshold or tuning follows.

Stage33–34 and Stage39 remain separate evidence with overlapping elections and different samples/information sets; their forecasts are not naively pooled here. Fixed earlier fits, conditional observed local party inputs, selected historical geography, algorithmic identity, uniform within-source party transport and only two reused environments limit interpretation. Population overlap does not reconstruct candidate votes or bound candidate error. θR is a log-intensity coefficient, not personal-vote retention. No causal or operational claim, electorate probabilities or uncertainty calibration.

Next separately authorized task: one coherent local-party/candidate uncertainty implementation around continuous transport and the retained mean-model preference, sharing national error once and making local/transport/feature/parameter uncertainty explicit. Official nominations and Māori electorate polling remain separately bounded. Stop further candidate mean-model experiments here.
