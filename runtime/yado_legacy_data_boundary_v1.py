"""Explicit checked recovery APIs for historical G0 data.

These replacements are not additional active cognitive organs. Original classes,
manifests and archives retain their historical bytes and reproducible defects.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
from pathlib import Path
import sys
import zlib

_LEGACY = Path(__file__).resolve().parent / "yado_rc8_v36"
if str(_LEGACY) not in sys.path:
    sys.path.insert(0, str(_LEGACY))

from yado_core_v2 import AbsoluteCodeSystem
from yado_evolution_archive_runtime_v1 import EvolutionArchiveRuntime
from yado_transfer_memory_runtime_v1 import TransferMemoryRuntime


def _envelope_digest(payload):
    unsigned = {key: value for key, value in payload.items() if key != "envelope_sha256"}
    return hashlib.sha256(json.dumps(unsigned, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class CheckedAbsoluteCodeSystem(AbsoluteCodeSystem):
    """Bind new envelope metadata and validate the shape of inherited envelopes."""

    CODEC = "bitpack+zlib-v3"

    def compress_data(self, binary_data):
        payload = super().compress_data(binary_data)
        payload["envelope_sha256"] = _envelope_digest(payload)
        return payload

    def decompress_data(self, compressed):
        try:
            codec = compressed.get("codec")
            if codec not in {self.CODEC, AbsoluteCodeSystem.CODEC}:
                return False, ""
            if codec == self.CODEC and "envelope_sha256" not in compressed:
                return False, ""
            length, pad = compressed["binary_length"], compressed["pad_bits"]
            if type(length) is not int or length < 0 or type(pad) is not int or not 0 <= pad < 8:
                return False, ""
            if pad != (-length) % 8:
                return False, ""
            if "envelope_sha256" in compressed and not hmac.compare_digest(
                    str(compressed["envelope_sha256"]), _envelope_digest(compressed)):
                return False, ""
            raw = zlib.decompress(base64.urlsafe_b64decode(compressed["payload_b64"]))
            if len(raw) * 8 != length + pad:
                return False, ""
            if pad and raw[-1] & ((1 << pad) - 1):
                return False, ""
            if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), str(compressed["raw_sha256"])):
                return False, ""
            return True, self._unpack_bits(raw, length)
        except (KeyError, TypeError, ValueError, AttributeError, zlib.error):
            return False, ""

    @classmethod
    def decompress_text(cls, compressed):
        try:
            length = compressed.get("binary_length")
            if type(length) is not int or length < 0 or length % 8:
                return False, ""
            ok, bits = cls(0).decompress_data(compressed)
            if not ok:
                return False, ""
            raw = bytes(int(bits[index:index + 8], 2) for index in range(0, len(bits), 8))
            return True, raw.decode("utf-8")
        except (TypeError, ValueError, AttributeError, UnicodeDecodeError):
            return False, ""


def _finite_score(value):
    try:
        score = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("LEGACY_NONFINITE_MEMORY_SCORE") from exc
    if not math.isfinite(score):
        raise ValueError("LEGACY_NONFINITE_MEMORY_SCORE")
    return score


class CheckedTransferMemoryRuntime(TransferMemoryRuntime):
    def consolidate(self, experiences):
        _finite_score(self.min_mean_score)
        _finite_score(self.max_failure_rate)
        unique = {}
        for experience in experiences:
            _finite_score(experience.outcome_score)
            previous = unique.get(experience.experience_id)
            if previous is not None and previous.canonical() != experience.canonical():
                raise ValueError("LEGACY_EXPERIENCE_ID_COLLISION")
            unique[experience.experience_id] = experience
        result = super().consolidate(unique.values())
        for memory in result["memories"]:
            _finite_score(memory.mean_score)
        for rejected in result["rejected"]:
            _finite_score(rejected["mean_score"])
        return result

    def retrieve(self, memories, query_tags, *, target_domain="", k=3):
        memories = list(memories)
        for memory in memories:
            _finite_score(memory.mean_score)
            _finite_score(memory.failure_rate)
        return super().retrieve(memories, query_tags, target_domain=target_domain, k=k)


class CheckedEvolutionArchiveRuntime(EvolutionArchiveRuntime):
    def add(self, variant):
        if any(type(value) is not bool for value in variant.constraints.values()):
            raise ValueError("LEGACY_ARCHIVE_CONSTRAINT_NOT_BOOLEAN")
        super().add(variant)

    def admitted(self, variant):
        return all(variant.constraints.get(key) is True for key in self.REQUIRED_CONSTRAINTS)


__all__ = ["CheckedAbsoluteCodeSystem", "CheckedTransferMemoryRuntime", "CheckedEvolutionArchiveRuntime"]
