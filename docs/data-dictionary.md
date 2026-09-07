# Data dictionary

## Implemented contracts (version 1)

`src/types/contracts.ts` is authoritative. `SourceRegistrySchema` is a strict object with `schemaVersion: 1` and `sources: SourceRecord[]`; duplicate source IDs are rejected. `SourceRecordSchema` is strict and all fields are required. Field meanings are listed in [DATA_SOURCES.md](../DATA_SOURCES.md). IDs are case-sensitive opaque strings. Paths are repository-relative, must use the prescribed prefix, and reject traversal. Retrieval timestamps include timezone; the election/period field is descriptive text, not an inferred date. SHA-256 refers to exact original bytes, not parsed contents. `processingScript: null` means no processing script exists yet, not an empty script.

`Availability<T>` is a TypeScript discriminated union: `{status: 'unavailable', reason: string}` or `{status: 'available', value: T, sourceIds: string[]}`. It prevents absent results from masquerading as zero. It is not yet a runtime forecast schema.

## Deferred domain contracts

Party and candidate identity, boundary vintages and crosswalks, vote counts and denominators, polls and fieldwork, split-ticket observations, effect estimates, joint simulation draws and seat allocations remain unspecified. Define and review each before use. Do not conflate party vote with candidate vote, historical party identity with a current entity, or electorate identifiers across boundary vintages.

For each future field document type, unit, valid range, denominator, temporal/geographic coverage, source linkage and missing-value semantics. Prefer explicit null/reason over sentinel numbers. Distinguish proportion (0–1), percent (0–100), percentage-point change and integer counts; no convention for unimplemented domain schemas is implied here. Breaking changes require a schema version and migration instructions.
