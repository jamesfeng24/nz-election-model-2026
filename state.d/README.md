# Pending PROJECT_STATE fragments

One file per PR: `YYYY-MM-DD-<stageNN-or-area>.md`, starting with a `# ` heading in the existing newest-first shape of `PROJECT_STATE.md` (branch, commits/PRs, what changed and did not, counts, exact checks, limits, exact next action). `python3 -m scripts.fold_doc_fragments` prepends them to `PROJECT_STATE.md` (newest first, `---` separated) and deletes them. See AGENTS.md. This README is never folded.
