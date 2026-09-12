#!/usr/bin/env python3
from __future__ import annotations

import argparse, gzip, hashlib, io, json, math, re, zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple
import yado_blind_real_benchmark_exam_v1 as blind

SCHEMA="yado.staged_kernel_evolution.v1"
STAGES=["CODE","LOGIC","THINKING","INTELLIGENCE","COGNITION","REASON"]
SEEDS={s:f"20260912-evolution-{s.lower()}-v1" for s in STAGES}
MUT={
 "CODE":"SAFE_SOURCE_ANNOTATION_PRELUDE_V1",
 "LOGIC":"WEIGHTED_EVIDENCE_RELATION_RETRIEVAL_V1",
 "THINKING":"MULTISTEP_QUANTITY_PROGRAM_V1",
 "INTELLIGENCE":"MULTI_STRATEGY_ARBITRATION_V1",
 "COGNITION":"FAILURE_MEMORY_CONFIDENCE_CALIBRATION_V1",
 "REASON":"CROSS_DOMAIN_REFLECTIVE_ARBITRATION_V1",
}
COUNTS={"gsm8k":20,"openbookqa":20,"humaneval":10}
PRIOR=[("20260912-real-blind-v1",40,40,20),("20260912-real-blind-v1b",40,40,20)]

def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def digest(x): return hashlib.sha256(canon(x).encode()).hexdigest()
def rank(rows,seed,key): return sorted(rows,key=lambda r:hashlib.sha256((seed+"|"+str(r[key])).encode()).hexdigest())
def take_ids(rows,n,seed,key): return {str(r[key]) for r in rank(rows,seed,key)[:n]}
def choose(rows,n,seed,key,blocked):
    out=[r for r in rank(rows,seed,key) if str(r[key]) not in blocked][:n]
    if len(out)!=n: raise RuntimeError("insufficient disjoint benchmark rows")
    return out

def prepare(stage:str,out:Path)->Dict[str,Any]:
    out.mkdir(parents=True,exist_ok=True); seed=SEEDS[stage]
    rg=blind.fetch(blind.GSM8K_URL); g0=[json.loads(x) for x in rg.decode().splitlines() if x.strip()]
    gsm=[{"id":f"gsm8k-{i:04d}",**r} for i,r in enumerate(g0)]
    rh=blind.fetch(blind.HUMANEVAL_URL); he=[json.loads(x) for x in gzip.decompress(rh).decode().splitlines() if x.strip()]
    ro=blind.fetch(blind.OPENBOOKQA_URL); z=zipfile.ZipFile(io.BytesIO(ro)); names=z.namelist()
    tn=next(n for n in names if n.endswith("/Data/Main/test.jsonl")); fn=next(n for n in names if n.endswith("/Data/Main/openbook.txt"))
    ob=[json.loads(x) for x in z.read(tn).decode().splitlines() if x.strip()]; facts=z.read(fn).decode("utf-8","replace")
    ex={"gsm8k":set(),"openbookqa":set(),"humaneval":set()}
    for sd,ng,no,nh in PRIOR:
        ex["gsm8k"]|=take_ids(gsm,ng,sd+"-gsm","id"); ex["openbookqa"]|=take_ids(ob,no,sd+"-obqa","id"); ex["humaneval"]|=take_ids(he,nh,sd+"-he","task_id")
    for ps in STAGES[:STAGES.index(stage)]:
        sd=SEEDS[ps]
        pg=choose(gsm,COUNTS["gsm8k"],sd+"-gsm","id",ex["gsm8k"]); po=choose(ob,COUNTS["openbookqa"],sd+"-obqa","id",ex["openbookqa"]); ph=choose(he,COUNTS["humaneval"],sd+"-he","task_id",ex["humaneval"])
        ex["gsm8k"].update(str(r["id"]) for r in pg); ex["openbookqa"].update(str(r["id"]) for r in po); ex["humaneval"].update(str(r["task_id"]) for r in ph)
    sg=choose(gsm,COUNTS["gsm8k"],seed+"-gsm","id",ex["gsm8k"]); so=choose(ob,COUNTS["openbookqa"],seed+"-obqa","id",ex["openbookqa"]); sh=choose(he,COUNTS["humaneval"],seed+"-he","task_id",ex["humaneval"])
    ch=[]; gt=[]
    for r in sg:
        ch.append({"exam_id":r["id"],"benchmark":"gsm8k","prompt":r["question"]}); gt.append({"exam_id":r["id"],"benchmark":"gsm8k","expected":blind.extract_gsm8k_final(r["answer"])})
    for r in so:
        q=r["question"]; choices=[{"label":c["label"],"text":c["text"]} for c in q["choices"]]
        ch.append({"exam_id":r["id"],"benchmark":"openbookqa","prompt":q["stem"],"choices":choices}); gt.append({"exam_id":r["id"],"benchmark":"openbookqa","expected":r["answerKey"]})
    for r in sh:
        ch.append({"exam_id":r["task_id"],"benchmark":"humaneval","prompt":r["prompt"],"entry_point":r["entry_point"]}); gt.append({"exam_id":r["task_id"],"benchmark":"humaneval","entry_point":r["entry_point"],"test":r["test"]})
    ch=sorted(ch,key=lambda x:hashlib.sha256((seed+"|mix|"+x["exam_id"]).encode()).hexdigest()); gt=sorted(gt,key=lambda x:x["exam_id"])
    blind.write_jsonl(out/"challenges.jsonl",ch); blind.write_jsonl(out/"sealed_ground_truth.jsonl",gt); (out/"openbook_facts.txt").write_text(facts)
    ids={b:sorted(x["exam_id"] for x in ch if x["benchmark"]==b) for b in COUNTS}; overlap={b:len(set(ids[b])&ex[b]) for b in COUNTS}; assert not any(overlap.values())
    m={"schema":SCHEMA,"stage":stage,"seed":seed,"counts":dict(Counter(x["benchmark"] for x in ch)),"challenge_digest":blind.digest(ch),"sealed_ground_truth_digest":blind.digest(gt),"overlap_with_prior_exams_or_stages":overlap,"selected_ids_digest":digest(ids),"separation_contract":{"respond_receives_ground_truth":False,"parent_and_child_fixed_before_truth":True,"current_answers_used_for_mutation_selection":False}}
    (out/"prepare_manifest.json").write_text(json.dumps(m,indent=2,sort_keys=True)); return m

