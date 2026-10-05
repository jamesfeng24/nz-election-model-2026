# Stage45 producer dependency audit

2026-10-05. The final audit found that Stage45 cache identity pinned its five new simulation producer modules but omitted some imported historical helpers. This is a provenance/cache invalidation defect, not a statistical or arithmetic error.

The input contract now enumerates the static repository import closure of those producers:17 historical helpers, including the unchanged Stage44 comparator construction, shared random streams/transforms, Stage39 national/local/candidate adapter, complete-party construction and Stage33 numerical kernel. Their bytes were independently compared with merged Stage44 `35f88067ace2fa20a8f6e0f729a18d309a1f565c`; every helper is unchanged. Actual consumed-code bytes enter the cache signature, so changing a helper changes identity even before the frozen contract rejects it. This does not couple the run to unrelated source-registry additions.

Fresh draw construction under the expanded signature and evaluation/audit/independent verification reproduce all earlier numerical values exactly. A recursive comparison of convergence, construction, evaluation, mean audit and independent verification permits only cache signature/path changes: zero changed numbers, scores, IDs or tolerances. No old cache was relabelled as newly validated; new companions were reconstructed. Prior Stage44 and earlier artifacts remain unchanged.

Run manifests still distinguish deterministic post-processing from full reconstruction. Platform-specific compressed cache bytes are checked against each local runtime manifest, while portable metadata/numerical comparisons retain the original tolerance. The new dependency test changes a real consumed helper hash and requires both signature invalidation and provenance rejection.
