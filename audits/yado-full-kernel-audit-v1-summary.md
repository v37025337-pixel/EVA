# YADO Full Kernel Audit V1

- Status: **FAIL_AUDIT**
- Commit: `5452d9bb0f52f1d0e08159e52d77359f72ba5b17`
- Generation: `G2_CANDIDATE_TRCG_V1`; G3 started: `False`
- Frontier: `KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2`
- Runtime Python: 576; workflows: 40; JSON artifacts: 1094; ledger events: 294
- Canonical guard: PASS; ledger: PASS

## Findings
- **HIGH PHYSICAL_BRANCH_DIVERGENCE** — 4 historical branches retain commits not in active branch ancestry. Logical closure is not physical Git closure.

## Branches
- `origin`: active-only 0, branch-only 0, drift paths 0, branch-only paths 0.
- `main`: active-only 0, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-all-experience-tri-organ-genesis-v1`: active-only 29, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-architecture-shadow-pre-rebind-20260907`: active-only 29, branch-only 80, drift paths 11, branch-only paths 26.
- `yado-context-compaction-v1`: active-only 8, branch-only 480, drift paths 30, branch-only paths 38.
- `yado-g2-causal-library-kernel-v1`: active-only 8, branch-only 101, drift paths 13, branch-only paths 33.
- `yado-kernel-task-v37-repair`: active-only 164, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-main-experience-refresh-v1`: active-only 120, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-main-selective-admission-v1`: active-only 18, branch-only 3, drift paths 4, branch-only paths 0.
- `yado-rc8-candidate`: active-only 164, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-ab`: active-only 164, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-audit`: active-only 164, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-digital-consciousness-v1`: active-only 164, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v30-runtime`: active-only 164, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v33-evolution`: active-only 164, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v35-training`: active-only 164, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v36-digital-consciousness`: active-only 164, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v37-digital-consciousness`: active-only 164, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v28-runtime`: active-only 164, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v29-cognitive`: active-only 164, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v7-meta-admission-shadow-v1`: active-only 100, branch-only 0, drift paths 0, branch-only paths 0.
