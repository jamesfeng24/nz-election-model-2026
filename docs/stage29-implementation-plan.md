# Stage29 implementation plan — before calculation

Verified Stage28 PR35 merged at44fab0a containing reviewedacafef0; clean main synchronized; branch `stage/29-asymmetric-response-test`.

1. Pin the Stage28 aggregate inputs/guards, Stage25 exact IDs/folds and Stage27 response adapter records. Commit samples and this extension before any anchor or coefficient calculation.
2. Reuse rational normal equations and independent NumPy least squares, with existing scaled-SVD rank/condition gates. Estimate centered equal-election anchors full and delete-one snapshot; audit anchors when at least four snapshots exist even if response environment counts already fail. Never substitute an anchor.
3. Generate chronological construction separately from full-panel descriptive construction. Anchor or classification failure abstains on the whole case; no favorable trimming. Apply the asymmetric regime/rank gate to all three restrictions on identical records, each independently refitted intercept. Commit construction before scoring.
4. For valid full-panel setup only, freeze its anchor/classifications and remove each complete transition from response rows. Refit the same three restrictions and reapply all gates. Never score deleted transitions; never recompute anchors in these refits.
5. Independently verify anchor/response arithmetic and errors; add synthetic and full-adapter outcome-boundary tests. Deterministically regenerate companions, protect consumed records/raw bytes and all prior data, run configured Python/source checks and CI. Document findings, push and open an unmerged PR.

No acquisition, new threshold/anchor, interaction extension, identity queue, persistence fit or operational change. Stage28 is preserved; the full-panel/deletion view is newly authorized descriptive work, not part of its original freeze. Synthetic examples remain outside historical outputs.
