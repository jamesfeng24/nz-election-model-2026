# Stage39 implementation plan

1. Verify merged Stage38 ancestry and preserve the clean checkout; freeze consumed hashes, exact saved-fit IDs and full geography exclusions.
2. Adapt raw gauss categories with a small reusable reader. Preserve explicit Conservative/UnitedFuture and any explicit TPM/TOP. Use Stage37's recent-report/prior and prior-only policies only for remaining Other; reuse existing cutoff/weight arithmetic for nonexplicit2020MRI.
3. Reuse fixed Stage33 primary baseline/S/S+R parameters and source-only centered features. Batch every cached joint draw through the complete Stage31 affinity roster, then the complete candidate slate. Preserve shared draw IDs and average transformed predictions.
4. Seal and commit construction before scoring. Reuse Stage33 metric arithmetic on identical162-contest samples and matching conditional context. Independently recalculate representative vectors and paired errors.
5. Focused synthetic/actual-path tests, deterministic cache reproduction, source/preservation checks, configured final checks. Document findings, concrete forecast dependencies and provisional choices; push an unmerged PR and verify final CI.

No inference, coefficient tuning, owned-model replay, candidate R-only replay, live forecast or acquisition. The proposed adapter and tests remain independent of GPL statistical code; raw gauss outputs retain pin, attribution and licensing metadata. A bounded independent agent audits/tests correctness only.
