from __future__ import annotations

import json
from pathlib import Path

import yado_causal_ablation_cycle_v1 as cycle


def main() -> int:
    historical = json.loads(Path(cycle.DEFAULT_HISTORY).read_text(encoding="utf-8"))
    candidate_digest = str(historical.get("candidate_digest") or "").strip()
    if len(candidate_digest) != 64:
        raise RuntimeError(f"INVALID_CANONICAL_CANDIDATE_DIGEST:{candidate_digest!r}")
    # Bind the replay to the digest present in the canonical receipt itself rather than
    # duplicating a historical hash in the experiment harness.
    cycle.HISTORICAL_CANDIDATE_SHA256 = candidate_digest
    return cycle.main()


if __name__ == "__main__":
    raise SystemExit(main())
