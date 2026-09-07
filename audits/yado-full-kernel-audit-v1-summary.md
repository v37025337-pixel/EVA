# YADO Full Kernel Audit V1

- Status: **FAIL_AUDIT**
- Commit: `02d413baba201a4772b626566f73a228a8328458`
- Generation: `G2_CANDIDATE_TRCG_V1`; G3 started: `False`
- Frontier: `KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2`
- Runtime Python: 581; workflows: 40; JSON artifacts: 1115; ledger events: 294
- Canonical guard: PASS; ledger: PASS

## Findings
- **HIGH PHYSICAL_BRANCH_DIVERGENCE** — 1 historical branches retain commits not in active branch ancestry. Logical closure is not physical Git closure.

## Branches
- `origin`: active-only 87, branch-only 0, drift paths 0, branch-only paths 0.
- `main`: active-only 87, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-all-experience-tri-organ-genesis-v1`: active-only 108, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-architecture-shadow-pre-rebind-20260907`: active-only 28, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-kernel-task-v37-repair`: active-only 243, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-main-experience-refresh-v1`: active-only 199, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-main-selective-admission-v1`: active-only 97, branch-only 3, drift paths 4, branch-only paths 0.
- `yado-rc8-candidate`: active-only 243, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-ab`: active-only 243, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-audit`: active-only 243, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-digital-consciousness-v1`: active-only 243, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v30-runtime`: active-only 243, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v33-evolution`: active-only 243, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v35-training`: active-only 243, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v36-digital-consciousness`: active-only 243, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v37-digital-consciousness`: active-only 243, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v28-runtime`: active-only 243, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v29-cognitive`: active-only 243, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v7-meta-admission-shadow-v1`: active-only 179, branch-only 0, drift paths 0, branch-only paths 0.
