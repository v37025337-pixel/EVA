#!/usr/bin/env python3
"""Evidence-gated adaptive repair of YADO's THINKING_BOUNDARY_REASONING deficit."""
from __future__ import annotations
import argparse, hashlib, json, random, re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

SCHEMA = "yado.thinking_boundary_adaptive_repair.v1"
TARGET_DEFICIT = "THINKING_BOUNDARY_REASONING"
PRIMITIVES = ("forward_chain", "contradiction_guard", "representation_normalization")
DOMAIN_NAMES = ("programming","cybersecurity","medicine_biology","physics_astronomy","mathematics","philosophy_cognition","climate_systems","web_systems")
FAMILY_TO_PRIMITIVE = {"multi_hop":"forward_chain","contradiction":"contradiction_guard","representation":"representation_normalization"}
CRITICAL_FAMILIES = ("multi_hop","contradiction","representation")

@dataclass(frozen=True)
class Task:
    task_id: str
    family: str
    domain: str
    positive_edges: Tuple[Tuple[str,str], ...]
    negative_edges: Tuple[Tuple[str,str], ...]
    aliases: Tuple[Tuple[str,str], ...]
    query: Tuple[str,str]
    expected: str

def stable_digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode()).hexdigest()

def normalize_surface(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())

def alias_map(task: Task) -> Dict[str,str]:
    out = {}
    for surface, canonical in task.aliases:
        out[normalize_surface(surface)] = canonical
        out[normalize_surface(canonical)] = canonical
    return out

def canonicalize(value: str, task: Task, enabled: bool) -> str:
    if not enabled:
        return value
    amap = alias_map(task)
    return amap.get(normalize_surface(value), normalize_surface(value))

def canon_edges(edges: Iterable[Tuple[str,str]], task: Task, enabled: bool) -> Set[Tuple[str,str]]:
    return {(canonicalize(a,task,enabled), canonicalize(b,task,enabled)) for a,b in edges}

def reachable(edges: Set[Tuple[str,str]], src: str, dst: str, multi_hop: bool) -> bool:
    if (src,dst) in edges:
        return True
    if not multi_hop:
        return False
    graph = defaultdict(set)
    for a,b in edges: graph[a].add(b)
    seen, frontier = {src}, [src]
    while frontier:
        current = frontier.pop(0)
        for nxt in sorted(graph.get(current,())):
            if nxt == dst: return True
            if nxt not in seen:
                seen.add(nxt); frontier.append(nxt)
    return False

def oracle_label(task: Task) -> str:
    pos, neg = canon_edges(task.positive_edges,task,True), canon_edges(task.negative_edges,task,True)
    src, dst = canonicalize(task.query[0],task,True), canonicalize(task.query[1],task,True)
    support, counter = reachable(pos,src,dst,True), (src,dst) in neg
    if support and counter: return "CONFLICT"
    if counter: return "CONTRADICTED"
    if support: return "SUPPORTED"
    return "UNSUPPORTED"

def candidate_label(task: Task, features: Set[str]) -> str:
    norm = "representation_normalization" in features
    pos, neg = canon_edges(task.positive_edges,task,norm), canon_edges(task.negative_edges,task,norm)
    src, dst = canonicalize(task.query[0],task,norm), canonicalize(task.query[1],task,norm)
    support = reachable(pos,src,dst,"forward_chain" in features)
    if "contradiction_guard" in features:
        counter = (src,dst) in neg
        if support and counter: return "CONFLICT"
        if counter: return "CONTRADICTED"
    return "SUPPORTED" if support else "UNSUPPORTED"

def vname(base: str, variant: int) -> str:
    options = (base, base.upper(), base.replace("_","-"), base.replace("_"," "), f"{base}.", f"[{base}]")
    return options[variant % len(options)]

def build_task(rng: random.Random, suite: str, idx: int, family: str, domain: str) -> Task:
    root=f"{domain}_{suite}_{idx}"; nodes=[f"{root}_n{i}" for i in range(6)]
    pos=[]; neg=[]; aliases=[]
    if family == "direct": pos=[(nodes[0],nodes[1])]; query=(nodes[0],nodes[1])
    elif family == "negative": pos=[(nodes[0],nodes[1]),(nodes[2],nodes[3])]; query=(nodes[0],nodes[3])
    elif family == "multi_hop":
        hops=2+rng.randrange(3); pos=[(nodes[i],nodes[i+1]) for i in range(hops)]; query=(nodes[0],nodes[hops])
    elif family == "contradiction":
        hops=2+rng.randrange(2); pos=[(nodes[i],nodes[i+1]) for i in range(hops)]; neg=[(nodes[0],nodes[hops])]; query=(nodes[0],nodes[hops])
    elif family == "representation":
        sa,sb,sc=vname(nodes[0],idx+1),vname(nodes[1],idx+2),vname(nodes[2],idx+3)
        aliases=[(sa,nodes[0]),(sb,nodes[1]),(sc,nodes[2])]; pos=[(sa,sb),(sb,sc)]; query=(nodes[0],nodes[2])
    else: raise ValueError(family)
    t=Task(f"{suite}-{idx:03d}",family,domain,tuple(pos),tuple(neg),tuple(aliases),query,"")
    return Task(**{**t.__dict__,"expected":oracle_label(t)})