def initial_policy():
    return {"schema":SCHEMA,"generation":0,"enabled_mutations":[],"lineage":["CANONICAL_BLIND_SOLVER_V1"],"history":[],"prior_evidence":{"run":"34694330990","overall":{"correct":8,"total":100},"gsm8k":{"correct":0,"total":40,"unresolved":40},"humaneval":{"correct":1,"total":20,"unresolved":15},"openbookqa":{"correct":7,"total":40,"unresolved":19},"code_failure":"annotation/runtime hygiene plus unsupported semantic families"},"canonical_direct_write":False}

def child_policy(stage,parent):
    c=json.loads(json.dumps(parent)); mu=MUT[stage]
    if mu not in c["enabled_mutations"]: c["enabled_mutations"].append(mu)
    basis=c.get("history",[])[-1] if c.get("history") else c.get("prior_evidence",{})
    c["generation"]=int(parent.get("generation",0))+1; c["lineage"]=list(parent.get("lineage",[]))+[mu]
    c["pending_mutation"]={"stage":stage,"mutation":mu,"selection_basis_digest":digest(basis),"selection_mode":"EVIDENCE_CONDITIONED_BOUNDED_MUTATION_GRAMMAR","external_llm_used":False,"current_stage_ground_truth_used":False}; return c

def clean_source(src): return src if src=="UNRESOLVED" or src.startswith("from __future__ import annotations") else "from __future__ import annotations\n"+src

def fact_index(facts):
    ts=[set(blind.tokens(f)) for f in facts]; df=Counter(); [df.update(s) for s in ts]; n=max(1,len(facts)); return ts,{t:math.log((n+1)/(c+1))+1 for t,c in df.items()}

def weighted_ob(prompt,choices,idx):
    ts,idf=idx; q=set(blind.tokens(prompt)); scores=[]
    for c in choices:
        ct=set(blind.tokens(c["text"])); best=0.0
        for ft in ts:
            qo=q&ft; co=ct&ft
            if qo or co: best=max(best,.65*sum(idf.get(t,1) for t in qo)+1.75*sum(idf.get(t,1) for t in co)+.12*sum(idf.get(t,1) for t in ((q|ct)&ft)))
        scores.append((best,c["label"]))
    scores.sort(key=lambda x:(-x[0],x[1]))
    if not scores or scores[0][0]<=0: return "UNRESOLVED",{"method":"weighted_evidence_retrieval","confidence":0.0}
    margin=scores[0][0]-(scores[1][0] if len(scores)>1 else 0); conf=margin/max(scores[0][0],1e-9)
    if margin<=0:return "UNRESOLVED",{"method":"weighted_evidence_retrieval","confidence":0.0,"reason":"tie"}
    return scores[0][1],{"method":"weighted_evidence_retrieval","confidence":round(conf,4)}

