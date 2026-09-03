from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from yado_core_v2 import canonical_json, utc_now
from yado_core_v2_1 import RuleProgramSynthesizer
from yado_core_v2_2 import (
    FieldMapperSynthesizer,
    Mechanism,
    MechanismSelector,
    SequencePlannerSynthesizer,
    UnifiedCognitiveSystemV22,
)


class AuditedMechanismSelector(MechanismSelector):
    """Mechanism selection with explicit rejection diagnostics.

    v2.2 deliberately tolerated unsupported mechanism families, but discarded
    their ValueError reasons.  This wrapper keeps the same bounded families and
    selection behavior while making the failure evidence observable.
    """

    @classmethod
    def synthesize_candidates_with_diagnostics(
        cls,
        target_capability: str,
        target_organ: str,
        examples: Sequence[Mapping[str, Any]],
        min_support: int = 2,
    ) -> Tuple[List[Mechanism], List[Dict[str, str]]]:
        candidates: List[Mechanism] = []
        rejected: List[Dict[str, str]] = []
        expected = [e.get("expected") for e in examples]

        if expected and all(isinstance(x, Mapping) for x in expected):
            try:
                candidates.append(FieldMapperSynthesizer.synthesize(target_capability, target_organ, examples))
            except ValueError as exc:
                rejected.append({"family": "FIELD_MAPPER", "reason": str(exc)})
        else:
            rejected.append({"family": "FIELD_MAPPER", "reason": "output_contract_mismatch"})

        if expected and all(isinstance(x, list) and all(isinstance(a, str) for a in x) for x in expected):
            try:
                candidates.append(SequencePlannerSynthesizer.synthesize(target_capability, target_organ, examples, min_support))
            except ValueError as exc:
                rejected.append({"family": "SEQUENCE_PLANNER", "reason": str(exc)})
        else:
            rejected.append({"family": "SEQUENCE_PLANNER", "reason": "output_contract_mismatch"})

        try:
            candidates.append(
                RuleProgramSynthesizer.synthesize(
                    target_capability=target_capability,
                    target_organ=target_organ,
                    examples=examples,
                    min_support=min_support,
                )
            )
        except ValueError as exc:
            rejected.append({"family": "RULE_PROGRAM", "reason": str(exc)})

        if not candidates:
            reasons = "; ".join(f"{r['family']}:{r['reason']}" for r in rejected)
            raise ValueError(f"no supported bounded mechanism family fits the training evidence; {reasons}")
        return candidates, rejected


class UnifiedCognitiveSystemV24Audited(UnifiedCognitiveSystemV22):
    """YADO-only audited developmental profile.

    It intentionally inherits the proven v2.2 developmental substrate rather
    than v2.3's NOESIS authority plane.  The purpose is to establish one
    observable YADO development registry before any canonical promotion.
    """

    SCHEMA_VERSION = 6

    def _init_schema(self) -> None:
        super()._init_schema()
        with self.db_lock:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS development_artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    registered_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS self_audit_findings (
                    finding_id TEXT PRIMARY KEY,
                    severity TEXT NOT NULL,
                    component TEXT NOT NULL,
                    title TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS mechanism_rejections (
                    rejection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    capability TEXT NOT NULL,
                    organ TEXT NOT NULL,
                    family TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cognitive_training_runs (
                    run_id TEXT PRIMARY KEY,
                    organ TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    baseline REAL NOT NULL,
                    candidate REAL NOT NULL,
                    blind REAL NOT NULL,
                    ablation REAL NOT NULL,
                    restore REAL NOT NULL,
                    verdict TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            self.conn.commit()

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def register_artifact(self, path: str | Path, role: str, status: str, metadata: Mapping[str, Any] | None = None) -> str:
        p = Path(path)
        digest = self._sha256(p)
        artifact_id = "A-" + digest[:16]
        with self.db_lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO development_artifacts
                   (artifact_id,path,sha256,role,status,metadata_json,registered_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (artifact_id, str(p), digest, role, status, canonical_json(dict(metadata or {})), utc_now().isoformat()),
            )
            self.conn.commit()
        return artifact_id

    def record_finding(self, finding_id: str, severity: str, component: str, title: str, evidence: Mapping[str, Any], status: str = "OPEN") -> None:
        with self.db_lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO self_audit_findings
                   (finding_id,severity,component,title,evidence_json,status,created_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (finding_id, severity, component, title, canonical_json(dict(evidence)), status, utc_now().isoformat()),
            )
            self.conn.commit()

    def select_with_diagnostics(self, target_capability: str, target_organ: str, examples: Sequence[Mapping[str, Any]], min_support: int = 2):
        candidates, rejected = AuditedMechanismSelector.synthesize_candidates_with_diagnostics(
            target_capability, target_organ, examples, min_support
        )
        with self.db_lock:
            for row in rejected:
                self.conn.execute(
                    """INSERT INTO mechanism_rejections(capability,organ,family,reason,created_at)
                       VALUES(?,?,?,?,?)""",
                    (target_capability, target_organ, row["family"], row["reason"], utc_now().isoformat()),
                )
            self.conn.commit()
        return candidates, rejected

    def record_training(self, run: Mapping[str, Any]) -> None:
        with self.db_lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO cognitive_training_runs
                   (run_id,organ,capability,baseline,candidate,blind,ablation,restore,verdict,details_json,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run["run_id"], run["organ"], run["capability"], float(run["baseline"]), float(run["candidate"]),
                    float(run["blind"]), float(run["ablation"]), float(run["restore"]), run["verdict"],
                    canonical_json(dict(run.get("details") or {})), utc_now().isoformat(),
                ),
            )
            self.conn.commit()

    def audit_snapshot(self) -> Dict[str, Any]:
        with self.db_lock:
            artifact_count = self.conn.execute("SELECT COUNT(*) FROM development_artifacts").fetchone()[0]
            open_findings = self.conn.execute("SELECT COUNT(*) FROM self_audit_findings WHERE status='OPEN'").fetchone()[0]
            rejection_count = self.conn.execute("SELECT COUNT(*) FROM mechanism_rejections").fetchone()[0]
            training_count = self.conn.execute("SELECT COUNT(*) FROM cognitive_training_runs").fetchone()[0]
        return {
            "profile": "YADO_V2_4_AUDITED_SHADOW",
            "yado_only": True,
            "noesis_authority_active": hasattr(self, "noesis_authority"),
            "development_artifacts": artifact_count,
            "open_findings": open_findings,
            "mechanism_rejections_logged": rejection_count,
            "cognitive_training_runs": training_count,
            "canonical_durable_mutation": False,
        }


__all__ = ["AuditedMechanismSelector", "UnifiedCognitiveSystemV24Audited"]
