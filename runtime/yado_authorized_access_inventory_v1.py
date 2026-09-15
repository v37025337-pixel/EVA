#!/usr/bin/env python3
"""YADO authorized access inventory v1.

Discovers only credential *references* and explicitly authorized/public access
paths in the repository. It never reads, prints, stores, guesses, or exports
secret values.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (".github/workflows", "runtime", "successor", "architecture", "canonical")
TEXT_SUFFIXES = {".py", ".yml", ".yaml", ".json", ".md", ".txt", ".toml"}

SECRET_REF_PATTERNS = (
    re.compile(r"secrets\.([A-Z][A-Z0-9_]{2,})"),
    re.compile(r"os\.environ\[['\"]([A-Z][A-Z0-9_]{2,})['\"]\]"),
    re.compile(r"os\.getenv\(['\"]([A-Z][A-Z0-9_]{2,})['\"]"),
    re.compile(r"getenv\(['\"]([A-Z][A-Z0-9_]{2,})['\"]"),
)

PUBLIC_ACCESS = [
    {
        "id": "judge0_ce",
        "endpoint": "https://ce.judge0.com",
        "mode": "PUBLIC_NO_AUTH_EXECUTION_SANDBOX",
        "verified_by": "runtime/yado_public_sandbox_connect_v1.py",
    },
    {
        "id": "runlet",
        "endpoint": "https://runlet.codealong.live",
        "mode": "PUBLIC_NO_AUTH_EXECUTION_SANDBOX",
        "verified_by": "runtime/yado_public_sandbox_connect_v1.py",
    },
]

KNOWN_PROTECTED_ACCESS = [
    {
        "id": "mailru_webdav",
        "endpoint": "https://webdav.cloud.mail.ru",
        "required_env": ["YADO_MAILRU_USER", "YADO_MAILRU_APP_PASSWORD"],
        "mode": "AUTHORIZED_CREDENTIAL_REQUIRED",
    },
]


def iter_text_files(root: Path = ROOT) -> Iterable[Path]:
    for rel in SCAN_ROOTS:
        base = root / rel
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                yield path


def find_credential_references(root: Path = ROOT) -> list[dict[str, Any]]:
    refs: dict[str, set[str]] = {}
    for path in iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(path.relative_to(root))
        for pattern in SECRET_REF_PATTERNS:
            for name in pattern.findall(text):
                refs.setdefault(name, set()).add(rel)
    return [
        {
            "name": name,
            "configured_in_current_process": bool(os.getenv(name)),
            "referenced_by": sorted(paths),
            "value_exposed": False,
        }
        for name, paths in sorted(refs.items())
    ]


def build_report(root: Path = ROOT) -> dict[str, Any]:
    references = find_credential_references(root)
    protected = []
    for entry in KNOWN_PROTECTED_ACCESS:
        required = entry["required_env"]
        protected.append(
            {
                **entry,
                "configured": all(bool(os.getenv(name)) for name in required),
                "secret_values_exposed": False,
            }
        )
    return {
        "schema": "yado.authorized_access_inventory.v1",
        "status": "PASS_AUTHORIZED_ACCESS_INVENTORY",
        "policy": {
            "credential_value_capture": False,
            "credential_guessing": False,
            "credential_bypass": False,
            "secret_values_exposed": False,
            "authorized_reference_discovery_only": True,
        },
        "public_no_auth_access": PUBLIC_ACCESS,
        "protected_access": protected,
        "credential_references": references,
        "counts": {
            "credential_reference_names": len(references),
            "public_no_auth_endpoints": len(PUBLIC_ACCESS),
            "protected_access_profiles": len(protected),
            "configured_credential_profiles": sum(1 for x in protected if x["configured"]),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    report = build_report()
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
