from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "canonical" / "yado-unified-core-v1.json"
AUDIT = ROOT / "audits" / "yado-full-kernel-audit-v1-summary.md"


def _load_status():
    data = {
        "service": "YADO Successor V2 runtime facade",
        "status": "ok",
        "mode": "read_only_bootstrap",
        "persistent_state": "external_required",
    }
    if CANONICAL.exists():
        try:
            c = json.loads(CANONICAL.read_text(encoding="utf-8"))
            data["canonical_active"] = c.get("canonical_active")
            data["generation"] = c.get("generation") or c.get("canonical_generation")
            data["g3_genesis_performed"] = c.get("g3_genesis_performed", False)
        except Exception as exc:
            data["canonical_read_error"] = type(exc).__name__
    if AUDIT.exists():
        text = AUDIT.read_text(encoding="utf-8", errors="replace")
        data["full_kernel_audit_pass"] = "Status: **PASS**" in text
    return data


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health", "/status"):
            self.send_response(404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"error":"not_found"}')
            return

        payload = json.dumps(_load_status(), ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)
