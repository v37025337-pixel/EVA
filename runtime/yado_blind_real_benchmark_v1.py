#!/usr/bin/env python3
from __future__ import annotations

import argparse, ast, gzip, hashlib, json, math, re, subprocess, sys, tempfile, urllib.request
from pathlib import Path
from typing import Any

SCHEMA = 'yado.blind_real_benchmark.v1'
SEED = 'YADO-BLIND-REAL-20260912-V1'
GSM8K_URL = 'https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl'
HUMANEVAL_URL = 'https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl.gz'


def jd(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'YADO-Blind-Benchmark/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def rank(key: str) -> str:
    return hashlib.sha256((SEED + '|' + key).encode()).hexdigest()


def parse_gsm_answer(answer: str) -> float | int | None:
    m = re.search(r'####\s*([-+]?\d[\d,]*(?:\.\d+)?)', answer)
    if not m:
        return None
    s = m.group(1).replace(',', '')
    try:
        v = float(s)
        return int(v) if v.is_integer() else v
    except Exception:
        return None


def prepare(prompt_out: Path, key_out: Path, gsm_n: int, he_n: int) -> None:
    gsm_raw = fetch(GSM8K_URL)
    gsm_rows = [json.loads(x) for x in gsm_raw.decode().splitlines() if x.strip()]
    gsm_rows.sort(key=lambda r: rank(r['question']))
    gsm_sel = gsm_rows[:gsm_n]

    he_raw = fetch(HUMANEVAL_URL)
    he_text = gzip.decompress(he_raw).decode('utf-8')
    he_rows = [json.loads(x) for x in he_text.splitlines() if x.strip()]
    he_rows.sort(key=lambda r: rank(r['task_id']))
    he_sel = he_rows[:he_n]

    prompts = {
        'schema': SCHEMA,
        'mode': 'PROMPTS_ONLY_NO_ANSWERS',
        'selection_seed_sha256': hashlib.sha256(SEED.encode()).hexdigest(),
        'benchmarks': {
            'gsm8k': [
                {'task_id': f'gsm8k:{i:03d}', 'question': r['question'], 'source_item_sha256': hashlib.sha256(r['question'].encode()).hexdigest()}
                for i, r in enumerate(gsm_sel)
            ],
            'humaneval': [
                {'task_id': r['task_id'], 'prompt': r['prompt'], 'entry_point': r['entry_point'], 'source_item_sha256': hashlib.sha256(r['prompt'].encode()).hexdigest()}
                for r in he_sel
            ],
        },
        'claim_boundary': {
            'answers_present': False,
            'tests_present': False,
            'canonical_solutions_present': False,
            'selection_independent_of_answers': True,
        },
    }
    keys = {
        'schema': SCHEMA,
        'mode': 'SEALED_OFFICIAL_KEY',
        'prompt_digest': jd(prompts),
        'sources': {
            'gsm8k': {'url': GSM8K_URL, 'sha256': hashlib.sha256(gsm_raw).hexdigest(), 'total_items': len(gsm_rows)},
            'humaneval': {'url': HUMANEVAL_URL, 'sha256': hashlib.sha256(he_raw).hexdigest(), 'total_items': len(he_rows)},
        },
        'gsm8k': {
            f'gsm8k:{i:03d}': {'answer': parse_gsm_answer(r['answer']), 'answer_text_sha256': hashlib.sha256(r['answer'].encode()).hexdigest()}
            for i, r in enumerate(gsm_sel)
        },
        'humaneval': {
            r['task_id']: {'test': r['test'], 'entry_point': r['entry_point'], 'canonical_solution_sha256': hashlib.sha256(r['canonical_solution'].encode()).hexdigest()}
            for r in he_sel
        },
    }
    prompt_out.parent.mkdir(parents=True, exist_ok=True)
    key_out.parent.mkdir(parents=True, exist_ok=True)
    prompt_out.write_text(json.dumps(prompts, indent=2, ensure_ascii=False))
    key_out.write_text(json.dumps(keys, indent=2, ensure_ascii=False))


NUM_RE = re.compile(r'(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?')

def nums(text: str) -> list[float]:
    out=[]
    for m in NUM_RE.findall(text):
        try: out.append(float(m.replace(',', '')))
        except Exception: pass
    return out


def solve_gsm(question: str) -> tuple[float | int | None, str]:
    q = question.lower().replace('$', '')
    ns = nums(q)
    if not ns:
        return None, 'no_numbers'
    # Generic bounded arithmetic planner. It has no access to benchmark answers.
    if '%' in q or 'percent' in q:
        pcts=[x for x in ns if 0 <= x <= 100]
        if len(ns) >= 2 and pcts:
            pct=pcts[-1]
            base=next((x for x in ns if x != pct), ns[0])
            val=base*pct/100.0
            return (int(val) if val.is_integer() else val), 'percent_of'
    if any(k in q for k in ('average', 'mean')) and len(ns) >= 2:
        val=sum(ns)/len(ns)
        return (int(val) if val.is_integer() else val), 'average_all_quantities'
    if any(k in q for k in ('how many times', 'times as many')) and len(ns) >= 2 and min(abs(x) for x in ns if x != 0) > 0:
        hi=max(ns); lo=min(x for x in ns if x > 0); val=hi/lo
        return (int(val) if val.is_integer() else val), 'ratio'
    # Strong subtraction cues: inventory / remaining quantity.
    if any(k in q for k in (' left', 'remain', 'remaining', 'gave away', 'sold ', 'spent ', 'used ')) and len(ns) >= 2:
        val=ns[0]-sum(ns[1:])
        return (int(val) if val.is_integer() else val), 'inventory_subtraction'
    # Division cues when a known total is shared among groups.
    if any(k in q for k in ('equally', 'split', 'shared', 'per person', 'each person', 'each get')) and len(ns) >= 2:
        a,b=ns[-2],ns[-1]
        if b:
            val=a/b
            return (int(val) if val.is_integer() else val), 'equal_share'
    # Multiplicative cues. Prefer nearest two quantities around repeated/each language.
    if any(k in q for k in (' each ', ' per ', 'every ', 'times ')) and len(ns) >= 2:
        # If question also asks a remaining/total after an explicit unit rate, combine one product with other quantities.
        if len(ns) == 2:
            val=ns[0]*ns[1]
            return (int(val) if val.is_integer() else val), 'unit_rate_product'
        if any(k in q for k in ('altogether', 'total', 'in all')):
            val=ns[0]*ns[1] + sum(ns[2:])
            return (int(val) if float(val).is_integer() else val), 'product_plus_rest'
        val=ns[-2]*ns[-1]
        return (int(val) if val.is_integer() else val), 'nearest_unit_rate_product'
    if any(k in q for k in ('altogether', 'in all', 'total', 'combined', 'together')):
        val=sum(ns)
        return (int(val) if val.is_integer() else val), 'sum_all_quantities'
    if any(k in q for k in ('more than', 'increase', 'additional', 'extra')) and len(ns) >= 2:
        val=ns[0]+sum(ns[1:])
        return (int(val) if val.is_integer() else val), 'additive_change'
    if any(k in q for k in ('less than', 'fewer than', 'decrease')) and len(ns) >= 2:
        val=ns[0]-sum(ns[1:])
        return (int(val) if val.is_integer() else val), 'subtractive_change'
    # Conservative fallback: do not invent a confident answer for an unsupported composition.
    if len(ns) == 1:
        return (int(ns[0]) if ns[0].is_integer() else ns[0]), 'single_quantity'
    return None, 'unsupported_multistep_language'


def function_info(prompt: str):
    # HumanEval prompts are valid function prefixes. Add pass only when necessary.
    try:
        tree=ast.parse(prompt + '\n    pass\n')
    except Exception:
        return None, []
    fn=next((n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    if not fn: return None, []
    return fn.name, [a.arg for a in fn.args.args]


def synthesize_humaneval(prompt: str, entry: str) -> tuple[str | None, str]:
    low=prompt.lower(); name,args=function_info(prompt)
    if not name or name != entry or not args:
        return None, 'signature_parse_fail'
    a=args[0]; body=None; strategy='unsupported_spec'
    if 'palindrome' in low:
        body=f"return str({a}) == str({a})[::-1]"; strategy='palindrome_template'
    elif 'prime' in low and ('is prime' in low or 'prime number' in low):
        body=f"\n    if {a} < 2: return False\n    i = 2\n    while i * i <= {a}:\n        if {a} % i == 0: return False\n        i += 1\n    return True"; strategy='prime_template'
    elif 'fibonacci' in low:
        body=f"\n    x, y = 0, 1\n    for _ in range({a}): x, y = y, x + y\n    return x"; strategy='fibonacci_template'
    elif 'factorial' in low:
        body=f"\n    out = 1\n    for i in range(2, {a}+1): out *= i\n    return out"; strategy='factorial_template'
    elif ('greatest common divisor' in low or 'gcd' in low) and len(args) >= 2:
        b=args[1]; body=f"\n    x, y = abs({a}), abs({b})\n    while y: x, y = y, x % y\n    return x"; strategy='gcd_template'
    elif 'reverse' in low and ('string' in low or 'str' in low):
        body=f"return {a}[::-1]"; strategy='reverse_template'
    elif ('sorted' in low or 'sort ' in low) and ('list' in low or 'array' in low):
        body=f"return sorted({a})"; strategy='sort_template'
    elif 'sum of digits' in low or 'sum the digits' in low:
        body=f"return sum(int(c) for c in str(abs({a})))"; strategy='digit_sum_template'
    elif 'vowel' in low and ('count' in low or 'number of' in low):
        body=f"return sum(c.lower() in 'aeiou' for c in {a})"; strategy='vowel_count_template'
    elif 'average' in low or 'mean' in low:
        body=f"return sum({a}) / len({a})"; strategy='mean_template'
    elif 'maximum' in low or 'largest' in low or 'max ' in low:
        body=f"return max({a})"; strategy='max_template'
    elif 'minimum' in low or 'smallest' in low or 'min ' in low:
        body=f"return min({a})"; strategy='min_template'
    elif 'unique' in low and ('list' in low or 'elements' in low):
        body=f"return list(dict.fromkeys({a}))"; strategy='unique_template'
    elif 'even' in low and 'odd' not in low and ('return' in low or 'check' in low):
        body=f"return {a} % 2 == 0"; strategy='even_template'
    elif 'odd' in low and 'even' not in low and ('return' in low or 'check' in low):
        body=f"return {a} % 2 != 0"; strategy='odd_template'
    if body is None:
        return None, strategy
    # Append an implementation to the benchmark-provided signature/docstring prefix.
    if body.startswith('\n'):
        code=prompt.rstrip()+body+'\n'
    else:
        code=prompt.rstrip()+'\n    '+body+'\n'
    return code, strategy


def solve(prompts_path: Path, out: Path) -> None:
    prompts=json.loads(prompts_path.read_text())
    assert prompts['claim_boundary']['answers_present'] is False
    pred={'schema':SCHEMA,'mode':'BLIND_PREDICTIONS','prompt_digest':jd(prompts),'gsm8k':{},'humaneval':{},'claim_boundary':{'answer_key_accessed':False,'official_tests_accessed':False,'canonical_solutions_accessed':False}}
    for t in prompts['benchmarks']['gsm8k']:
        ans,strategy=solve_gsm(t['question']); pred['gsm8k'][t['task_id']]={'prediction':ans,'strategy':strategy}
    for t in prompts['benchmarks']['humaneval']:
        code,strategy=synthesize_humaneval(t['prompt'],t['entry_point']); pred['humaneval'][t['task_id']]={'code':code,'strategy':strategy}
    pred['prediction_digest']=jd({'gsm8k':pred['gsm8k'],'humaneval':pred['humaneval']})
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(pred,indent=2,ensure_ascii=False))


def numeq(a,b)->bool:
    if a is None or b is None:return False
    try:return abs(float(a)-float(b)) <= 1e-9*max(1.0,abs(float(b)))
    except Exception:return False


def run_humaneval(code: str | None, test: str, entry: str) -> tuple[bool,str]:
    if not code:return False,'UNSOLVED'
    harness=code+'\n'+test+f'\ncheck({entry})\n'
    try:
        cp=subprocess.run([sys.executable,'-I','-c',harness],capture_output=True,text=True,timeout=3)
        return cp.returncode==0, ('PASS' if cp.returncode==0 else (cp.stderr[-300:] or 'FAIL'))
    except subprocess.TimeoutExpired:return False,'TIMEOUT'
    except Exception as e:return False,type(e).__name__


def score(prompts_path:Path,pred_path:Path,key_path:Path,out:Path)->None:
    prompts=json.loads(prompts_path.read_text()); pred=json.loads(pred_path.read_text()); key=json.loads(key_path.read_text())
    assert key['prompt_digest']==jd(prompts)==pred['prompt_digest']
    assert pred['claim_boundary']['answer_key_accessed'] is False
    gsm=[]
    for t in prompts['benchmarks']['gsm8k']:
        tid=t['task_id']; p=pred['gsm8k'][tid]['prediction']; truth=key['gsm8k'][tid]['answer']; gsm.append({'task_id':tid,'correct':numeq(p,truth),'prediction':p,'official_answer':truth,'strategy':pred['gsm8k'][tid]['strategy']})
    he=[]
    for t in prompts['benchmarks']['humaneval']:
        tid=t['task_id']; ok,status=run_humaneval(pred['humaneval'][tid]['code'],key['humaneval'][tid]['test'],key['humaneval'][tid]['entry_point']); he.append({'task_id':tid,'correct':ok,'status':status,'strategy':pred['humaneval'][tid]['strategy']})
    gc=sum(x['correct'] for x in gsm); hc=sum(x['correct'] for x in he)
    report={'schema':SCHEMA,'status':'COMPLETED_BLIND_REAL_BENCHMARK_V1','protocol':{'solver_received_answer_key':False,'solver_received_official_tests':False,'predictions_frozen_before_scoring':True,'prompt_digest':jd(prompts),'prediction_digest':pred['prediction_digest']},'results':{'gsm8k':{'correct':gc,'total':len(gsm),'accuracy':round(gc/len(gsm),6) if gsm else 0,'items':gsm},'humaneval':{'correct':hc,'total':len(he),'pass_at_1':round(hc/len(he),6) if he else 0,'items':he},'combined':{'correct':gc+hc,'total':len(gsm)+len(he),'accuracy':round((gc+hc)/(len(gsm)+len(he)),6)}},'claim_boundary':{'general_intelligence_proven':False,'benchmark_training_performed':False,'failures_are_retained_as_evidence':True}}
    report['evidence_digest']=jd(report);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,ensure_ascii=False))


def main():
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True)
    p=sp.add_parser('prepare');p.add_argument('--prompts',required=True);p.add_argument('--key',required=True);p.add_argument('--gsm-n',type=int,default=80);p.add_argument('--he-n',type=int,default=24)
    s=sp.add_parser('solve');s.add_argument('--prompts',required=True);s.add_argument('--out',required=True)
    c=sp.add_parser('score');c.add_argument('--prompts',required=True);c.add_argument('--predictions',required=True);c.add_argument('--key',required=True);c.add_argument('--out',required=True)
    a=ap.parse_args()
    if a.cmd=='prepare':prepare(Path(a.prompts),Path(a.key),a.gsm_n,a.he_n)
    elif a.cmd=='solve':solve(Path(a.prompts),Path(a.out))
    else:score(Path(a.prompts),Path(a.predictions),Path(a.key),Path(a.out))
if __name__=='__main__':main()
