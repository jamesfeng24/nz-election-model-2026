# Stage44 implementation notes

2026-10-05. Numerical serialization resolved before evaluation; frozen statistical contract unchanged.

## Deterministic numerical serialization and cache checks

Before evaluation: exact run signatures cover inputs, code, dependency versions, seed and draw count. A completed case is reused only under that exact signature and a verified cache checksum. Each case is checkpointed. Same-runtime regeneration must reproduce its draw bytes. Across supported numerical platforms, regenerated floating diagnostics are compared at the already frozen absolute tolerance1e-10; integer IDs, category membership, chronology and all consumed-source hashes remain exact. Generated draw checksums identify the actual runtime archive and are verified locally; a platform's regenerated draw checksum is not claimed to equal a different platform's last-bit floating representation. No equation, statistical scale, solver gate or score tolerance is relaxed to address serialization.

## Concrete Linux CI cache correction

Final-head d311690 CI passed construction's numerical reproduction but failed evaluation because it compared a newly generated Linux draw archive to the committed macOS archive checksum. The frozen contract already distinguishes portable numerical equivalence from exact runtime archive identity. The corrected shared cache reader verifies the actual local archive checksum against its exact-signature runtime manifest, then verifies that manifest's case IDs, scales, location metadata and means against the committed case at the unchanged1e-10 tolerance. Evaluation, precision and independent audit consume that locally verified archive. Corrupt local bytes or changed case metadata still fail. No equation, scale, score, mean model, tolerance or statistical gate changes; same-platform score values are independently checked unchanged. The failed CI attempt remains recorded.
