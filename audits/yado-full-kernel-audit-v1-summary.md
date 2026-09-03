# YADO Full Kernel Audit V1

- Status: **FAIL_AUDIT**
- Commit: `c3a93ac21172b1d366e4060b988ee2ace7f0b285`
- Generation: `G2_CANDIDATE_TRCG_V1`; G3 started: `False`
- Frontier: `KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1`
- Runtime Python: 391; workflows: 294; JSON artifacts: 686; ledger events: 257
- Canonical guard: PASS; ledger: PASS

## Findings
- **HIGH BROKEN_WORKFLOW_STATIC_REFERENCES** — 742 workflow references point to missing files.
- **HIGH PHYSICAL_BRANCH_DIVERGENCE** — 13 historical branches retain commits not in active branch ancestry. Logical closure is not physical Git closure.

## Branches
- `origin`: active-only 1252, branch-only 3, drift paths 0, branch-only paths 3.
- `main`: active-only 1252, branch-only 3, drift paths 0, branch-only paths 3.
- `yado-kernel-task-v37-repair`: active-only 1250, branch-only 5, drift paths 0, branch-only paths 3.
- `yado-rc8-candidate`: active-only 1262, branch-only 7, drift paths 0, branch-only paths 22.
- `yado-rc8-consciousness-ab`: active-only 1255, branch-only 13, drift paths 1, branch-only paths 24.
- `yado-rc8-consciousness-audit`: active-only 1255, branch-only 9, drift paths 1, branch-only paths 20.
- `yado-rc8-digital-consciousness-v1`: active-only 1255, branch-only 7, drift paths 1, branch-only paths 20.
- `yado-rc8-v30-runtime`: active-only 1259, branch-only 4, drift paths 1, branch-only paths 13.
- `yado-rc8-v33-evolution`: active-only 1256, branch-only 2, drift paths 1, branch-only paths 15.
- `yado-rc8-v35-training`: active-only 1255, branch-only 3, drift paths 1, branch-only paths 16.
- `yado-rc8-v36-digital-consciousness`: active-only 1250, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v37-digital-consciousness`: active-only 1250, branch-only 10, drift paths 0, branch-only paths 10.
- `yado-v28-runtime`: active-only 1263, branch-only 5, drift paths 1, branch-only paths 13.
- `yado-v29-cognitive`: active-only 1262, branch-only 2, drift paths 0, branch-only paths 13.