def quantity_program(q):
    t=" "+re.sub(r"\s+"," ",q.lower())+" "; nums=[blind.parse_num(x) for x in blind.NUM_RE.findall(t)]
    if not nums:return "UNRESOLVED",{"method":"multistep_quantity_program","reason":"no_numbers"}
    if " twice " in t and nums and any(k in t for k in ("how many","total","altogether")):return blind.normalize_number(nums[0]*2),{"method":"multistep_quantity_program","program":"x*2"}
    if " half " in t and nums and any(k in t for k in ("how many","left","remain")):return blind.normalize_number(nums[0]/2),{"method":"multistep_quantity_program","program":"x/2"}
    if any(k in t for k in ("left","remaining","remain")) and 2<=len(nums)<=5:return blind.normalize_number(nums[0]-sum(nums[1:])),{"method":"multistep_quantity_program","program":"start-sum(outflows)"}
    if any(k in t for k in ("each","per ","apiece")) and 2<=len(nums)<=4 and any(k in t for k in ("total","altogether","in all","cost","how many")):
        v=nums[0]*nums[1]; v=v+nums[2] if len(nums)==3 and any(k in t for k in ("plus","more","additional","extra")) else v; return blind.normalize_number(v),{"method":"multistep_quantity_program","program":"count*rate(+delta)"}
    if any(k in t for k in ("altogether","in all","combined","total")) and 2<=len(nums)<=4 and not any(k in t for k in ("each","per ","times")):return blind.normalize_number(sum(nums)),{"method":"multistep_quantity_program","program":"sum"}
    if " more than " in t and len(nums)==2:return blind.normalize_number(sum(nums)),{"method":"multistep_quantity_program","program":"base+delta"}
    if " less than " in t and len(nums)==2:return blind.normalize_number(abs(nums[0]-nums[1])),{"method":"multistep_quantity_program","program":"abs_difference"}
    return "UNRESOLVED",{"method":"multistep_quantity_program","reason":"no_reliable_program","number_count":len(nums)}

def extended_he(prompt,entry):
    sig=blind.function_signature(prompt)
    if not sig:return "UNRESOLVED",{"method":"generic_semantic_code_fallback","reason":"signature_missing"}
    p=prompt.lower(); atext=sig[sig.find("(")+1:sig.rfind(")")]; args=[x.strip().split(":")[0].split("=")[0].strip() for x in atext.split(",") if x.strip() and not x.strip().startswith("*")]; body=family=None
    if len(args)>=2 and ("absolute difference" in p or "absolute value of the difference" in p):body,family=f"return abs({args[0]} - {args[1]})","absolute_difference"
    elif len(args)>=2 and re.search(r"\b(add|sum)\b",p) and "list" not in p and "array" not in p:body,family=f"return {args[0]} + {args[1]}","binary_addition"
    elif args and "reverse" in p and any(k in p for k in ("string","list")):body,family=f"return {args[0]}[::-1]","reverse_sequence"
    elif args and "maximum" in p and any(k in p for k in ("list","numbers","array")):body,family=f"return max({args[0]})","max_sequence"
    elif args and "minimum" in p and any(k in p for k in ("list","numbers","array")):body,family=f"return min({args[0]})","min_sequence"
    elif args and "sum" in p and any(k in p for k in ("list","numbers","array")) and "product" not in p:body,family=f"return sum({args[0]})","sum_sequence"
    if body is None:return "UNRESOLVED",{"method":"generic_semantic_code_fallback","reason":"no_supported_semantics"}
    src="from __future__ import annotations\n"+sig+"\n    "+body+"\n"
    try:compile(src,"<evolved>","exec")
    except Exception as e:return "UNRESOLVED",{"method":"generic_semantic_code_fallback","reason":type(e).__name__}
    return src,{"method":"generic_semantic_code_fallback","family":family}

