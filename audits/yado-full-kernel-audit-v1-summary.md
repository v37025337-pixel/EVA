# YADO Full Kernel Audit V1

- Status: **FAIL_AUDIT**
- Commit: `a82c44ef614bfdf07d860820d04ff50ee03be76d`
- Generation: `G2_CANDIDATE_TRCG_V1`; G3 started: `False`
- Frontier: `KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2`
- Runtime Python: 466; workflows: 35; JSON artifacts: 811; ledger events: 278
- Canonical guard: PASS; ledger: PASS

## Findings
- **CRITICAL PYTHON_COMPILE_ERRORS** — 1 runtime Python files fail compilation.
- **CRITICAL AST_PARSE_ERRORS** — 1 runtime files fail AST parsing.
- **HIGH JSON_PARSE_ERRORS** — 2 JSON artifacts are invalid.
- **HIGH BROKEN_WORKFLOW_STATIC_REFERENCES** — 30 workflow references point to missing files.

## Branches
- `origin`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
- `main`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-kernel-task-v37-repair`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-candidate`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-ab`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-consciousness-audit`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-digital-consciousness-v1`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v30-runtime`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v33-evolution`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v35-training`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v36-digital-consciousness`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-rc8-v37-digital-consciousness`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v28-runtime`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
- `yado-v29-cognitive`: active-only 1, branch-only 0, drift paths 0, branch-only paths 0.
