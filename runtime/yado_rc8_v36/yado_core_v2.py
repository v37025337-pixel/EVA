from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import secrets
import socket
import sqlite3
import threading
import time
import uuid
import zlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Tuple, Union
from urllib.parse import urlparse

import aiohttp
import networkx as nx
import numpy as np
from bs4 import BeautifulSoup
from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors

logger = logging.getLogger("YADO-CORE")
logging.basicConfig(
    level=os.getenv("YADO_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

UTC = timezone.utc


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Reversible "Absolute Code" layer
# ---------------------------------------------------------------------------
class AbsoluteCodeSystem:
    """
    Reversible bit-packing + zlib compression with integrity verification.

    The v1 implementation kept only a hash of a geometry trajectory, which was
    not sufficient to reconstruct the original bits. v2 keeps a reversible
    payload and treats the geometric-looking digest only as an auxiliary
    deterministic fingerprint, never as storage.
    """

    CODEC = "bitpack+zlib-v2"

    def __init__(self, data_size: int, seed: Optional[str] = None):
        self.data_size = max(0, int(data_size))
        self.seed = seed or secrets.token_hex(16)
        self.dimensions = max(8, min(64, int(np.log2(self.data_size + 1) * 4) if self.data_size else 8))
        self.bits_per_point = max(4, min(16, int(np.log2(self.data_size + 1) * 2) if self.data_size else 4))

    @staticmethod
    def _pack_bits(binary_data: str) -> Tuple[bytes, int]:
        if any(ch not in "01" for ch in binary_data):
            raise ValueError("binary_data must contain only '0' and '1'")
        pad = (-len(binary_data)) % 8
        padded = binary_data + ("0" * pad)
        if not padded:
            return b"", pad
        return bytes(int(padded[i : i + 8], 2) for i in range(0, len(padded), 8)), pad

    @staticmethod
    def _unpack_bits(raw: bytes, binary_length: int) -> str:
        if not raw:
            return ""
        bits = "".join(f"{byte:08b}" for byte in raw)
        return bits[:binary_length]

    def _geometry_digest(self, raw_sha256: str) -> str:
        material = f"{self.seed}:{self.dimensions}:{self.bits_per_point}:{raw_sha256}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def compress_data(self, binary_data: str) -> Dict[str, Any]:
        raw, pad_bits = self._pack_bits(binary_data)
        payload = zlib.compress(raw, level=9)
        raw_sha256 = hashlib.sha256(raw).hexdigest()
        return {
            "codec": self.CODEC,
            "seed": self.seed,
            "dimensions": self.dimensions,
            "bits_per_point": self.bits_per_point,
            "binary_length": len(binary_data),
            "pad_bits": pad_bits,
            "raw_sha256": raw_sha256,
            "geometry_digest": self._geometry_digest(raw_sha256),
            "payload_b64": base64.urlsafe_b64encode(payload).decode("ascii"),
        }

    def decompress_data(self, compressed: Mapping[str, Any]) -> Tuple[bool, str]:
        if compressed.get("codec") != self.CODEC:
            return False, ""
        try:
            payload = base64.urlsafe_b64decode(str(compressed["payload_b64"]).encode("ascii"))
            raw = zlib.decompress(payload)
            valid = hmac.compare_digest(hashlib.sha256(raw).hexdigest(), str(compressed["raw_sha256"]))
            if not valid:
                return False, ""
            return True, self._unpack_bits(raw, int(compressed["binary_length"]))
        except (KeyError, ValueError, TypeError, zlib.error, base64.binascii.Error):
            return False, ""

    @classmethod
    def compress_text(cls, text: str, seed: Optional[str] = None) -> Dict[str, Any]:
        raw = text.encode("utf-8")
        bits = "".join(f"{byte:08b}" for byte in raw)
        return cls(len(bits), seed=seed).compress_data(bits)

    @classmethod
    def decompress_text(cls, compressed: Mapping[str, Any]) -> Tuple[bool, str]:
        system = cls(int(compressed.get("binary_length", 0)), seed=str(compressed.get("seed", "")))
        ok, bits = system.decompress_data(compressed)
        if not ok:
            return False, ""
        try:
            raw = bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8)) if bits else b""
            return True, raw.decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return False, ""


# ---------------------------------------------------------------------------
# Embedding backends
# ---------------------------------------------------------------------------
class Embedder(Protocol):
    dimension: int
    name: str

    def encode(self, text: str) -> np.ndarray:
        ...


