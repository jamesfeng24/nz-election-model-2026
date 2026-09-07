# Data layout and lifecycle

No election datasets are present. The source registry is empty.

`raw source → ingestion/transformation → validation → processed dataset → fitted model/output → website`

Raw directories: elections, polls, boundaries, candidates. Processed directories: elections, polls, electorates, split-votes, model. Empty .gitkeep files preserve layout only and are not datasets.

Never overwrite original source bytes. Keep new releases separately. If a resource is too large or unsuitable for Git, store an exact reproducible retrieval recipe, immutable resource identity and expected SHA-256, rather than committing a huge binary. Local rawPath identifies where verified bytes should be materialized; a path does not assert that the file is committed. Document exclusions in .gitignore per dataset when needed. Registry download instructions must not contain credentials. Do not collect data during stage 1.