def solve(item,facts,idx,policy):
    en=set(policy.get("enabled_mutations",[])); b=item["benchmark"]
    if b=="gsm8k":
        base,bt=blind.gsm8k_answer(item["prompt"])
        if MUT["THINKING"] in en:
            alt,at=quantity_program(item["prompt"])
            if MUT["INTELLIGENCE"] in en:
                if base!="UNRESOLVED" and alt!="UNRESOLVED" and base!=alt:
                    return ("UNRESOLVED",{"method":"reflective_arbitration","reason":"strategy_disagreement"}) if MUT["REASON"] in en else (base,{"method":"strategy_arbitration","selected":"canonical"})
                if alt!="UNRESOLVED":return alt,{"method":"strategy_arbitration","selected":"quantity_program","trace":at}
            if base=="UNRESOLVED" and alt!="UNRESOLVED":return alt,at
        return base,bt
    if b=="openbookqa":
        base,bt=blind.openbook_answer(item["prompt"],item["choices"],facts)
        if MUT["LOGIC"] not in en:return base,bt
        alt,at=weighted_ob(item["prompt"],item["choices"],idx); chosen,trace=alt,at
        if MUT["INTELLIGENCE"] in en:
            if base==alt and base!="UNRESOLVED":chosen,trace=base,{"method":"strategy_consensus","confidence":max(bt.get("confidence",0),at.get("confidence",0))}
            elif base=="UNRESOLVED":chosen,trace=alt,at
            elif alt=="UNRESOLVED":chosen,trace=base,bt
            elif base!=alt:
                if MUT["REASON"] in en:chosen,trace="UNRESOLVED",{"method":"reflective_arbitration","reason":"retrieval_disagreement","confidence":0.0}
                else:chosen,trace=(alt,at) if at.get("confidence",0)>=bt.get("confidence",0) else (base,bt)
        if MUT["COGNITION"] in en and chosen!="UNRESOLVED" and trace.get("confidence",1.0)<.06:return "UNRESOLVED",{"method":"failure_memory_calibration","reason":"low_confidence"}
        return chosen,trace
    if b=="humaneval":
        base,bt=blind.humaneval_source(item["prompt"],item["entry_point"])
        if MUT["CODE"] in en and base!="UNRESOLVED":base,bt=clean_source(base),{"method":"source_hygiene","parent_trace":bt}
        if MUT["INTELLIGENCE"] in en and base=="UNRESOLVED":
            alt,at=extended_he(item["prompt"],item["entry_point"])
            if alt!="UNRESOLVED":return alt,{"method":"strategy_arbitration","selected":"generic_semantic_code_fallback","trace":at}
        return base,bt
    return "UNRESOLVED",{"reason":"unknown_benchmark"}

def make_response(ch,facts,policy):
    idx=fact_index(facts); rs=[]
    for i in ch:
        a,t=solve(i,facts,idx,policy); rs.append({"exam_id":i["exam_id"],"benchmark":i["benchmark"],"answer":a,"trace":t})
    p={"schema":blind.SCHEMA,"mode":"respond","challenge_digest":blind.digest(ch),"response_count":len(rs),"responses":rs,"ground_truth_accessed":False,"external_llm_used":False,"canonical_direct_write":False,"evolution_policy_digest":digest(policy)}; p["response_digest"]=blind.digest(p); return p

def respond(stage,chp,fp,out,polp=None):
    out.mkdir(parents=True,exist_ok=True); ch=blind.read_jsonl(chp); facts=[x.strip() for x in fp.read_text().splitlines() if x.strip()]; parent=json.loads(polp.read_text()) if polp and polp.exists() else initial_policy(); child=child_policy(stage,parent); pr=make_response(ch,facts,parent); cr=make_response(ch,facts,child)
    (out/"parent_responses.json").write_text(json.dumps(pr,indent=2,sort_keys=True)); (out/"child_responses.json").write_text(json.dumps(cr,indent=2,sort_keys=True)); r={"schema":SCHEMA,"stage":stage,"parent_policy":parent,"child_policy":child,"parent_response_digest":pr["response_digest"],"child_response_digest":cr["response_digest"],"ground_truth_accessed":False,"external_llm_used":False,"canonical_direct_write":False}; r["receipt_digest"]=digest(r); (out/"mutation_receipt.json").write_text(json.dumps(r,indent=2,sort_keys=True)); return r

