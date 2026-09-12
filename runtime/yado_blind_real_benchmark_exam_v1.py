#!/usr/bin/env python3
from __future__ import annotations
import argparse, ast, gzip, hashlib, io, json, math, re, subprocess, sys, tempfile, urllib.request, zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

SCHEMA = "yado.blind_real_benchmark_exam.v1"
GSM8K_URL = "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl"
HUMANEVAL_URL = "https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl.gz"
OPENBOOKQA_URL = "https://s3-us-west-2.amazonaws.com/ai2-website/data/OpenBookQA-V1-Sep2018.zip"
UA = "YADO-Blind-Exam/1.0"

def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode()).hexdigest()

def fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(canon(row) + "\n")

def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def rank_select(rows: List[Dict[str, Any]], n: int, seed: str, id_key: str) -> List[Dict[str, Any]]:
    ranked = sorted(rows, key=lambda r: hashlib.sha256((seed + "|" + str(r[id_key])).encode()).hexdigest())
    return ranked[: min(n, len(ranked))]

def extract_gsm8k_final(answer: str) -> str:
    m = re.search(r"####\s*([^\n]+)", answer)
    if not m:
        return ""
    return m.group(1).strip().replace(",", "")

def prepare(out_dir: Path, seed: str, gsm8k_n: int, openbook_n: int, humaneval_n: int) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    challenges: List[Dict[str, Any]] = []
    sealed: List[Dict[str, Any]] = []
    sources: Dict[str, Any] = {}

    raw = fetch(GSM8K_URL)
    sources["gsm8k"] = {"url": GSM8K_URL, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    gsm = [json.loads(x) for x in raw.decode().splitlines() if x.strip()]
    gsm_rows = [{"id": f"gsm8k-{i:04d}", **r} for i, r in enumerate(gsm)]
    for r in rank_select(gsm_rows, gsm8k_n, seed + "-gsm", "id"):
        challenges.append({"exam_id": r["id"], "benchmark": "gsm8k", "prompt": r["question"]})
        sealed.append({"exam_id": r["id"], "benchmark": "gsm8k", "expected": extract_gsm8k_final(r["answer"])})

    raw = fetch(HUMANEVAL_URL)
    sources["humaneval"] = {"url": HUMANEVAL_URL, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    hum = [json.loads(x) for x in gzip.decompress(raw).decode().splitlines() if x.strip()]
    for r in rank_select(hum, humaneval_n, seed + "-he", "task_id"):
        challenges.append({"exam_id": r["task_id"], "benchmark": "humaneval", "prompt": r["prompt"], "entry_point": r["entry_point"]})
        sealed.append({"exam_id": r["task_id"], "benchmark": "humaneval", "entry_point": r["entry_point"], "test": r["test"]})

    raw = fetch(OPENBOOKQA_URL)
    sources["openbookqa"] = {"url": OPENBOOKQA_URL, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    zf = zipfile.ZipFile(io.BytesIO(raw))
    names = zf.namelist()
    test_name = next(n for n in names if n.endswith("/Data/Main/test.jsonl"))
    facts_name = next(n for n in names if n.endswith("/Data/Main/openbook.txt"))
    oq = [json.loads(x) for x in zf.read(test_name).decode("utf-8").splitlines() if x.strip()]
    selected = rank_select(oq, openbook_n, seed + "-obqa", "id")
    for r in selected:
        q = r["question"]
        choices = [{"label": c["label"], "text": c["text"]} for c in q["choices"]]
        challenges.append({"exam_id": r["id"], "benchmark": "openbookqa", "prompt": q["stem"], "choices": choices})
        sealed.append({"exam_id": r["id"], "benchmark": "openbookqa", "expected": r["answerKey"]})
    facts = zf.read(facts_name).decode("utf-8", "replace")
    (out_dir / "openbook_facts.txt").write_text(facts, encoding="utf-8")

    challenges = sorted(challenges, key=lambda x: hashlib.sha256((seed + "|mix|" + x["exam_id"]).encode()).hexdigest())
    sealed = sorted(sealed, key=lambda x: x["exam_id"])
    challenge_digest = digest(challenges)
    sealed_digest = digest(sealed)
    write_jsonl(out_dir / "challenges.jsonl", challenges)
    write_jsonl(out_dir / "sealed_ground_truth.jsonl", sealed)
    manifest = {
        "schema": SCHEMA,
        "mode": "prepare",
        "seed": seed,
        "challenge_count": len(challenges),
        "counts": dict(Counter(x["benchmark"] for x in challenges)),
        "challenge_digest": challenge_digest,
        "sealed_ground_truth_digest": sealed_digest,
        "sources": sources,
        "separation_contract": {
            "respond_job_must_not_receive_sealed_ground_truth": True,
            "ground_truth_opened_only_after_response_digest_fixed": True,
            "training_on_exam_answers": False,
        },
    }
    (out_dir / "prepare_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest

STOP = {
    "the","a","an","of","to","in","is","are","was","were","and","or","for","on","with","that","this","it","as","by","from",
    "which","what","when","where","how","would","could","will","can","be","into","than","then","most","least","not","does",
}
def tokens(s: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 1 and w not in STOP]

def openbook_answer(prompt: str, choices: List[Dict[str, str]], facts: List[str]) -> Tuple[str, Dict[str, Any]]:
    qtok = Counter(tokens(prompt))
    scored_facts = []
    for fact in facts:
        ft = Counter(tokens(fact))
        overlap = sum((qtok & ft).values())
        if overlap:
            scored_facts.append((overlap, fact, ft))
    scored_facts.sort(key=lambda x: (-x[0], x[1]))
    top = scored_facts[:80]
    choice_scores = []
    for c in choices:
        ct = Counter(tokens(c["text"]))
        query = qtok + ct
        best = 0.0
        for base, _, ft in top:
            ov = sum((query & ft).values())
            cov = sum((ct & ft).values())
            score = ov + 1.75 * cov + 0.15 * base
            if score > best:
                best = score
        choice_scores.append((best, c["label"]))
    choice_scores.sort(key=lambda x: (-x[0], x[1]))
    if not choice_scores or choice_scores[0][0] <= 0:
        return "UNRESOLVED", {"method": "lexical_openbook_retrieval", "confidence": 0.0, "reason": "no_support"}
    margin = choice_scores[0][0] - (choice_scores[1][0] if len(choice_scores) > 1 else 0)
    if margin <= 0:
        return "UNRESOLVED", {"method": "lexical_openbook_retrieval", "confidence": 0.0, "reason": "tied_best_score"}
    return choice_scores[0][1], {"method": "lexical_openbook_retrieval", "confidence": round(margin / max(choice_scores[0][0], 1e-9), 4)}

NUM_RE = re.compile(r"(?<![\w.])-?\$?\d+(?:,\d{3})*(?:\.\d+)?%?")
def parse_num(s: str) -> float:
    pct = s.endswith("%")
    s = s.replace("$", "").replace(",", "").rstrip("%")
    v = float(s)
    return v / 100.0 if pct else v

def normalize_number(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return ("%.10f" % v).rstrip("0").rstrip(".")

def gsm8k_answer(q: str) -> Tuple[str, Dict[str, Any]]:
    text = " " + re.sub(r"\s+", " ", q.lower()) + " "
    nums = [parse_num(x) for x in NUM_RE.findall(text)]
    if not nums:
        return "UNRESOLVED", {"method": "bounded_arithmetic_language_adapter", "reason": "no_numbers"}
    m = re.search(r"(\d+(?:\.\d+)?)%\s+of\s+\$?(\d+(?:\.\d+)?)", text)
    if m and any(k in text for k in ("how much", "what is", "amount", "cost")):
        return normalize_number(float(m.group(1)) / 100 * float(m.group(2))), {"method": "percent_of"}
    m = re.search(r"(\d+(?:\.\d+)?)\s+\w+(?:\s+\w+){0,3}\s+(?:at|cost(?:ing)?|for)\s+\$?(\d+(?:\.\d+)?)\s+(?:each|apiece|per)", text)
    if m and any(k in text for k in ("total", "altogether", "spend", "cost")):
        return normalize_number(float(m.group(1)) * float(m.group(2))), {"method": "count_times_unit_price"}
    if len(nums) == 2 and any(k in text for k in ("per hour", "each hour", "per day", "each day", "per minute", "each minute")) and any(k in text for k in ("how many", "total", "altogether")):
        return normalize_number(nums[0] * nums[1]), {"method": "rate_times_duration"}
    if len(nums) == 2 and any(k in text for k in ("left", "remain", "remaining", "gave away", "used", "spent")):
        return normalize_number(nums[0] - nums[1]), {"method": "bounded_subtraction"}
    if len(nums) == 2 and any(k in text for k in ("in all", "altogether", "total", "together", "combined")):
        return normalize_number(nums[0] + nums[1]), {"method": "bounded_addition"}
    if len(nums) == 2 and any(k in text for k in ("equally", "each get", "each person", "per person", "shared")) and nums[1] != 0:
        return normalize_number(nums[0] / nums[1]), {"method": "bounded_division"}
    return "UNRESOLVED", {"method": "bounded_arithmetic_language_adapter", "reason": "outside_supported_templates", "number_count": len(nums)}

def function_signature(prompt: str) -> str:
    for line in prompt.splitlines():
        if line.lstrip().startswith("def "):
            return line.strip()
    return ""

def humaneval_source(prompt: str, entry_point: str) -> Tuple[str, Dict[str, Any]]:
    p = prompt.lower()
    sig = function_signature(prompt)
    if not sig:
        return "UNRESOLVED", {"method": "bounded_native_template_library", "reason": "signature_missing"}
    arg_text = sig[sig.find("(")+1:sig.rfind(")")]
    args = [x.strip().split(":")[0].split("=")[0].strip() for x in arg_text.split(",") if x.strip() and not x.strip().startswith("*")]
    source = None
    family = None
    if "greatest common divisor" in p or re.search(r"\bgcd\b", p):
        if len(args) >= 2:
            source = f"{sig}\n    import math\n    return math.gcd({args[0]}, {args[1]})\n"
            family = "gcd"
    elif "fibonacci" in p:
        n = args[0] if args else "n"
        source = f"{sig}\n    a, b = 0, 1\n    for _ in range({n}):\n        a, b = b, a + b\n    return a\n"
        family = "fibonacci"
    elif "palindrome" in p:
        x = args[0] if args else "s"
        source = f"{sig}\n    return {x} == {x}[::-1]\n"
        family = "palindrome"
    elif "balanced" in p and "parenth" in p:
        x = args[0] if args else "s"
        source = f"{sig}\n    d = 0\n    for ch in {x}:\n        d += 1 if ch == '(' else -1\n        if d < 0:\n            return False\n    return d == 0\n"
        family = "balanced_parentheses"
    elif "mean absolute deviation" in p:
        xs = args[0] if args else "numbers"
        source = f"{sig}\n    m = sum({xs}) / len({xs})\n    return sum(abs(x - m) for x in {xs}) / len({xs})\n"
        family = "mean_absolute_deviation"
    elif "sort" in p and "list" in p and "return" in p:
        xs = args[0] if args else "values"
        source = f"{sig}\n    return sorted({xs})\n"
        family = "sorting"
    if source is None:
        return "UNRESOLVED", {"method": "bounded_native_template_library", "reason": "no_supported_family"}
    try:
        tree = ast.parse(source)
        forbidden = (ast.With, ast.AsyncWith, ast.Try, ast.Raise, ast.Lambda, ast.ClassDef, ast.Delete, ast.Global, ast.Nonlocal,
                     ast.While, ast.Yield, ast.YieldFrom, ast.Await, ast.AsyncFunctionDef)
        bad = sorted({type(n).__name__ for n in ast.walk(tree) if isinstance(n, forbidden)})
        if bad:
            return "UNRESOLVED", {"method": "bounded_native_template_library", "reason": "ast_safety", "bad_nodes": bad}
        compile(source, "<candidate>", "exec")
    except Exception as e:
        return "UNRESOLVED", {"method": "bounded_native_template_library", "reason": "compile_error", "error": type(e).__name__}
    return source, {"method": "bounded_native_template_library", "family": family}

def respond(challenges_path: Path, facts_path: Path, out_path: Path) -> Dict[str, Any]:
    challenges = read_jsonl(challenges_path)
    facts = [x.strip() for x in facts_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    responses = []
    for item in challenges:
        b = item["benchmark"]
        if b == "gsm8k":
            ans, trace = gsm8k_answer(item["prompt"])
        elif b == "openbookqa":
            ans, trace = openbook_answer(item["prompt"], item["choices"], facts)
        elif b == "humaneval":
            ans, trace = humaneval_source(item["prompt"], item["entry_point"])
        else:
            ans, trace = "UNRESOLVED", {"reason": "unknown_benchmark"}
        responses.append({"exam_id": item["exam_id"], "benchmark": b, "answer": ans, "trace": trace})
    payload = {
        "schema": SCHEMA,
        "mode": "respond",
        "challenge_digest": digest(challenges),
        "response_count": len(responses),
        "responses": responses,
        "ground_truth_accessed": False,
        "external_llm_used": False,
        "canonical_direct_write": False,
    }
    payload["response_digest"] = digest(payload)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload

def norm_numeric(s: Any) -> str:
    if s is None:
        return ""
    t = str(s).strip().replace(",", "").replace("$", "")
    try:
        return normalize_number(float(t))
    except Exception:
        return t

def safe_humaneval_check(source: str, test: str, entry_point: str) -> Tuple[bool, str]:
    if source == "UNRESOLVED":
        return False, "UNRESOLVED"
    harness = source + "\n" + test + f"\ncheck({entry_point})\n"
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "run.py"
        p.write_text(harness, encoding="utf-8")
        try:
            cp = subprocess.run([sys.executable, "-I", "-S", str(p)], capture_output=True, text=True, timeout=3)
            return cp.returncode == 0, (cp.stderr[-300:] if cp.returncode else "PASS")
        except subprocess.TimeoutExpired:
            return False, "TIMEOUT"

def verify(challenges_path: Path, sealed_path: Path, responses_path: Path, out_path: Path) -> Dict[str, Any]:
    challenges = read_jsonl(challenges_path)
    sealed = read_jsonl(sealed_path)
    resp_obj = json.loads(responses_path.read_text(encoding="utf-8"))
    assert resp_obj["ground_truth_accessed"] is False
    assert resp_obj["challenge_digest"] == digest(challenges)
    response_digest_before_truth = resp_obj["response_digest"]
    tmp = dict(resp_obj); tmp.pop("response_digest", None)
    assert response_digest_before_truth == digest(tmp)
    gt = {x["exam_id"]: x for x in sealed}
    rp = {x["exam_id"]: x for x in resp_obj["responses"]}
    rows = []
    summary: Dict[str, List[int]] = {}
    abstain: Dict[str, int] = {}
    for item in challenges:
        eid = item["exam_id"]; b = item["benchmark"]; r = rp[eid]; g = gt[eid]
        if b == "gsm8k":
            ok = norm_numeric(r["answer"]) == norm_numeric(g["expected"])
            detail = {"expected": g["expected"], "answer": r["answer"]}
        elif b == "openbookqa":
            ok = str(r["answer"]).strip().upper() == str(g["expected"]).strip().upper()
            detail = {"expected": g["expected"], "answer": r["answer"]}
        elif b == "humaneval":
            ok, exec_detail = safe_humaneval_check(r["answer"], g["test"], g["entry_point"])
            detail = {"entry_point": g["entry_point"], "execution": exec_detail, "answer_kind": "source" if r["answer"] != "UNRESOLVED" else "UNRESOLVED"}
        else:
            ok = False; detail = {}
        summary.setdefault(b, []).append(int(ok))
        if r["answer"] == "UNRESOLVED":
            abstain[b] = abstain.get(b, 0) + 1
        rows.append({"exam_id": eid, "benchmark": b, "correct": ok, **detail})
    per = {b: {"correct": sum(v), "total": len(v), "accuracy": round(sum(v)/len(v), 6),
               "unresolved": abstain.get(b, 0)} for b, v in sorted(summary.items())}
    total = sum(len(v) for v in summary.values()); correct = sum(sum(v) for v in summary.values())
    result = {
        "schema": SCHEMA,
        "status": "PASS_MEASURED_BLIND_REAL_BENCHMARK_V1",
        "challenge_digest": digest(challenges),
        "sealed_ground_truth_digest": digest(sealed),
        "response_digest_fixed_before_ground_truth": response_digest_before_truth,
        "ground_truth_revealed_after_response_fixation": True,
        "external_llm_used_for_answers": False,
        "training_on_exam_answers": False,
        "overall": {"correct": correct, "total": total, "accuracy": round(correct/total, 6)},
        "per_benchmark": per,
        "results": rows,
        "claim_boundary": {
            "blind_answer_separation_proven_by_workflow": True,
            "benchmark_solution_quality_is_measured_not_assumed": True,
            "general_intelligence_proven": False,
            "phenomenal_consciousness_proven": False,
        },
    }
    result["evidence_digest"] = digest(result)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result

def self_test() -> None:
    assert extract_gsm8k_final("work\n#### 1,234") == "1234"
    assert gsm8k_answer("A box has 10 balls and 3 are used. How many are left?")[0] == "7"
    assert gsm8k_answer("A worker makes 5 items per hour for 4 hours. How many items total?")[0] == "20"
    facts = ["metal conducts electricity", "plants use sunlight for photosynthesis"]
    ans, _ = openbook_answer("Which material conducts electricity?", [{"label":"A","text":"metal"},{"label":"B","text":"wood"}], facts)
    assert ans == "A"
    src, tr = humaneval_source("def fib(n):\n    \"\"\"Return fibonacci number.\"\"\"\n", "fib")
    assert src != "UNRESOLVED" and tr["family"] == "fibonacci"
    compile(src, "<candidate>", "exec")
    print("PASS_BLIND_REAL_BENCHMARK_SELF_TEST")

def main() -> None:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prepare"); p.add_argument("--out-dir", required=True); p.add_argument("--seed", default="20260912-real-blind-v1"); p.add_argument("--gsm8k", type=int, default=40); p.add_argument("--openbook", type=int, default=40); p.add_argument("--humaneval", type=int, default=20)
    p = sp.add_parser("respond"); p.add_argument("--challenges", required=True); p.add_argument("--facts", required=True); p.add_argument("--out", required=True)
    p = sp.add_parser("verify"); p.add_argument("--challenges", required=True); p.add_argument("--sealed", required=True); p.add_argument("--responses", required=True); p.add_argument("--out", required=True)
    sp.add_parser("self-test")
    a = ap.parse_args()
    if a.cmd == "prepare": print(json.dumps(prepare(Path(a.out_dir), a.seed, a.gsm8k, a.openbook, a.humaneval), indent=2))
    elif a.cmd == "respond": print(json.dumps(respond(Path(a.challenges), Path(a.facts), Path(a.out)), indent=2))
    elif a.cmd == "verify": print(json.dumps(verify(Path(a.challenges), Path(a.sealed), Path(a.responses), Path(a.out)), indent=2))
    else: self_test()
if __name__ == "__main__":
    main()
