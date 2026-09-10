from __future__ import annotations

from pathlib import Path
import json

from yado_native_code_writer_v1 import (
    YADONativeCodeWriterV1,
    REPO,
    CANDIDATE,
    REPORT,
    digest,
    load,
)

REQUEST = REPO / "architecture/yado-native-code-writer-v1-1-request.json"


class YADONativeCodeWriterV11(YADONativeCodeWriterV1):
    """V1.1 repair: capture complete href values, then strip URL fragments later."""

    COMPONENT_ID = "CTRL-G2-NATIVE-CODE-WRITER-V1_1"

    @classmethod
    def materialize(cls, ir: dict) -> str:
        source = super().materialize(ir)
        old = r'''href\s*=\s*[\"']([^\"'#]+)[\"']'''
        new = r'''href\s*=\s*[\"']([^\"']+)[\"']'''
        if old not in source:
            raise RuntimeError("V1_1_EXPECTED_HREF_PATTERN_NOT_FOUND")
        source = source.replace(old, new, 1)
        compile(source, "<yado-native-code-writer-v1-1>", "exec")
        return source

    def run(self, request: dict) -> dict:
        report = super().run(request)
        report["component_id"] = self.COMPONENT_ID
        report["writer_revision"] = "V1_1_FRAGMENT_CAPTURE_FIX"
        report["repair_reason"] = "V1 incorrectly excluded # inside href capture, preventing the later FRAGMENT_STRIP operation from running. V1.1 captures the full href and strips fragments after URL parsing."
        report["receipt_sha256"] = digest({k: v for k, v in report.items() if k != "receipt_sha256"})
        return report


def main() -> int:
    request = load(REQUEST)
    writer = YADONativeCodeWriterV11()
    report = writer.run(request)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report.get("status"),
        "writer_revision": report.get("writer_revision"),
        "candidate_path": report.get("candidate_path"),
        "candidate_source_sha256": report.get("candidate_source_sha256"),
        "candidate_source_produced_by_yado": report.get("candidate_source_produced_by_yado"),
        "fresh_tests": (report.get("fresh_tests") or {}).get("pass"),
        "safety": (report.get("safety") or {}).get("pass"),
        "receipt_sha256": report.get("receipt_sha256"),
    }, indent=2, sort_keys=True))
    return 0 if report.get("status") == "PASS_SHADOW_G2_NATIVE_CODE_WRITER_V1" else 2


if __name__ == "__main__":
    raise SystemExit(main())
