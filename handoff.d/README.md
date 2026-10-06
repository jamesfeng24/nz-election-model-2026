# Pending handoff fragments

A PR does not edit CHANGELOG.md, PROJECT_STATE.md, DECISIONS.md, METHODOLOGY.md, DATA_SOURCES.md or the roadmap status table. It adds **one** file here, `YYYY-MM-DD-<stageNN-or-area>.md`, and the coordinator folds all pending fragments after a batch of PRs merges (`python3 -m scripts.fold_doc_fragments`, `--check` to validate). Unfolded fragments on main are part of the handoff record: read them with PROJECT_STATE.md. This README is never folded. Rules: AGENTS.md.

## Format

Sections start with a line `<!-- fold: NAME -->`. Every section is optional (omit one instead of writing "no change"), at least one is required, and nothing may precede the first marker.

| Section | Folded into | Content | Placement |
|---|---|---|---|
| `changelog` | CHANGELOG.md | one entry starting `## Stage53 — title, 2026-10-06` | appended at the end |
| `state` | PROJECT_STATE.md | one entry starting `# StageNN … — date`, in the existing shape (branch, commits/PRs, what changed and did not, counts, exact checks, limits, **exact next action**) | top, newest first, `---` separated |
| `decisions` | DECISIONS.md | one or more `## D084 — date — title` entries (number from the coordinator) | in D-number order; an existing number is an error |
| `methodology` | METHODOLOGY.md | one entry starting `## ` or `### ` | appended at the end |
| `sources` | DATA_SOURCES.md | one entry starting `## ` or `### ` | appended at the end |
| `roadmap` | docs/stage39-forecast-roadmap.md | table rows `\| StageNN \| question \| status \|` | a row with the same first cell replaces the existing row; a new one goes after the table's last row |

Fragments are applied in file-name order (the date prefix), and an entry whose heading is already present is rejected, so a fragment cannot be folded twice. Lines beginning with a git conflict marker (`<<<<<<<`, `=======`, `>>>>>>>`) are rejected, so an unresolved merge cannot be folded into the shared documents.

## Example

```
<!-- fold: changelog -->
## Stage99 — example, 2026-10-06

- What was added, what was not touched.

<!-- fold: state -->
# Stage99 example — review-ready, 2026-10-06

Branch `claude/project-thread-xxxxxx`. ... **Exact next action:** ...

<!-- fold: roadmap -->
| Stage99 | Example question | review-ready (PR #NN) |
```

Stage-specific docs (the stage's own `docs/*.md`) are edited directly in the PR, not here.