def generate_suite(seed: int, suite: str, per_family: int=18) -> List[Task]:
    rng=random.Random(seed); tasks=[]; idx=0
    for family in ("direct","negative","multi_hop","contradiction","representation"):
        for _ in range(per_family):
            domain=DOMAIN_NAMES[rng.randrange(len(DOMAIN_NAMES))]; t=build_task(rng,suite,idx,family,domain)
            assert t.expected == oracle_label(t); tasks.append(t); idx += 1
    rng.shuffle(tasks); return tasks

def evaluate(tasks: Sequence[Task], features: Set[str]) -> Dict[str,Any]:
    by=defaultdict(list); failures=[]; correct=0
    for t in tasks:
        pred=candidate_label(t,features); ok=pred==t.expected; correct += int(ok); by[t.family].append(int(ok))
        if not ok: failures.append({"task_id":t.task_id,"family":t.family,"domain":t.domain,"expected":t.expected,"predicted":pred})
    fam={k:round(sum(v)/len(v),6) for k,v in sorted(by.items())}
    return {"score":round(correct/len(tasks),6),"correct":correct,"total":len(tasks),"family_accuracy":fam,"failure_count":len(failures),"failure_examples":failures[:12]}

def adaptive_development(tasks: Sequence[Task]) -> Dict[str,Any]:
    features=set(); current=evaluate(tasks,features)
    history=[{"iteration":0,"features":[],"score":current["score"],"family_accuracy":current["family_accuracy"],"decision":"BASELINE_MEASURED"}]
    for i in range(1,len(PRIMITIVES)+1):
        failing=sorted((float(acc), fam) for fam,acc in current["family_accuracy"].items() if float(acc)<.999999)
        trials=[]
        for primitive in PRIMITIVES:
            if primitive in features: continue
            proposed=set(features); proposed.add(primitive); metrics=evaluate(tasks,proposed)
            regressed=[fam for fam,old in current["family_accuracy"].items() if float(metrics["family_accuracy"].get(fam,0))+1e-12 < float(old)]
            gain=round(float(metrics["score"])-float(current["score"]),6)
            trials.append((gain, -len(regressed), primitive, proposed, metrics, regressed))
        if not trials: break
        trials.sort(key=lambda x:(-x[0], -x[1], x[2]))
        gain, _, primitive, proposed, trial, regressed = trials[0]
        accepted=gain>0 and not regressed
        history.append({"iteration":i,"error_profile_before":current["family_accuracy"],"worst_failing_family":failing[0][1] if failing else None,"primitive_trials":[{"primitive":t[2],"score":t[4]["score"],"gain":t[0],"regressed_families":t[5]} for t in trials],"selected_primitive":primitive,"proposal_features":sorted(proposed),"score_before":current["score"],"score_after":trial["score"],"family_accuracy_after":trial["family_accuracy"],"regressed_families":regressed,"decision":"ACCEPT" if accepted else "REJECT"})
        if not accepted: break
        features,current=proposed,trial
    return {"selected_features":sorted(features),"selected_policy_digest":stable_digest(sorted(features)),"development_metrics":current,"adaptation_history":history}

def load_json(path: Path) -> Dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))

def validate_inputs(sm: Dict[str,Any], exp: Dict[str,Any]) -> Dict[str,Any]:
    deficits={d.get("deficit_id"):d for d in sm.get("generation_deficits",[]) if isinstance(d,dict) and d.get("deficit_id")}
    target=deficits.get(TARGET_DEFICIT); acquisition=exp.get("acquisition",{}); status=str(exp.get("status",""))
    return {"self_model_status":sm.get("status"),"target_deficit":target,"target_present":target is not None,"experience_status":status,"experience_digest":exp.get("evidence_digest"),"experience_pass":status.startswith("PASS_"),"discipline_count":int(acquisition.get("discipline_count",0) or 0),"cross_domain_edge_count":len(exp.get("derived_experience",{}).get("cross_domain",{}).get("edges",[]))}

