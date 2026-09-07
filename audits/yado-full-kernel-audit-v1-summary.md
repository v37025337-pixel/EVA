# YADO Full Kernel Audit V1

- Status: **FAIL_AUDIT**
- Commit: `597a53bb88da0d7763e7f739ff6ad7f367a339bf`
- Generation: `G2_CANDIDATE_TRCG_V1`; G3 started: `False`
- Frontier: `KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2`
- Runtime Python: 576; workflows: 40; JSON artifacts: 1093; ledger events: 294
- Canonical guard: PASS; ledger: PASS

## Findings
- **HIGH PHYSICAL_BRANCH_DIVERGENCE** — 1 historical branches retain commits not in active branch ancestry. Logical closure is not physical Git closure.

## Branches
- `origin`: active-only 6, branch-only 0, drift paths 0, branch-only paths 0.
- `main`: active-only 6, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-all-experience-tri-organ-genesis-v1`: active-only 6, branch-only 62, drift paths 11, branch-only paths 20.
- `yado-kernel-task-v37-repair`: active-only 79, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-main-experience-refresh-v1`: active-only 35, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-main-selective-admission-v1`: active-only 0, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-candidate`: active-only 79, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-ab`: active-only 79, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-audit`: active-only 79, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-digital-consciousness-v1`: active-only 79, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v30-runtime`: active-only 79, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v33-evolution`: active-only 79, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v35-training`: active-only 79, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v36-digital-consciousness`: active-only 79, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v37-digital-consciousness`: active-only 79, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v28-runtime`: active-only 79, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v29-cognitive`: active-only 79, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v7-meta-admission-shadow-v1`: active-only 15, branch-only 0, drift paths 0, branch-only paths 0.
