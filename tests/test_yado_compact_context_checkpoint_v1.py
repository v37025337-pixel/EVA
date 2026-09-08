from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from yado_compact_context_checkpoint_v1 import build_checkpoint

CHECKPOINT = ROOT / "canonical" / "yado-compact-context-checkpoint-v1.json"


class CompactContextCheckpointV1Tests(unittest.TestCase):
    def test_checkpoint_matches_live_canonical_state(self) -> None:
        committed = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
        live = build_checkpoint()
        self.assertEqual(committed, live)

    def test_hot_context_invariants(self) -> None:
        checkpoint = build_checkpoint()
        self.assertEqual(checkpoint["status"], "PASS")
        self.assertEqual(checkpoint["active_graph"]["orphans"], [])
        self.assertEqual(len(checkpoint["open_deficits"]), 1)
        self.assertFalse(checkpoint["g3_genesis_performed"])
        self.assertEqual(
            checkpoint["hydration"]["normal_start"],
            ["canonical/yado-compact-context-checkpoint-v1.json"],
        )

    def test_checkpoint_stays_small(self) -> None:
        encoded = json.dumps(build_checkpoint(), sort_keys=True).encode("utf-8")
        self.assertLessEqual(len(encoded), 32768)


if __name__ == "__main__":
    unittest.main()