class HashingEmbedder:
    """Offline deterministic fallback; useful for bootstrapping and tests."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.name = f"hashing-{dimension}"
        self.vectorizer = HashingVectorizer(
            n_features=dimension,
            alternate_sign=False,
            norm="l2",
            ngram_range=(1, 2),
            analyzer="word",
        )

    def encode(self, text: str) -> np.ndarray:
        vector = self.vectorizer.transform([text]).toarray()[0].astype(np.float32)
        norm = float(np.linalg.norm(vector))
        return vector if norm == 0.0 else vector / norm


class SentenceTransformerEmbedder:
    """Optional high-quality backend loaded only when explicitly requested."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("sentence-transformers is not installed") from exc
        self._model = SentenceTransformer(model_name)
        self.name = model_name
        probe = self.encode("dimension probe")
        self.dimension = int(probe.shape[0])

    def encode(self, text: str) -> np.ndarray:
        vector = np.asarray(self._model.encode(text, normalize_embeddings=True), dtype=np.float32)
        return vector


def build_embedder() -> Embedder:
    backend = os.getenv("YADO_EMBEDDER", "hashing").strip().lower()
    if backend in {"sentence-transformers", "sentence_transformers", "sbert"}:
        model_name = os.getenv("YADO_EMBEDDER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        return SentenceTransformerEmbedder(model_name)
    return HashingEmbedder(dimension=int(os.getenv("YADO_HASH_DIM", "384")))


# ---------------------------------------------------------------------------
# Cognitive state
# ---------------------------------------------------------------------------
@dataclass
class CapabilityState:
    name: str
    score: float
    evidence: List[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: utc_now().isoformat())


@dataclass
class GoalState:
    goal_id: str
    objective: str
    required_capabilities: Dict[str, float]
    success_criteria: Dict[str, Any]
    status: str = "OPEN"
    created_at: str = field(default_factory=lambda: utc_now().isoformat())


@dataclass
class DeficitState:
    deficit_id: str
    goal_id: str
    kind: str
    target: str
    observed: float
    required: float
    evidence: List[str]
    status: str = "OPEN"
    created_at: str = field(default_factory=lambda: utc_now().isoformat())


@dataclass
class CandidateChange:
    candidate_id: str
    deficit_id: str
    action_type: str
    description: str
    expected_effect: str
    status: str = "SHADOW"


@dataclass
class ExperimentReceipt:
    experiment_id: str
    candidate_id: str
    baseline_score: float
    candidate_score: float
    ablation_score: float
    min_gain: float
    min_ablation_drop: float
    verdict: str
    state_committed: bool
    reason: str
    created_at: str = field(default_factory=lambda: utc_now().isoformat())


class CausalExecutive:
    """
    Bounded causal controller.

    It does not claim to autonomously rewrite arbitrary code. It localizes a
    functional deficit, produces a bounded candidate category, and only commits
    a measured capability change when improvement and ablation evidence pass.
    """

    def __init__(self, system: "UnifiedCognitiveSystem"):
        self.system = system
        self.capabilities: Dict[str, CapabilityState] = {}
        self.goals: Dict[str, GoalState] = {}
        self.deficits: Dict[str, DeficitState] = {}
        self.candidates: Dict[str, CandidateChange] = {}
        self.receipts: Dict[str, ExperimentReceipt] = {}
        self._restore_state()
        self._register_builtin_capabilities()

    def _register_builtin_capabilities(self) -> None:
        builtins = {
            "resource_memory": 1.0,
            "semantic_retrieval": 0.75,
            "knowledge_graph": 0.8,
            "causal_experiment_gate": 0.9,
        }
        for name, score in builtins.items():
            if name not in self.capabilities:
                self.register_capability(name, score, ["builtin:v2"])

    def _restore_state(self) -> None:
        with self.system.db_lock:
            rows = self.system.conn.execute("SELECT name, score, evidence, updated_at FROM capabilities").fetchall()
            for row in rows:
                self.capabilities[row["name"]] = CapabilityState(
                    name=row["name"], score=float(row["score"]), evidence=json.loads(row["evidence"]), updated_at=row["updated_at"]
                )
            rows = self.system.conn.execute("SELECT * FROM goals").fetchall()
            for row in rows:
                self.goals[row["goal_id"]] = GoalState(
                    goal_id=row["goal_id"], objective=row["objective"],
                    required_capabilities=json.loads(row["required_capabilities"]),
                    success_criteria=json.loads(row["success_criteria"]), status=row["status"], created_at=row["created_at"]
                )

    def register_capability(self, name: str, score: float, evidence: Sequence[str]) -> CapabilityState:
        score = float(np.clip(score, 0.0, 1.0))
        state = CapabilityState(name=name, score=score, evidence=list(evidence), updated_at=utc_now().isoformat())
        self.capabilities[name] = state
        with self.system.db_lock:
            self.system.conn.execute(
                "INSERT OR REPLACE INTO capabilities(name, score, evidence, updated_at) VALUES(?,?,?,?)",
                (name, score, canonical_json(state.evidence), state.updated_at),
            )
            self.system.conn.commit()
        return state

    def create_goal(
        self,
        objective: str,
        required_capabilities: Mapping[str, float],
        success_criteria: Optional[Mapping[str, Any]] = None,
    ) -> GoalState:
        goal = GoalState(
            goal_id=f"G-{uuid.uuid4().hex[:12]}",
            objective=objective,
            required_capabilities={k: float(v) for k, v in required_capabilities.items()},
            success_criteria=dict(success_criteria or {}),
        )
        self.goals[goal.goal_id] = goal
        with self.system.db_lock:
            self.system.conn.execute(
                "INSERT INTO goals(goal_id, objective, required_capabilities, success_criteria, status, created_at) VALUES(?,?,?,?,?,?)",
                (goal.goal_id, goal.objective, canonical_json(goal.required_capabilities), canonical_json(goal.success_criteria), goal.status, goal.created_at),
            )
            self.system.conn.commit()
        return goal

    def detect_deficits(self, goal_id: str) -> List[DeficitState]:
        goal = self.goals[goal_id]
        found: List[DeficitState] = []
        for capability, required in goal.required_capabilities.items():
            current = self.capabilities.get(capability)
            observed = current.score if current else 0.0
            if observed + 1e-12 >= required:
                continue
            deficit = DeficitState(
                deficit_id=f"D-{uuid.uuid4().hex[:12]}",
                goal_id=goal_id,
                kind="CAPABILITY_MISSING" if current is None else "CAPABILITY_INSUFFICIENT",
                target=capability,
                observed=observed,
                required=required,
                evidence=(current.evidence[:] if current else ["capability:not_registered"]),
            )
            self.deficits[deficit.deficit_id] = deficit
            found.append(deficit)
            with self.system.db_lock:
                self.system.conn.execute(
                    "INSERT INTO deficits(deficit_id, goal_id, kind, target, observed, required, evidence, status, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        deficit.deficit_id, deficit.goal_id, deficit.kind, deficit.target, deficit.observed,
                        deficit.required, canonical_json(deficit.evidence), deficit.status, deficit.created_at,
                    ),
                )
                self.system.conn.commit()
        if not found:
            goal.status = "READY_FOR_GOAL_TEST"
            with self.system.db_lock:
                self.system.conn.execute("UPDATE goals SET status=? WHERE goal_id=?", (goal.status, goal.goal_id))
                self.system.conn.commit()
        return found

    def propose_candidate(self, deficit_id: str) -> CandidateChange:
        deficit = self.deficits[deficit_id]
        if deficit.target.startswith("knowledge:"):
            action_type = "ACQUIRE_EVIDENCE"
        elif deficit.kind == "CAPABILITY_MISSING":
            action_type = "BUILD_CAPABILITY"
        else:
            action_type = "IMPROVE_CAPABILITY"
        candidate = CandidateChange(
            candidate_id=f"C-{uuid.uuid4().hex[:12]}",
            deficit_id=deficit_id,
            action_type=action_type,
            description=f"Bounded candidate to address {deficit.target}",
            expected_effect=f"Raise {deficit.target} from {deficit.observed:.3f} toward >= {deficit.required:.3f}",
        )
        self.candidates[candidate.candidate_id] = candidate
        return candidate

    def evaluate_candidate(
        self,
        candidate_id: str,
        baseline_score: float,
        candidate_score: float,
        ablation_score: float,
        min_gain: float = 0.05,
        min_ablation_drop: float = 0.03,
    ) -> ExperimentReceipt:
        candidate = self.candidates[candidate_id]
        deficit = self.deficits[candidate.deficit_id]
        gain = candidate_score - baseline_score
        ablation_drop = candidate_score - ablation_score
        pass_gain = gain >= min_gain
        pass_ablation = ablation_drop >= min_ablation_drop
        pass_target = candidate_score >= deficit.required
        committed = pass_gain and pass_ablation and pass_target

        if committed:
            verdict = "COMMIT"
            reason = "candidate improved the metric, passed ablation, and reached the required threshold"
            candidate.status = "COMMITTED"
            deficit.status = "RESOLVED"
            self.register_capability(
                deficit.target,
                candidate_score,
                [
                    f"experiment:{candidate_id}",
                    f"gain:{gain:.6f}",
                    f"ablation_drop:{ablation_drop:.6f}",
                ],
            )
        else:
            verdict = "ROLLBACK"
            candidate.status = "ROLLED_BACK"
            reasons = []
            if not pass_gain:
                reasons.append("insufficient_gain")
            if not pass_ablation:
                reasons.append("ablation_not_causal")
            if not pass_target:
                reasons.append("target_not_reached")
            reason = ",".join(reasons)

        receipt = ExperimentReceipt(
            experiment_id=f"E-{uuid.uuid4().hex[:12]}",
            candidate_id=candidate_id,
            baseline_score=float(baseline_score),
            candidate_score=float(candidate_score),
            ablation_score=float(ablation_score),
            min_gain=float(min_gain),
            min_ablation_drop=float(min_ablation_drop),
            verdict=verdict,
            state_committed=committed,
            reason=reason,
        )
        self.receipts[receipt.experiment_id] = receipt
        with self.system.db_lock:
            self.system.conn.execute(
                "INSERT INTO experiments(experiment_id, candidate_id, receipt_json, created_at) VALUES(?,?,?,?)",
                (receipt.experiment_id, candidate_id, canonical_json(asdict(receipt)), receipt.created_at),
            )
            self.system.conn.commit()
        return receipt

    def run_cycle(self, goal_id: str) -> Dict[str, Any]:
        deficits = self.detect_deficits(goal_id)
        if not deficits:
            return {
                "goal_id": goal_id,
                "state": "READY_FOR_GOAL_TEST",
                "next_action": "execute_goal_success_criteria",
            }
        primary = max(deficits, key=lambda d: d.required - d.observed)
        candidate = self.propose_candidate(primary.deficit_id)
        return {
            "goal_id": goal_id,
            "state": "CANDIDATE_READY",
            "deficit": asdict(primary),
            "candidate": asdict(candidate),
            "next_action": "run_bounded_experiment_then_submit_metrics",
        }


