# YADO Full Kernel Audit V1

- Status: **FAIL_AUDIT**
- Commit: `5ad74a6d369dd7336e13bc6430d02a738da72a5f`
- Generation: `G2_CANDIDATE_TRCG_V1`; G3 started: `False`
- Frontier: `KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2`
- Runtime Python: 576; workflows: 40; JSON artifacts: 1094; ledger events: 294
- Canonical guard: PASS; ledger: PASS

## Findings
- **HIGH PHYSICAL_BRANCH_DIVERGENCE** — 1 historical branches retain commits not in active branch ancestry. Logical closure is not physical Git closure.

## Branches
- `origin`: active-only 0, branch-only 0, drift paths 0, branch-only paths 0.
- `deployment-vercel-runtime-v1`: active-only 0, branch-only 2, drift paths 0, branch-only paths 2.
- `main`: active-only 0, branch-only 0, drift paths 0, branch-only paths 0.
- `pre-history-closure-backup-20260910`: active-only 483, branch-only 0, drift paths 0, branch-only paths 0.
- `tmp-history-closure-20260910`: active-only 483, branch-only 0, drift paths 0, branch-only paths 0.
- `tmp-history-closure-20260910b`: active-only 483, branch-only 0, drift paths 0, branch-only paths 0.
- `tmp-history-closure-20260910c`: active-only 483, branch-only 0, drift paths 0, branch-only paths 0.
- `tmp-history-closure-20260910d`: active-only 483, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-all-experience-tri-organ-genesis-v1`: active-only 513, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-architecture-shadow-pre-rebind-20260907`: active-only 433, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-context-compaction-v1`: active-only 12, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-g2-causal-library-kernel-v1`: active-only 391, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-kernel-task-v37-repair`: active-only 648, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-main-experience-refresh-v1`: active-only 604, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-main-selective-admission-v1`: active-only 499, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-candidate`: active-only 648, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-ab`: active-only 648, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-audit`: active-only 648, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-digital-consciousness-v1`: active-only 648, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v30-runtime`: active-only 648, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v33-evolution`: active-only 648, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v35-training`: active-only 648, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v36-digital-consciousness`: active-only 648, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v37-digital-consciousness`: active-only 648, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v28-runtime`: active-only 648, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v29-cognitive`: active-only 648, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v7-meta-admission-shadow-v1`: active-only 584, branch-only 0, drift paths 0, branch-only paths 0.
