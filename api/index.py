from http.server import BaseHTTPRequestHandler
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "canonical" / "yado-unified-core-v1.json"
AUDIT = ROOT / "audits" / "yado-full-kernel-audit-v1-report.json"


class ReadinessError(ValueError):
    pass


def _digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _load_object(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReadinessError("OBJECT_REQUIRED")
    return value


def _check_self_digest(value, field):
    if value.get(field) != _digest({k: v for k, v in value.items() if k != field}):
        raise ReadinessError("SELF_DIGEST_MISMATCH")


def _verify_sources(sources):
    if not isinstance(sources, dict) or not sources:
        raise ReadinessError("SOURCE_BINDING_REQUIRED")
    root = ROOT.resolve()
    for relative, expected in sources.items():
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise ReadinessError("SOURCE_PATH_INVALID")
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ReadinessError("SOURCE_PATH_OUTSIDE_ROOT")
        if not isinstance(expected, str) or len(expected) != 64:
            raise ReadinessError("SOURCE_DIGEST_INVALID")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ReadinessError("SOURCE_DRIFT")


def _load_status():
    """Readiness of the verified bootstrap files, not a running cognitive loop.

    Source hashes bind an audit to deployed bytes even when .git is absent or a
    report-only commit follows the audited commit. Unbound historical reports
    cannot establish readiness.
    """
    data = {
        "service": "YADO Successor V2 runtime facade",
        "status": "not_ready",
        "mode": "read_only_bootstrap",
        "persistent_state": "external_required",
        "canonical_status": "UNVERIFIED",
        "full_kernel_audit_pass": False,
        "audit_freshness": "UNVERIFIED",
    }
    phase = "canonical"
    try:
        core = _load_object(CANONICAL)
        head = _load_object(ROOT / "canonical/yado-main-head-g2.json")
        ledger = _load_object(ROOT / "architecture/evolution-ledger.json")
        _check_self_digest(core, "core_digest")
        _check_self_digest(head, "canonical_head_digest")
        if core.get("canonical_active") is not True:
            raise ReadinessError("CANONICAL_INACTIVE")
        generation = core.get("generation") or core.get("canonical_generation")
        if (not generation or generation != head.get("generation_id")
                or generation != ledger.get("current_head")
                or head["canonical_head_digest"] != ledger.get("current_head_digest")):
            raise ReadinessError("HEAD_LEDGER_BINDING_MISMATCH")
        manifest = core["runtime_integrity_manifest"]
        sources = manifest["sources"]
        if manifest.get("manifest_digest") != _digest(sources):
            raise ReadinessError("MANIFEST_DIGEST_MISMATCH")
        _verify_sources(sources)
        if not set(core.get("active_runtime_sources", [])) <= set(sources):
            raise ReadinessError("ACTIVE_SOURCE_BINDING_INCOMPLETE")
        data.update(canonical_status="VERIFIED", canonical_active=True, generation=generation,
                    g3_genesis_performed=core.get("g3_genesis_performed", False))

        phase = "audit"
        report = _load_object(AUDIT)
        if (report.get("schema") != "yado.full_kernel_audit.v1" or report.get("status") != "PASS"
                or any(item.get("severity") in {"MEDIUM", "HIGH", "CRITICAL"}
                       for item in report.get("findings", []))):
            raise ReadinessError("AUDIT_NOT_PASS")
        if report.get("canonical", {}).get("head_digest") != head["canonical_head_digest"]:
            raise ReadinessError("AUDIT_CANONICAL_BINDING_MISMATCH")
        audited_sources = report.get("source_sha256")
        _verify_sources(audited_sources)
        required = set(sources) | {"canonical/yado-unified-core-v1.json", "canonical/yado-main-head-g2.json",
                                   "architecture/evolution-ledger.json", "api/index.py"}
        if not required <= set(audited_sources):
            raise ReadinessError("AUDIT_SOURCE_COVERAGE_INCOMPLETE")
        data.update(status="ok", full_kernel_audit_pass=True, audit_freshness="SOURCE_SHA256_MATCH",
                    audited_commit=report.get("audited_commit"))
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        if phase == "canonical":
            data["canonical_status"] = "INVALID"
        else:
            data["audit_freshness"] = "UNVERIFIED_OR_STALE"
        data["readiness_error"] = str(exc) if isinstance(exc, ReadinessError) else type(exc).__name__
    return data


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health", "/status"):
            self.send_response(404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"error":"not_found"}')
            return

        status = _load_status()
        payload = json.dumps(status, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(200 if status["status"] == "ok" else 503)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)
