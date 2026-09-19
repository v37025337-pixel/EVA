from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDITS = ROOT / "audits"
V1_REPORT = AUDITS / "yado-full-kernel-audit-v1-report.json"
V2_REPORT = AUDITS / "yado-full-kernel-audit-v2-report.json"
V2_SUMMARY = AUDITS / "yado-full-kernel-audit-v2-summary.md"

sys.path.insert(0, str(ROOT / "runtime"))
from yado_repository_reconciliation_v1 import run as run_reconciliation


def main() -> int:
    reconciliation = run_reconciliation(strict=False)

    cp = subprocess.run(
        [sys.executable, str(ROOT / "runtime" / "yado_full_kernel_audit_v1.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=1800,
        check=False,
    )

    v1 = {}
    if V1_REPORT.exists():
        v1 = json.loads(V1_REPORT.read_text(encoding="utf-8"))

    v1_pass = cp.returncode == 0 and v1.get("status") == "PASS" and not v1.get("findings")
    recon_pass = reconciliation.get("status") == "PASS"
    status = "PASS" if v1_pass and recon_pass else "FAIL_AUDIT_V2"

    report = {
        "schema": "yado.full_kernel_audit.v2",
        "status": status,
        "repository_reconciliation": {
            "status": reconciliation.get("status"),
            "failed_checks": [k for k, v in reconciliation.get("checks", {}).items() if not v],
            "finding_count": len(reconciliation.get("findings", [])),
            "branch_inventory": reconciliation.get("branch_inventory", {}),
        },
        "kernel_audit_v1": {
            "status": v1.get("status"),
            "finding_count": len(v1.get("findings", [])),
            "returncode": cp.returncode,
            "stdout_tail": cp.stdout[-4000:],
            "stderr_tail": cp.stderr[-4000:],
        },
        "claim_boundary": "V2 ADDS REPOSITORY, VERSION, BRANCH, RUNTIME-PROMOTION AND CONTINUITY CONSISTENCY TO THE EXISTING FULL KERNEL AUDIT. IT DOES NOT CHANGE THE FORMAL GENERATION OR ESTABLISH CONSCIOUSNESS.",
    }

    AUDITS.mkdir(exist_ok=True)
    V2_REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    V2_SUMMARY.write_text(
        "# YADO Full Kernel Audit V2\n\n"
        f"- Status: **{status}**\n"
        f"- Repository reconciliation: **{reconciliation.get('status')}**\n"
        f"- Kernel Audit V1: **{v1.get('status')}**\n"
        f"- Formal generation: {reconciliation.get('formal_generation')}\n"
        f"- Runtime generation: {reconciliation.get('runtime_generation')}\n"
        f"- Reconciliation findings: {len(reconciliation.get('findings', []))}\n"
        f"- V1 findings: {len(v1.get('findings', []))}\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "status": status,
        "reconciliation": reconciliation.get("status"),
        "v1": v1.get("status"),
        "v2_report": str(V2_REPORT.relative_to(ROOT)),
    }, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
