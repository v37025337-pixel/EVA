from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "candidates" / "g2-self-evolution"
RECEIPT = ROOT / "receipts" / "yado-external-source-evolution-v1.json"
EXTERNAL_COMMIT = "b69f0d5b8d13625ac8f0bd3e177cc2d9ec3c2119"
BASE = f"https://raw.githubusercontent.com/exercism/problem-specifications/{EXTERNAL_COMMIT}/exercises"
SOURCES = {
    "leap": f"{BASE}/leap/canonical-data.json",
    "grains": f"{BASE}/grains/canonical-data.json",
    "difference-of-squares": f"{BASE}/difference-of-squares/canonical-data.json",
}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_text(text: str) -> str:
    return sha_bytes(text.encode("utf-8"))


def fetch_json(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "YADO-External-Source-Evolution-V1/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(2_000_000)
        status = int(getattr(response, "status", 200) or 200)
    if status != 200:
        raise RuntimeError(f"external source returned HTTP {status}: {url}")
    return json.loads(raw.decode("utf-8")), {"url": url, "http_status": status, "sha256": sha_bytes(raw), "bytes": len(raw)}


def flatten_cases(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        if {"property", "input", "expected"} <= set(node):
            found.append(node)
        for child in node.get("cases", []):
            found.extend(flatten_cases(child))
    elif isinstance(node, list):
        for child in node:
            found.extend(flatten_cases(child))
    return found


def split_external(data: dict[str, dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    leap = flatten_cases(data["leap"])
    if len(leap) != 9:
        raise RuntimeError(f"unexpected leap case count: {len(leap)}")

    grains_all = [
        c for c in flatten_cases(data["grains"])
        if c.get("property") == "square" and isinstance(c.get("expected"), int) and not isinstance(c.get("expected"), bool)
    ]
    if len(grains_all) != 7:
        raise RuntimeError(f"unexpected numeric grains case count: {len(grains_all)}")

    diff_all = flatten_cases(data["difference-of-squares"])
    grouped: dict[str, list[dict[str, Any]]] = {}
    for case in diff_all:
        grouped.setdefault(str(case["property"]), []).append(case)
    required = {"squareOfSum", "sumOfSquares", "differenceOfSquares"}
    if set(grouped) != required or any(len(grouped[p]) != 3 for p in required):
        raise RuntimeError("unexpected difference-of-squares shape")

    training = {
        "leap": leap[:7],
        "grains": grains_all[:5],
        "difference-of-squares": [c for p in sorted(required) for c in grouped[p][:2]],
    }
    sealed = {
        "leap": leap[7:],
        "grains": grains_all[5:],
        "difference-of-squares": [grouped[p][2] for p in sorted(required)],
    }
    return training, sealed


def case_fingerprint(case: dict[str, Any]) -> str:
    public = {
        "uuid": case.get("uuid"),
        "description": case.get("description"),
        "property": case.get("property"),
        "input": case.get("input"),
        "expected": case.get("expected"),
    }
    return sha_text(json.dumps(public, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def evolve_leap(cases: list[dict[str, Any]]) -> dict[str, int]:
    rows = [(int(c["input"]["year"]), bool(c["expected"]), str(c.get("description", ""))) for c in cases]
    divisors = sorted({d for d in range(2, 401) if any(year % d == 0 for year, _, _ in rows)})
    mentions: dict[int, int] = {}
    for _, _, description in rows:
        for token in re.findall(r"\b\d+\b", description):
            value = int(token)
            mentions[value] = mentions.get(value, 0) + 1

    ranked: list[tuple[tuple[int, int, int, int, int], tuple[int, int, int]]] = []
    for a in divisors:
        for b in divisors:
            if b % a:
                continue
            for c in divisors:
                if c % b:
                    continue
                errors = 0
                for year, expected, _ in rows:
                    predicted = (year % a == 0) and ((year % b != 0) or (year % c == 0))
                    errors += int(predicted != expected)
                semantic_support = mentions.get(a, 0) + mentions.get(b, 0) + mentions.get(c, 0)
                # Training error is primary. Textual constants in the external training descriptions
                # break ties; no sealed expected value is visible here.
                key = (errors, -semantic_support, a, b, -c)
                ranked.append((key, (a, b, c)))
    ranked.sort(key=lambda item: item[0])
    best_key, (a, b, c) = ranked[0]
    if best_key[0] != 0:
        raise RuntimeError("leap grammar could not fit external training cases")
    return {"a": a, "b": b, "c": c}


def evolve_grains(cases: list[dict[str, Any]]) -> dict[str, int]:
    rows = [(int(c["input"]["square"]), int(c["expected"])) for c in cases]
    ranked: list[tuple[tuple[int, int, int], tuple[int, int]]] = []
    for base in range(2, 11):
        for offset in range(-3, 4):
            errors = 0
            for square, expected in rows:
                exponent = square + offset
                if exponent < 0:
                    errors += 1
                    continue
                errors += int(base ** exponent != expected)
            ranked.append(((errors, abs(offset), base), (base, offset)))
    ranked.sort(key=lambda item: item[0])
    key, (base, offset) = ranked[0]
    if key[0] != 0:
        raise RuntimeError("grains grammar could not fit external training cases")
    return {"base": base, "offset": offset}


def evolve_difference(cases: list[dict[str, Any]]) -> dict[str, int]:
    by_property: dict[str, list[tuple[int, int]]] = {}
    for c in cases:
        by_property.setdefault(str(c["property"]), []).append((int(c["input"]["number"]), int(c["expected"])))

    square_rows = by_property["squareOfSum"]
    square_ranked: list[tuple[tuple[int, int, int, int, int], tuple[int, int, int]]] = []
    for a in range(-2, 4):
        for divisor in range(1, 7):
            for power in range(1, 4):
                errors = 0
                for n, expected in square_rows:
                    numerator = n * (n + a)
                    if numerator % divisor:
                        errors += 1
                        continue
                    predicted = (numerator // divisor) ** power
                    errors += int(predicted != expected)
                square_ranked.append(((errors, int(a < 0), abs(a) + divisor + power, divisor, power), (a, divisor, power)))
    square_ranked.sort(key=lambda item: item[0])
    square_key, square_params = square_ranked[0]
    if square_key[0] != 0:
        raise RuntimeError("squareOfSum grammar did not fit")

    sum_rows = by_property["sumOfSquares"]
    sum_ranked: list[tuple[tuple[int, int, int, int], tuple[int, int, int]]] = []
    for a in range(-2, 4):
        for b in range(-3, 6):
            for divisor in range(1, 13):
                errors = 0
                for n, expected in sum_rows:
                    numerator = n * (n + a) * (2 * n + b)
                    if numerator % divisor:
                        errors += 1
                        continue
                    errors += int(numerator // divisor != expected)
                sum_ranked.append(((errors, int(a < 0 or b < 0), abs(a) + abs(b) + divisor, divisor), (a, b, divisor)))
    sum_ranked.sort(key=lambda item: item[0])
    sum_key, sum_params = sum_ranked[0]
    if sum_key[0] != 0:
        raise RuntimeError("sumOfSquares grammar did not fit")

    return {
        "square_a": square_params[0],
        "square_divisor": square_params[1],
        "square_power": square_params[2],
        "sum_a": sum_params[0],
        "sum_b": sum_params[1],
        "sum_divisor": sum_params[2],
    }


def seed_source() -> str:
    return '''from __future__ import annotations\n\ndef solve(exercise, prop, data):\n    if exercise == "leap":\n        return False\n    if exercise == "grains":\n        return 1\n    if exercise == "difference-of-squares":\n        return 0\n    raise KeyError(exercise)\n'''


def candidate_source(leap: dict[str, int], grains: dict[str, int], diff: dict[str, int]) -> str:
    return f'''from __future__ import annotations\n\n# Generated by runtime/yado_external_source_evolution_v1.py from external TRAINING cases only.\nLEAP_A = {leap["a"]}\nLEAP_B = {leap["b"]}\nLEAP_C = {leap["c"]}\nGRAINS_BASE = {grains["base"]}\nGRAINS_OFFSET = {grains["offset"]}\nSQUARE_A = {diff["square_a"]}\nSQUARE_DIVISOR = {diff["square_divisor"]}\nSQUARE_POWER = {diff["square_power"]}\nSUM_A = {diff["sum_a"]}\nSUM_B = {diff["sum_b"]}\nSUM_DIVISOR = {diff["sum_divisor"]}\n\ndef square_of_sum(n):\n    return ((n * (n + SQUARE_A)) // SQUARE_DIVISOR) ** SQUARE_POWER\n\ndef sum_of_squares(n):\n    return n * (n + SUM_A) * (2 * n + SUM_B) // SUM_DIVISOR\n\ndef solve(exercise, prop, data):\n    if exercise == "leap":\n        year = int(data["year"])\n        return (year % LEAP_A == 0) and ((year % LEAP_B != 0) or (year % LEAP_C == 0))\n    if exercise == "grains":\n        square = int(data["square"])\n        return GRAINS_BASE ** (square + GRAINS_OFFSET)\n    if exercise == "difference-of-squares":\n        n = int(data["number"])\n        if prop == "squareOfSum":\n            return square_of_sum(n)\n        if prop == "sumOfSquares":\n            return sum_of_squares(n)\n        if prop == "differenceOfSquares":\n            return square_of_sum(n) - sum_of_squares(n)\n        raise KeyError(prop)\n    raise KeyError(exercise)\n'''


def load_source(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def evaluate(module: Any, cases: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    results = []
    for exercise, rows in cases.items():
        for c in rows:
            actual = module.solve(exercise, str(c["property"]), dict(c["input"]))
            ok = actual == c["expected"]
            results.append({
                "exercise": exercise,
                "uuid": c.get("uuid"),
                "property": c["property"],
                "ok": ok,
                "actual": actual,
                "expected": c["expected"],
            })
    correct = sum(int(r["ok"]) for r in results)
    return {"correct": correct, "total": len(results), "score": correct / len(results), "results": results}


def main() -> int:
    external: dict[str, dict[str, Any]] = {}
    provenance = []
    for name, url in SOURCES.items():
        external[name], proof = fetch_json(url)
        proof["exercise"] = name
        proof["commit"] = EXTERNAL_COMMIT
        provenance.append(proof)

    training, sealed = split_external(external)
    training_fingerprints = {k: [case_fingerprint(c) for c in v] for k, v in training.items()}
    sealed_fingerprints = {k: [case_fingerprint(c) for c in v] for k, v in sealed.items()}

    # Evolution receives only the training partitions.
    leap = evolve_leap(training["leap"])
    grains = evolve_grains(training["grains"])
    diff = evolve_difference(training["difference-of-squares"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seed_path = OUT_DIR / "yado_external_synth_seed_v1.py"
    candidate_path = OUT_DIR / "yado_external_synth_candidate_v1.py"
    seed_path.write_text(seed_source(), encoding="utf-8")
    candidate_text = candidate_source(leap, grains, diff)
    compile(candidate_text, str(candidate_path), "exec")
    candidate_path.write_text(candidate_text, encoding="utf-8")

    # Freeze source identity before sealed evaluation.
    frozen_candidate_sha256 = sha_text(candidate_text)
    frozen_seed_sha256 = sha_text(seed_path.read_text(encoding="utf-8"))
    seed_module = load_source("yado_external_seed_v1", seed_path)
    candidate_module = load_source("yado_external_candidate_v1", candidate_path)

    training_candidate = evaluate(candidate_module, training)
    # Sealed expected values are first consumed after candidate source is compiled and hashed.
    sealed_seed = evaluate(seed_module, sealed)
    sealed_candidate = evaluate(candidate_module, sealed)
    if sha_text(candidate_path.read_text(encoding="utf-8")) != frozen_candidate_sha256:
        raise RuntimeError("candidate changed after sealed evaluation gate opened")

    gain = sealed_candidate["score"] - sealed_seed["score"]
    pass_gate = (
        training_candidate["score"] == 1.0
        and sealed_candidate["score"] >= 0.85
        and gain >= 0.50
        and frozen_seed_sha256 != frozen_candidate_sha256
    )
    status = "PASS_SHADOW_G2_EXTERNAL_SOURCE_EVOLUTION_V1" if pass_gate else "WITHHOLD_G2_EXTERNAL_SOURCE_EVOLUTION_V1"

    report = {
        "schema": "yado.external_source_evolution.v1",
        "status": status,
        "source_commit": EXTERNAL_COMMIT,
        "external_provenance": provenance,
        "scope": {
            "exercises": sorted(SOURCES),
            "training_cases": sum(len(v) for v in training.values()),
            "sealed_cases": sum(len(v) for v in sealed.values()),
            "sealed_not_used_for_selection": True,
            "mutation_scope": "bounded Python source synthesis from a fixed grammar",
        },
        "training_fingerprints": training_fingerprints,
        "sealed_fingerprints": sealed_fingerprints,
        "evolved_parameters": {"leap": leap, "grains": grains, "difference-of-squares": diff},
        "seed_source": {"path": str(seed_path.relative_to(ROOT)), "sha256": frozen_seed_sha256},
        "candidate_source": {"path": str(candidate_path.relative_to(ROOT)), "sha256": frozen_candidate_sha256, "compiled": True},
        "metrics": {
            "training_candidate": training_candidate,
            "sealed_seed": sealed_seed,
            "sealed_candidate": sealed_candidate,
            "sealed_absolute_gain": gain,
        },
        "gates": {
            "training_perfect": training_candidate["score"] == 1.0,
            "sealed_score_at_least_0_85": sealed_candidate["score"] >= 0.85,
            "sealed_gain_at_least_0_50": gain >= 0.50,
            "source_changed": frozen_seed_sha256 != frozen_candidate_sha256,
            "candidate_frozen_before_sealed_eval": True,
        },
        "claim_boundary": {
            "general_intelligence_claimed": False,
            "consciousness_claimed": False,
            "unbounded_self_rewrite_claimed": False,
            "note": "This run tests bounded source-level evolution on fixed external Exercism cases. The mutation grammar is externally authored and constrained.",
        },
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": status,
        "training": training_candidate["score"],
        "sealed_seed": sealed_seed["score"],
        "sealed_candidate": sealed_candidate["score"],
        "gain": gain,
        "candidate_sha256": frozen_candidate_sha256,
        "evolved_parameters": report["evolved_parameters"],
    }, sort_keys=True))
    return 0 if pass_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