# ---------------------------------------------------------------------------
# Persistent resource / knowledge subsystem
# ---------------------------------------------------------------------------
class UnifiedCognitiveSystem:
    SCHEMA_VERSION = 2

    def __init__(self, db_path: str = "cognitive_system_v2.db", embedder: Optional[Embedder] = None):
        self.db_path = db_path
        self.db_lock = threading.RLock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self.db_lock:
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

        self.embedder = embedder or build_embedder()
        self.graph = nx.Graph()
        self.resource_ids: List[str] = []
        self.data_points = np.empty((0, self.embedder.dimension), dtype=np.float32)
        self.nn_index: Optional[NearestNeighbors] = None
        self.start_time = utc_now()

        self._cipher = self._build_cipher()
        self._load_resources_from_db()
        self.executive = CausalExecutive(self)
        logger.info("YADO-CORE v2 initialized with embedder=%s", self.embedder.name)

    def close(self) -> None:
        with self.db_lock:
            self.conn.close()

    def _init_schema(self) -> None:
        with self.db_lock:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS resources (
                    id TEXT PRIMARY KEY,
                    compressed_data TEXT NOT NULL,
                    vector BLOB NOT NULL,
                    vector_dim INTEGER NOT NULL,
                    embedder TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS capabilities (
                    name TEXT PRIMARY KEY,
                    score REAL NOT NULL,
                    evidence TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS goals (
                    goal_id TEXT PRIMARY KEY,
                    objective TEXT NOT NULL,
                    required_capabilities TEXT NOT NULL,
                    success_criteria TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deficits (
                    deficit_id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    target TEXT NOT NULL,
                    observed REAL NOT NULL,
                    required REAL NOT NULL,
                    evidence TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    receipt_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS registration_tokens (
                    token_hash TEXT PRIMARY KEY,
                    expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS access_keys (
                    key_id TEXT PRIMARY KEY,
                    encrypted_secret BLOB NOT NULL,
                    permissions TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            self.conn.commit()

    def _build_cipher(self) -> Fernet:
        master = os.getenv("YADO_MASTER_KEY")
        if not master:
            # Development-safe bootstrap: process-specific unless caller persists it.
            master = secrets.token_urlsafe(48)
            logger.warning("YADO_MASTER_KEY is unset; registered access keys will not survive process restart")
        digest = hashlib.sha256(master.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    @staticmethod
    def text_to_binary(text: str) -> str:
        return "".join(f"{byte:08b}" for byte in text.encode("utf-8"))

    @staticmethod
    def binary_to_text(binary_str: str) -> str:
        if len(binary_str) % 8 != 0:
            raise ValueError("binary string length must be divisible by 8")
        raw = bytes(int(binary_str[i : i + 8], 2) for i in range(0, len(binary_str), 8))
        return raw.decode("utf-8")

    @staticmethod
    def _vector_to_blob(vector: np.ndarray) -> bytes:
        return np.asarray(vector, dtype=np.float32).tobytes()

    @staticmethod
    def _blob_to_vector(blob: bytes, dim: int) -> np.ndarray:
        vector = np.frombuffer(blob, dtype=np.float32).copy()
        if vector.shape[0] != dim:
            raise ValueError(f"stored vector dim mismatch: expected {dim}, got {vector.shape[0]}")
        return vector

    def _load_resources_from_db(self) -> None:
        rows = self.conn.execute("SELECT * FROM resources ORDER BY created_at, id").fetchall()
        ids: List[str] = []
        vectors: List[np.ndarray] = []
        for row in rows:
            if row["embedder"] != self.embedder.name or int(row["vector_dim"]) != self.embedder.dimension:
                # Recompute from reversible stored text if the embedding backend changed.
                payload = json.loads(row["compressed_data"])
                ok, text = AbsoluteCodeSystem.decompress_text(payload)
                if not ok:
                    logger.error("Skipping resource %s: cannot decode stored text", row["id"])
                    continue
                vector = self.embedder.encode(text)
                with self.db_lock:
                    self.conn.execute(
                        "UPDATE resources SET vector=?, vector_dim=?, embedder=?, updated_at=? WHERE id=?",
                        (self._vector_to_blob(vector), self.embedder.dimension, self.embedder.name, utc_now().isoformat(), row["id"]),
                    )
                    self.conn.commit()
            else:
                vector = self._blob_to_vector(row["vector"], int(row["vector_dim"]))
            metadata = json.loads(row["metadata"])
            tags = json.loads(row["tags"])
            self.graph.add_node(row["id"], metadata=metadata, tags=tags)
            ids.append(row["id"])
            vectors.append(vector)
        self.resource_ids = ids
        self.data_points = np.vstack(vectors).astype(np.float32) if vectors else np.empty((0, self.embedder.dimension), dtype=np.float32)
        self._rebuild_index()
        self._rebuild_semantic_edges()

    def _rebuild_index(self) -> None:
        if len(self.data_points) == 0:
            self.nn_index = None
            return
        self.nn_index = NearestNeighbors(metric="cosine", algorithm="brute")
        self.nn_index.fit(self.data_points)

    def _rebuild_semantic_edges(self, threshold: float = 0.55) -> None:
        self.graph.remove_edges_from(list(self.graph.edges))
        if len(self.data_points) < 2:
            return
        sims = cosine_similarity(self.data_points)
        for i in range(len(self.resource_ids)):
            for j in range(i + 1, len(self.resource_ids)):
                score = float(sims[i, j])
                if score >= threshold:
                    self.graph.add_edge(
                        self.resource_ids[i], self.resource_ids[j],
                        weight=score, relation="semantic_similarity", tags=["auto"],
                    )

    def add_resource(
        self,
        resource_id: str,
        resource_text: str,
        metadata: Optional[Mapping[str, Any]] = None,
        tags: Optional[Sequence[str]] = None,
        seed: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not resource_id or not resource_id.strip():
            raise ValueError("resource_id is required")
        metadata = dict(metadata or {})
        tags = list(dict.fromkeys(tags or []))
        compressed = AbsoluteCodeSystem.compress_text(resource_text, seed=seed)
        vector = self.embedder.encode(resource_text)
        now = utc_now().isoformat()
        with self.db_lock:
            existing = self.conn.execute("SELECT created_at FROM resources WHERE id=?", (resource_id,)).fetchone()
            created_at = existing["created_at"] if existing else now
            self.conn.execute(
                """
                INSERT OR REPLACE INTO resources
                (id, compressed_data, vector, vector_dim, embedder, metadata, tags, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    resource_id, canonical_json(compressed), self._vector_to_blob(vector), self.embedder.dimension,
                    self.embedder.name, canonical_json(metadata), canonical_json(tags), created_at, now,
                ),
            )
            self.conn.commit()
        self._reload_single_resource(resource_id, vector, metadata, tags)
        return {"status": "success", "resource_id": resource_id, "sha256": compressed["raw_sha256"]}

    def _reload_single_resource(self, resource_id: str, vector: np.ndarray, metadata: Mapping[str, Any], tags: Sequence[str]) -> None:
        self.graph.add_node(resource_id, metadata=dict(metadata), tags=list(tags))
        if resource_id in self.resource_ids:
            idx = self.resource_ids.index(resource_id)
            self.data_points[idx] = vector
        else:
            self.resource_ids.append(resource_id)
            if len(self.data_points) == 0:
                self.data_points = np.asarray([vector], dtype=np.float32)
            else:
                self.data_points = np.vstack([self.data_points, vector]).astype(np.float32)
        self._rebuild_index()
        self._rebuild_semantic_edges()

    def get_resource(self, resource_id: str, include_text: bool = True) -> Optional[Dict[str, Any]]:
        row = self.conn.execute("SELECT * FROM resources WHERE id=?", (resource_id,)).fetchone()
        if row is None:
            return None
        result = {
            "id": row["id"],
            "metadata": json.loads(row["metadata"]),
            "tags": json.loads(row["tags"]),
            "embedder": row["embedder"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        if include_text:
            ok, text = AbsoluteCodeSystem.decompress_text(json.loads(row["compressed_data"]))
            result["text"] = text if ok else None
            result["integrity_ok"] = ok
        return result

    def find_concept_neighbors(self, query: Union[str, np.ndarray], k: int = 5) -> List[Dict[str, Any]]:
        if self.nn_index is None or not self.resource_ids:
            return []
        if isinstance(query, str):
            vector = self.embedder.encode(query)
        else:
            vector = np.asarray(query, dtype=np.float32)
            if vector.shape != (self.embedder.dimension,):
                raise ValueError(f"query vector must have shape ({self.embedder.dimension},)")
        distances, indices = self.nn_index.kneighbors(vector.reshape(1, -1), n_neighbors=min(k, len(self.resource_ids)))
        results: List[Dict[str, Any]] = []
        for distance, idx in zip(distances[0], indices[0]):
            resource_id = self.resource_ids[int(idx)]
            node = self.graph.nodes[resource_id]
            results.append(
                {
                    "resource_id": resource_id,
                    "similarity": float(1.0 - distance),
                    "metadata": dict(node.get("metadata", {})),
                    "tags": list(node.get("tags", [])),
                }
            )
        return results

    def personalize_recommendations(self, user_query: str, user_history: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
        results = self.find_concept_neighbors(user_query, k=3)
        if user_history:
            weights = np.linspace(0.5, 1.0, len(user_history), dtype=np.float32)
            weighted = [self.embedder.encode(text) * weight for text, weight in zip(user_history, weights)]
            history_vector = np.mean(weighted, axis=0)
            history_vector /= max(float(np.linalg.norm(history_vector)), 1e-12)
            by_vector = self.find_concept_neighbors(history_vector, k=2)
            seen = {item["resource_id"] for item in results}
            results.extend(item for item in by_vector if item["resource_id"] not in seen)
        return results

    def find_sparse_topics(self, min_count: int = 2, since_year: int = 2021) -> List[Dict[str, Any]]:
        counts: Dict[Tuple[str, int], int] = {}
        for _, node in self.graph.nodes(data=True):
            year = int(node.get("metadata", {}).get("year", 0) or 0)
            for tag in node.get("tags", []):
                counts[(tag, year)] = counts.get((tag, year), 0) + 1
        return [
            {"tag": tag, "year": year, "count": count}
            for (tag, year), count in sorted(counts.items())
            if year >= since_year and count < min_count
        ]

    def knowledge_metrics(self) -> Dict[str, Any]:
        return {
            "resources": len(self.resource_ids),
            "semantic_edges": self.graph.number_of_edges(),
            "embedder": self.embedder.name,
            "vector_dimension": self.embedder.dimension,
        }

    # -----------------------------------------------------------------------
    # Secure evidence acquisition (replaces public-proxy harvesting)
    # -----------------------------------------------------------------------
    @staticmethod
    def _host_is_public(hostname: str) -> bool:
        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            return False
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        return True

    async def fetch_evidence(self, url: str, max_bytes: int = 2_000_000) -> Dict[str, Any]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("only https URLs are allowed")
        allowed_domains = {d.strip().lower() for d in os.getenv("YADO_ALLOWED_DOMAINS", "").split(",") if d.strip()}
        if allowed_domains and parsed.hostname.lower() not in allowed_domains:
            raise ValueError("domain is not allowlisted")
        if not self._host_is_public(parsed.hostname):
            raise ValueError("URL resolves to a non-public network address")

        timeout = aiohttp.ClientTimeout(total=15)
        headers = {"User-Agent": "YADO-Core/2.0 evidence-fetcher"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as response:
                response.raise_for_status()
                body = await response.content.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise ValueError("response too large")
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    raise ValueError(f"unsupported content type: {content_type}")
                text = body.decode(response.charset or "utf-8", errors="replace")
        if "html" in content_type:
            soup = BeautifulSoup(text, "html.parser")
            title = soup.title.get_text(" ", strip=True) if soup.title else ""
            clean_text = " ".join(soup.stripped_strings)
        else:
            title = ""
            clean_text = text
        return {
            "url": url,
            "title": title,
            "text": clean_text,
            "sha256": hashlib.sha256(body).hexdigest(),
            "fetched_at": utc_now().isoformat(),
        }

    # -----------------------------------------------------------------------
    # HMAC registration/authentication
    # -----------------------------------------------------------------------
    def generate_registration_token(self, expires_seconds: int = 3600) -> Tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + expires_seconds
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self.db_lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO registration_tokens(token_hash, expires_at) VALUES(?,?)",
                (token_hash, expires_at),
            )
            self.conn.commit()
        return token, datetime.fromtimestamp(expires_at, tz=UTC)

    def register_point(self, token: str, permissions: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self.db_lock:
            row = self.conn.execute("SELECT expires_at FROM registration_tokens WHERE token_hash=?", (token_hash,)).fetchone()
            if row is None:
                return {"status": "error", "message": "invalid token"}
            if time.time() > float(row["expires_at"]):
                self.conn.execute("DELETE FROM registration_tokens WHERE token_hash=?", (token_hash,))
                self.conn.commit()
                return {"status": "error", "message": "token expired"}
            key_id = secrets.token_urlsafe(16)
            secret = secrets.token_urlsafe(32)
            encrypted = self._cipher.encrypt(secret.encode("utf-8"))
            perms = list(permissions or ["read"])
            self.conn.execute(
                "INSERT INTO access_keys(key_id, encrypted_secret, permissions, created_at) VALUES(?,?,?,?)",
                (key_id, encrypted, canonical_json(perms), utc_now().isoformat()),
            )
            self.conn.execute("DELETE FROM registration_tokens WHERE token_hash=?", (token_hash,))
            self.conn.commit()
        return {"status": "success", "key_id": key_id, "key_secret": secret, "permissions": perms}

    def verify_signature(self, key_id: str, signature: str, timestamp: str, method: str, path: str, body: bytes) -> Dict[str, Any]:
        row = self.conn.execute("SELECT encrypted_secret, permissions FROM access_keys WHERE key_id=?", (key_id,)).fetchone()
        if row is None:
            raise ValueError("invalid key id")
        try:
            request_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if request_time.tzinfo is None:
                request_time = request_time.replace(tzinfo=UTC)
        except ValueError as exc:
            raise ValueError("invalid timestamp") from exc
        if abs((utc_now() - request_time.astimezone(UTC)).total_seconds()) > 300:
            raise ValueError("request expired")
        secret = self._cipher.decrypt(row["encrypted_secret"])
        message = method.upper().encode() + b"\n" + path.encode() + b"\n" + timestamp.encode() + b"\n" + body
        expected = hmac.new(secret, message, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        return {"key_id": key_id, "permissions": json.loads(row["permissions"])}


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
class ResourceIn(BaseModel):
    resource_id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    seed: Optional[str] = None


class GoalIn(BaseModel):
    objective: str
    required_capabilities: Dict[str, float]
    success_criteria: Dict[str, Any] = Field(default_factory=dict)


class ExperimentIn(BaseModel):
    candidate_id: str
    baseline_score: float
    candidate_score: float
    ablation_score: float
    min_gain: float = 0.05
    min_ablation_drop: float = 0.03


def create_app(system: Optional[UnifiedCognitiveSystem] = None) -> FastAPI:
    core = system or UnifiedCognitiveSystem(os.getenv("YADO_DB_PATH", "cognitive_system_v2.db"))
    app = FastAPI(title="YADO-CORE", version="2.0.0")
    app.state.core = core

    async def require_signed_request(
        request: Request,
        x_api_key_id: Optional[str] = Header(default=None),
        x_api_signature: Optional[str] = Header(default=None),
        x_api_timestamp: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        if not all([x_api_key_id, x_api_signature, x_api_timestamp]):
            raise HTTPException(status_code=401, detail="missing authentication headers")
        body = await request.body()
        target = request.url.path
        if request.url.query:
            target += "?" + request.url.query
        try:
            return core.verify_signature(
                key_id=x_api_key_id,
                signature=x_api_signature,
                timestamp=x_api_timestamp,
                method=request.method,
                path=target,
                body=body,
            )
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @app.get("/")
    def index() -> Dict[str, Any]:
        return {"status": "YADO-CORE running", "version": "2.0.0"}

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok", "uptime_seconds": (utc_now() - core.start_time).total_seconds()}

    @app.get("/metrics")
    def metrics() -> Dict[str, Any]:
        return {
            **core.knowledge_metrics(),
            "goals": len(core.executive.goals),
            "capabilities": len(core.executive.capabilities),
            "uptime_seconds": (utc_now() - core.start_time).total_seconds(),
        }

    @app.post("/registration-token")
    def registration_token(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
        admin_token = os.getenv("YADO_ADMIN_TOKEN")
        if not admin_token:
            raise HTTPException(status_code=503, detail="YADO_ADMIN_TOKEN is not configured")
        supplied = authorization.removeprefix("Bearer ") if authorization else ""
        if not secrets.compare_digest(supplied, admin_token):
            raise HTTPException(status_code=401, detail="unauthorized")
        token, expires = core.generate_registration_token()
        return {"token": token, "expires": expires.isoformat()}

    @app.post("/register")
    def register(payload: Dict[str, Any]) -> Dict[str, Any]:
        result = core.register_point(str(payload.get("token", "")), payload.get("permissions"))
        if result.get("status") != "success":
            raise HTTPException(status_code=400, detail=result.get("message", "registration failed"))
        return result

    def require_permission(identity: Dict[str, Any], permission: str) -> None:
        permissions = set(identity.get("permissions", []))
        if permission not in permissions and "*" not in permissions:
            raise HTTPException(status_code=403, detail=f"missing permission: {permission}")

    @app.post("/resources")
    def add_resource(payload: ResourceIn, identity: Dict[str, Any] = Depends(require_signed_request)) -> Dict[str, Any]:
        require_permission(identity, "write")
        return core.add_resource(payload.resource_id, payload.text, payload.metadata, payload.tags, payload.seed)

    @app.get("/resources/{resource_id}")
    def get_resource(resource_id: str, identity: Dict[str, Any] = Depends(require_signed_request)) -> Dict[str, Any]:
        require_permission(identity, "read")
        found = core.get_resource(resource_id)
        if found is None:
            raise HTTPException(status_code=404, detail="resource not found")
        return found

    @app.get("/search")
    def search(q: str, k: int = 5, identity: Dict[str, Any] = Depends(require_signed_request)) -> Dict[str, Any]:
        require_permission(identity, "read")
        return {"results": core.find_concept_neighbors(q, max(1, min(k, 50)))}

    @app.post("/goals")
    def create_goal(payload: GoalIn, identity: Dict[str, Any] = Depends(require_signed_request)) -> Dict[str, Any]:
        require_permission(identity, "write")
        return asdict(core.executive.create_goal(payload.objective, payload.required_capabilities, payload.success_criteria))

    @app.post("/goals/{goal_id}/cycle")
    def run_cycle(goal_id: str, identity: Dict[str, Any] = Depends(require_signed_request)) -> Dict[str, Any]:
        require_permission(identity, "write")
        if goal_id not in core.executive.goals:
            raise HTTPException(status_code=404, detail="goal not found")
        return core.executive.run_cycle(goal_id)

    @app.post("/experiments/evaluate")
    def evaluate_experiment(payload: ExperimentIn, identity: Dict[str, Any] = Depends(require_signed_request)) -> Dict[str, Any]:
        require_permission(identity, "write")
        if payload.candidate_id not in core.executive.candidates:
            raise HTTPException(status_code=404, detail="candidate not found")
        receipt = core.executive.evaluate_candidate(
            payload.candidate_id,
            payload.baseline_score,
            payload.candidate_score,
            payload.ablation_score,
            payload.min_gain,
            payload.min_ablation_drop,
        )
        return asdict(receipt)

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app(), host=os.getenv("YADO_HOST", "127.0.0.1"), port=int(os.getenv("YADO_PORT", "8000")))
