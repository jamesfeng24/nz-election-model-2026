# Stage37 frozen Other interface

Frozen before allocation; a conditional scenario, not a fine-party posterior.

## Inputs and categories

Eight primary Stage36 cases2014/2017/2020/2023 at14/56 days. Use exact archived current/election-day draws and average points. Fine roster/category IDs, target ballot keys and supported predecessor relationships come from Stage31 categoryRelationships. Extract only target membership/keys and **source** national shares, never target national votes/shares. Target roster is retrospectively established; its publication at each cutoff is not verified. Groups with no electorate candidate remain included. Shared Internet MANA/Freedoms NZ stay whole; constituent/whole-alliance continuity is not invented.

NAT/LAB/GRN/ACT/NZF/MRI map to their existing canonical categories. Model TOP is explicit from2017; benchmark TOP remains within independent coarse Other and must be allocated from its own inputs. Model explicit support is never copied to benchmark.

Preserved report mapping: NCP→conservative, UNF→unitedfuture, INM→internetmana (2014 only), MNA→manamovement (2017 only), INT→internetparty (2017 only), TOP→theopportunitiespartytop (2017 onward, benchmark only). A label absent from the target roster is not reassigned. Constituent MNA/INT observations do not allocate the2014 shared group; only the whole INM observation may do so. Unmapped reports are retained in the inventory with reasons. Rounded zeros are reported zeros, not structural absence. Threshold/censored/missing reports are not converted to point observations.

## Two policies

For each fine group within the system's Other:

**Primary recent-report/prior policy:** select Stage35 usable waves using verified publication or frozen field-end+5-day assumption, latest overlapping same-pollster wave; same-cycle field end within180 days. For a group with rounded observations, use their published decided-support working values. All-respondent values require reported nonresponse conversion; otherwise skip. Unknown denominators retain the Stage35 decided-voter assumption. Within each pollster weight by `2^(-age/30)*sqrt(min(n or750,1500)/1000)`; across reporting pollsters weight each mean by recency of its latest reporting wave. This is only a relative allocation weight, not an exact support constraint. Save every input value, bounds and normalized contribution. A reported zero may have zero primary weight; its uncertainty is exposed by sensitivity, not relabelled structural zero.

Without an eligible report use a supported continuing group's previous-election national share. An entrant or unavailable/nonpositive prior receives a fixed0.001 (0.1pp) neutral weight. This seed is an assumption, not evidence. No alliance predecessor is split. **Sensitivity:** use prior shares/0.001 seeds for every Other group, ignoring minor reports. These are the only two policies; no held-out scores choose them.

For weights `a_g≥0`, `π_g=a_g/Σa`, and each draw `x`, set `fine_g=x_Other π_g`; copy explicit categories exactly. If all reported weights are zero, use the predeclared prior/seed rule for the entire allocation and flag it. No rounding endpoints are imposed on posterior draws. Poll information already contributed to Stage36; this reuse is not independent evidence. Fixed conditional weights do not propagate allocation uncertainty within a policy. The two scenarios expose a finite assumption sensitivity, not exhaustive bounds or calibrated uncertainty.

Validate complete one-to-one roster accounting, finite simplex and explicit preservation at1e-12. Missing roster, duplicate keys, unsupported explicit category, or no recipient for positive Other raises/abstains with unresolved mass; never silently drops it. Zero Other allocates zero. Draw namespace/IDs remain paired and shared downstream. Output expected shares average allocated draws. No national/party-candidate renormalization or candidate filtering.

## Handoff

The national→Stage31 interface maps fine category IDs to ballot keys exactly. Later replay must apply the frozen local affinity and candidate formula per shared national draw, averaging transformed predictions; mean-input prediction is a different approximation. Keep roster/timing/entrant/conditional-allocation flags and Stage36 undercoverage. No candidate forecast, candidate score or replay here.
