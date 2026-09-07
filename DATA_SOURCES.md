# Data sources and provenance standard

**No external election datasets have been collected.** `data/sources.json` is an empty, version-1 registry. Software documentation links are not election datasets.

Every future external dataset must have a SourceRecord validated by `src/types/contracts.ts`, recording:

| Field | Requirement |
| --- | --- |
| schemaVersion / id | Version 1; stable unique source identifier |
| organisation | Source organisation |
| url | Exact source URL |
| dateOrElection | Applicable date, period or election |
| resource | Exact file, table, sheet, release or resource used |
| retrievedAt | Retrieval timestamp, ISO 8601 with timezone |
| rawPath | Original file under data/raw/ |
| processingScript | Script under scripts/; null only while unprocessed |
| limitations | Nonempty list of known limitations; explicitly say if assessment is pending |
| sha256 | Lowercase SHA-256 of original bytes |
| licence | Reuse terms or explicit unresolved status |

Keep raw bytes unchanged and retain each acquired version separately. Never silently replace a release. Record redirects, manual retrieval steps, sheet/range selections and access restrictions where relevant in source-specific notes. Verify rights before redistributing restricted material. Processed outputs must trace to source IDs, exact input checksums and documented scripts. A non-null script path must point to a real script before publishing its outputs; runtime schema validation alone does not verify filesystem existence or remote authenticity.

Unknown values must stay unknown; do not infer evidence from plausible-looking values. Synthetic test metadata lives only in tests, uses example.org, and must never enter the source register or model inputs.
