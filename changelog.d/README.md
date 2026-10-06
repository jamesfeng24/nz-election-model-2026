# Pending CHANGELOG fragments

One file per PR: `YYYY-MM-DD-<stageNN-or-area>.md`, starting with a `## ` heading in the style of the entries at the end of `CHANGELOG.md`. `python3 -m scripts.fold_doc_fragments` appends them to `CHANGELOG.md` (oldest first) and deletes them. See AGENTS.md. This README is never folded.