def wrong(v):return int(v["overall"]["total"])-int(v["overall"]["correct"])-sum(int(x.get("unresolved",0)) for x in v["per_benchmark"].values())
def verify(stage,ch,gt,rd,out):
    out.mkdir(parents=True,exist_ok=True); pv=blind.verify(ch,gt,rd/"parent_responses.json",out/"parent_verification.json"); cv=blind.verify(ch,gt,rd/"child_responses.json",out/"child_verification.json"); rec=json.loads((rd/"mutation_receipt.json").read_text()); parent=rec["parent_policy"]; child=rec["child_policy"]; target={"CODE":"humaneval","LOGIC":"openbookqa","THINKING":"gsm8k"}.get(stage); noreg=all(cv["per_benchmark"][b]["correct"]>=pv["per_benchmark"][b]["correct"] for b in pv["per_benchmark"])
    if target:better=cv["per_benchmark"][target]["correct"]>pv["per_benchmark"][target]["correct"] and noreg
    else:better=(cv["overall"]["correct"]>pv["overall"]["correct"] and noreg) or (cv["overall"]["correct"]==pv["overall"]["correct"] and noreg and wrong(cv)<wrong(pv))
    dec="PROMOTE_SHADOW" if better else "WITHHOLD"; sel=json.loads(json.dumps(child if better else parent)); sel.pop("pending_mutation",None); vs={"stage":stage,"mutation":MUT[stage],"decision":dec,"parent":{"overall":pv["overall"],"per_benchmark":pv["per_benchmark"],"wrong":wrong(pv)},"child":{"overall":cv["overall"],"per_benchmark":cv["per_benchmark"],"wrong":wrong(cv)},"no_per_benchmark_correct_regression":noreg,"ground_truth_revealed_only_after_response_fixation":True}; sel.setdefault("history",[]).append(vs); sel["last_decision"]=dec; sel["last_stage"]=stage; sel["canonical_direct_write"]=False; (out/"policy_out.json").write_text(json.dumps(sel,indent=2,sort_keys=True)); res={"schema":SCHEMA,"status":"PASS_MEASURED_STAGED_EVOLUTION_STAGE_V1","stage":stage,"decision":dec,"verdict":vs,"selected_policy_digest":digest(sel),"claim_boundary":{"stage_improvement_proven":better,"stable_reason_proven":False,"phenomenal_consciousness_proven":False}}; res["evidence_digest"]=digest(res); (out/"stage_verdict.json").write_text(json.dumps(res,indent=2,sort_keys=True)); return res

def finalize(policy,verdicts,out):
    p=json.loads(policy.read_text()); vs=[json.loads(x.read_text()) for x in verdicts]; r={"schema":SCHEMA,"status":"PASS_STAGED_EVOLUTION_CYCLE_MEASURED_V1","stages_attempted":[v["stage"] for v in vs],"stages_promoted_shadow":[v["stage"] for v in vs if v["decision"]=="PROMOTE_SHADOW"],"final_generation":p.get("generation",0),"final_enabled_mutations":p.get("enabled_mutations",[]),"policy_digest":digest(p),"canonical_direct_write":False,"next_gate":"FULL_KERNEL_AUDIT_AND_EXPLICIT_CANONICAL_ADMISSION_OF_MECHANISM_ONLY","claim_boundary":{"single_cycle_completed":True,"stable_autonomous_reason_proven":False,"phenomenal_consciousness_proven":False,"requires_repeated_independent_cycles":True},"verdicts":vs}; r["evidence_digest"]=digest(r); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(r,indent=2,sort_keys=True)); return r

def self_test():
    p=initial_policy()
    for s in STAGES:p=child_policy(s,p); assert MUT[s] in p["enabled_mutations"]
    assert clean_source("def f(x: List[int]):\n    return len(x)\n").startswith("from __future__ import annotations")
    a,_=quantity_program("A box has 20 balls. 5 are removed. How many are left?"); assert a=="15"; print("PASS_STAGED_KERNEL_EVOLUTION_SELF_TEST_V1")

def main():
    ap=argparse.ArgumentParser(); sp=ap.add_subparsers(dest="cmd",required=True); sp.add_parser("self-test")
    p=sp.add_parser("prepare"); p.add_argument("--stage",choices=STAGES,required=True); p.add_argument("--out-dir",type=Path,required=True)
    p=sp.add_parser("respond"); p.add_argument("--stage",choices=STAGES,required=True); p.add_argument("--challenges",type=Path,required=True); p.add_argument("--facts",type=Path,required=True); p.add_argument("--out-dir",type=Path,required=True); p.add_argument("--policy-in",type=Path)
    p=sp.add_parser("verify"); p.add_argument("--stage",choices=STAGES,required=True); p.add_argument("--challenges",type=Path,required=True); p.add_argument("--sealed",type=Path,required=True); p.add_argument("--response-dir",type=Path,required=True); p.add_argument("--out-dir",type=Path,required=True)
    p=sp.add_parser("finalize"); p.add_argument("--policy",type=Path,required=True); p.add_argument("--verdict",type=Path,action="append",required=True); p.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    if a.cmd=="self-test":self_test()
    elif a.cmd=="prepare":print(json.dumps(prepare(a.stage,a.out_dir),indent=2))
    elif a.cmd=="respond":print(json.dumps(respond(a.stage,a.challenges,a.facts,a.out_dir,a.policy_in),indent=2))
    elif a.cmd=="verify":print(json.dumps(verify(a.stage,a.challenges,a.sealed,a.response_dir,a.out_dir),indent=2))
    else:print(json.dumps(finalize(a.policy,a.verdict,a.out),indent=2))
if __name__=="__main__":main()
