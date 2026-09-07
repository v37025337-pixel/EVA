# YADO Full Kernel Audit V1

- Status: **FAIL_AUDIT**
- Commit: `475ac0a0cbdeecb808d3d80a4f7a33d9326b20e1`
- Generation: `G2_CANDIDATE_TRCG_V1`; G3 started: `False`
- Frontier: `KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2`
- Runtime Python: 581; workflows: 40; JSON artifacts: 1114; ledger events: 294
- Canonical guard: PASS; ledger: PASS

## Findings
- **HIGH PHYSICAL_BRANCH_DIVERGENCE** — 1 historical branches retain commits not in active branch ancestry. Logical closure is not physical Git closure.

## Branches
- `origin`: active-only 81, branch-only 0, drift paths 0, branch-only paths 0.
- `main`: active-only 81, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-all-experience-tri-organ-genesis-v1`: active-only 102, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-architecture-shadow-pre-rebind-20260907`: active-only 22, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-kernel-task-v37-repair`: active-only 237, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-main-experience-refresh-v1`: active-only 193, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-main-selective-admission-v1`: active-only 91, branch-only 3, drift paths 4, branch-only paths 0.
- `yado-rc8-candidate`: active-only 237, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-ab`: active-only 237, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-audit`: active-only 237, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-digital-consciousness-v1`: active-only 237, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v30-runtime`: active-only 237, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v33-evolution`: active-only 237, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v35-training`: active-only 237, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v36-digital-consciousness`: active-only 237, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v37-digital-consciousness`: active-only 237, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v28-runtime`: active-only 237, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v29-cognitive`: active-only 237, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v7-meta-admission-shadow-v1`: active-only 173, branch-only 0, drift paths 0, branch-only paths 0.