def run(sm: Dict[str,Any], exp: Dict[str,Any], dev_seed: int, ood_seed: int) -> Dict[str,Any]:
    binding=validate_inputs(sm,exp); dev=generate_suite(dev_seed,"development"); ood=generate_suite(ood_seed,"fresh_ood")
    adaptation=adaptive_development(dev); base=evaluate(ood,set()); features=set(adaptation["selected_features"]); cand=evaluate(ood,features); delta=round(cand["score"]-base["score"],6)
    no_reg=all(float(cand["family_accuracy"].get(f,0))+1e-12 >= float(base["family_accuracy"].get(f,0)) for f in CRITICAL_FAMILIES)
    floor=all(float(cand["family_accuracy"].get(f,0)) >= .80 for f in CRITICAL_FAMILIES)
    input_gate=binding["target_present"] and binding["experience_pass"] and binding["discipline_count"]>=5 and binding["cross_domain_edge_count"]>0
    bench_gate=cand["score"]>=.85 and delta>=.20 and no_reg and floor; admitted=input_gate and bench_gate
    result={"schema":SCHEMA,"status":"PASS_SHADOW_THINKING_BOUNDARY_ADAPTIVE_REPAIR_V1" if admitted else "WITHHOLD_THINKING_BOUNDARY_ADAPTIVE_REPAIR_V1","binding":binding,"candidate":{"target_deficit":TARGET_DEFICIT,"features":sorted(features),"policy_digest":adaptation["selected_policy_digest"],"canonical_direct_write":False,"admission_route":["shadow_adaptation","fresh_ood_transfer","full_kernel_audit","complete_regression","explicit_main_admission"]},"development":{"seed":dev_seed,"suite_digest":stable_digest([t.__dict__ for t in dev]),"task_count":len(dev),"adaptation_history":adaptation["adaptation_history"],"final_metrics":adaptation["development_metrics"]},"fresh_ood":{"seed":ood_seed,"suite_digest":stable_digest([t.__dict__ for t in ood]),"task_count":len(ood),"baseline":base,"candidate":cand,"absolute_gain":delta,"no_critical_regression":no_reg,"critical_family_floor_pass":floor},"gates":{"input_gate":input_gate,"benchmark_gate":bench_gate,"required_candidate_score":.85,"required_absolute_gain":.20,"required_critical_family_floor":.80},"claims":{"measured_benchmark_improvement":admitted,"general_intelligence_improvement_claimed":False,"phenomenal_consciousness_claimed":False,"interpretation":"Fresh/OOD improvement is evidence for this bounded boundary-reasoning benchmark only; it is not proof of general intelligence or subjective consciousness."},"safety_boundary":{"canonical_direct_write":False,"remote_content_executed":False,"bounded_primitive_library":list(PRIMITIVES)}}
    result["evidence_digest"]=stable_digest(result); return result

def self_test() -> None:
    dev=generate_suite(1234,"dev_test",4); ood=generate_suite(5678,"ood_test",4); adaptive=adaptive_development(dev)
    assert adaptive["selected_features"] == sorted(PRIMITIVES), adaptive["selected_features"]
    b=evaluate(ood,set()); c=evaluate(ood,set(adaptive["selected_features"])); assert c["score"] > b["score"] and c["score"] == 1.0 and b["score"] < .8
    print("PASS_THINKING_BOUNDARY_ADAPTIVE_REPAIR_SELF_TEST")

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--self-model",default="architecture/developmental-self-model-overlay.json"); p.add_argument("--experience"); p.add_argument("--out",default="artifacts/yado-thinking-boundary-adaptive-repair-v1.json"); p.add_argument("--dev-seed",type=int,default=20260912); p.add_argument("--ood-seed",type=int,default=20260913); p.add_argument("--self-test",action="store_true"); a=p.parse_args()
    if a.self_test: self_test(); return 0
    if not a.experience: raise SystemExit("--experience is required unless --self-test is used")
    r=run(load_json(Path(a.self_model)),load_json(Path(a.experience)),a.dev_seed,a.ood_seed); out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(r,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":r["status"],"target":r["candidate"]["target_deficit"],"selected_features":r["candidate"]["features"],"development_score":r["development"]["final_metrics"]["score"],"ood_baseline_score":r["fresh_ood"]["baseline"]["score"],"ood_candidate_score":r["fresh_ood"]["candidate"]["score"],"ood_gain":r["fresh_ood"]["absolute_gain"],"measured_benchmark_improvement":r["claims"]["measured_benchmark_improvement"],"evidence_digest":r["evidence_digest"]},indent=2,sort_keys=True))
    return 0 if r["status"].startswith("PASS_") else 2
if __name__ == "__main__": raise SystemExit(main())
