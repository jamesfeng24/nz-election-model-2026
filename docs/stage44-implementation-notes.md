# Stage44 implementation notes

2026-10-05. Numerical serialization resolved before evaluation; frozen statistical contract unchanged.

## Deterministic numerical serialization and cache checks

Before evaluation: exact run signatures cover inputs, code, dependency versions, seed and draw count. A completed case is reused only under that exact signature and a verified cache checksum. Each case is checkpointed. Same-runtime regeneration must reproduce its draw bytes. Across supported numerical platforms, regenerated floating diagnostics are compared at the already frozen absolute tolerance1e-10; integer IDs, category membership, chronology and all consumed-source hashes remain exact. Generated draw checksums identify the actual runtime archive and are verified locally; a platform's regenerated draw checksum is not claimed to equal a different platform's last-bit floating representation. No equation, statistical scale, solver gate or score tolerance is relaxed to address serialization.
