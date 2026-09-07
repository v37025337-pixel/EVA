# YADO Full Kernel Audit V1

- Status: **FAIL_AUDIT**
- Commit: `5e6e8be5e8dec421143ddfc46c881d2eeda6bb88`
- Generation: `G2_CANDIDATE_TRCG_V1`; G3 started: `False`
- Frontier: `KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2`
- Runtime Python: 576; workflows: 40; JSON artifacts: 1093; ledger events: 294
- Canonical guard: PASS; ledger: PASS

## Findings
- **HIGH PHYSICAL_BRANCH_DIVERGENCE** — 2 historical branches retain commits not in active branch ancestry. Logical closure is not physical Git closure.

## Branches
- `origin`: active-only 2, branch-only 10, drift paths 8, branch-only paths 1.
- `main`: active-only 2, branch-only 10, drift paths 8, branch-only paths 1.
- `yado-all-experience-tri-organ-genesis-v1`: active-only 13, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-kernel-task-v37-repair`: active-only 148, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-main-experience-refresh-v1`: active-only 104, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-main-selective-admission-v1`: active-only 0, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-candidate`: active-only 148, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-ab`: active-only 148, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-audit`: active-only 148, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-digital-consciousness-v1`: active-only 148, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v30-runtime`: active-only 148, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v33-evolution`: active-only 148, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v35-training`: active-only 148, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v36-digital-consciousness`: active-only 148, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v37-digital-consciousness`: active-only 148, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v28-runtime`: active-only 148, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v29-cognitive`: active-only 148, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v7-meta-admission-shadow-v1`: active-only 84, branch-only 0, drift paths 0, branch-only paths 0.
