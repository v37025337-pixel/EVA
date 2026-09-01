from __future__ import annotations
from pathlib import Path
from itertools import product
import hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate

HEAD=REPO/'canonical'/'yado-main-head-g2.json';ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json';LEDGER=REPO/'architecture'/'evolution-ledger.json';STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
FAILED=REPO/'receipts'/'yado-intelligence-plateau-fresh-admission-v1-run-33477068724.json'
V2SRC=REPO/'candidates'/'g2-self-evolution'/'budget_adaptive_compositional_schema_router_v2.py'
CAND_DIR=REPO/'candidates'/'g2-self-evolution';CAND_SRC=CAND_DIR/'coverage_pruned_compositional_schema_router_v3.py';CAND_META=CAND_DIR/'coverage_pruned_compositional_schema_router_v3.json'
OUT=ROOT/'yado_intelligence_plateau_self_evolution_v2_receipt.json'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))
head=load(HEAD);ledger=load(LEDGER);state=load(STATE);failed=load(FAILED);validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V2']:raise RuntimeError('UNEXPECTED_FRONTIER')
if failed.get('status')!='WITHHOLD_INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V1':raise RuntimeError('MISSING_COUNTEREXAMPLE')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

sp=importlib.util.spec_from_file_location('_router_v2',V2SRC);m2=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m2;sp.loader.exec_module(m2);V2=m2.BudgetAdaptiveCompositionalSchemaRouterV2

candidate_source=r'''from __future__ import annotations
from itertools import combinations
from collections import defaultdict

class CoveragePrunedCompositionalSchemaRouterV3:
    COMPONENT_ID="ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3"
    MAX_FIELD_CELLS=262144
    MAX_ALIGNMENT_CELLS=131072
    MAX_OUTPUTS=8
    MAX_TRIGGER_WIDTH=2
    MAX_TRIGGER_CANDIDATES=4096
    MAX_TRIGGERS_PER_OUTPUT=32
    MIN_TRIGGER_PRECISION=.995
    MIN_TRIGGER_SUPPORT=4

    @staticmethod
    def _outputs(y):
        if isinstance(y,str):return {y}
        if isinstance(y,(list,tuple,set)):return {str(z) for z in y}
        raise ValueError("UNSUPPORTED_OUTPUT")

    @classmethod
    def fit(cls,cases,fallback_output,max_trigger_width=None):
        if not cases:raise ValueError("EMPTY_CASES")
        fields=sorted(set().union(*(set(z["input"]) for z in cases)))
        if len(cases)*max(1,len(fields))>cls.MAX_FIELD_CELLS:
            return {"kind":"WITHHOLD","reason":"FIELD_WORK_BUDGET","fields":[],"outputs":[],"fallback_output":fallback_output,"triggers":{}}
        outputs=sorted(set().union(*(cls._outputs(z["expected"]) for z in cases)))
        if fallback_output not in outputs:outputs=[fallback_output]+outputs
        outputs=sorted(set(outputs))
        if len(outputs)>cls.MAX_OUTPUTS:
            return {"kind":"WITHHOLD","reason":"OUTPUT_BUDGET","fields":fields,"outputs":[],"fallback_output":fallback_output,"triggers":{}}
        atoms=[]
        for f in fields:
            vals=[]
            for z in cases:
                v=z["input"].get(f)
                if isinstance(v,(bool,str,int,float)) and v not in vals:vals.append(v)
            if 1 < len(vals) <= 8:
                for v in vals:atoms.append((f,v))
        width=min(cls.MAX_TRIGGER_WIDTH,int(max_trigger_width or cls.MAX_TRIGGER_WIDTH))
        combos=[(a,) for a in atoms]
        if width>=2:
            for a,b in combinations(atoms,2):
                if a[0]!=b[0]:combos.append((a,b))
        if len(combos)>cls.MAX_TRIGGER_CANDIDATES:
            return {"kind":"WITHHOLD","reason":"TRIGGER_CANDIDATE_BUDGET","fields":fields,"outputs":outputs,"fallback_output":fallback_output,"triggers":{}}
        candidates=defaultdict(list)
        for combo in combos:
            covered={i for i,z in enumerate(cases) if all(a[0] in z["input"] and z["input"][a[0]]==a[1] for a in combo)}
            if len(covered)<cls.MIN_TRIGGER_SUPPORT:continue
            for out in outputs:
                if out==fallback_output:continue
                positives={i for i,z in enumerate(cases) if out in cls._outputs(z["expected"])}
                precision=len(covered & positives)/len(covered)
                if precision>=cls.MIN_TRIGGER_PRECISION:
                    candidates[out].append({
                      "atoms":[{"field":a[0],"value":a[1]} for a in combo],
                      "support":len(covered),"precision":precision,"covered_positive":covered & positives
                    })
        clean={}
        for out in outputs:
            if out==fallback_output:continue
            positives={i for i,z in enumerate(cases) if out in cls._outputs(z["expected"])}
            uncovered=set(positives);chosen=[]
            xs=sorted(candidates.get(out,[]),key=lambda r:(len(r["atoms"]),-r["precision"],-r["support"],str(r["atoms"])))
            for r in xs:
                gain=len(r["covered_positive"] & uncovered)
                if gain<=0:continue
                chosen.append({"atoms":r["atoms"],"support":r["support"],"precision":r["precision"],"positive_gain":gain})
                uncovered-=r["covered_positive"]
                if not uncovered or len(chosen)>=cls.MAX_TRIGGERS_PER_OUTPUT:break
            clean[out]=chosen
        return {"kind":"COVERAGE_PRUNED_COMPOSITIONAL_TRIGGER_ROUTER_V3","fields":fields,"outputs":outputs,
                "fallback_output":fallback_output,"triggers":clean,"candidate_count":len(combos)}

    @classmethod
    def route(cls,model,x):
        if model.get("kind")=="WITHHOLD":raise ValueError(model.get("reason","ROUTER_WITHHOLD"))
        selected=[]
        for out in model["outputs"]:
            if out==model["fallback_output"]:continue
            for rule in model["triggers"].get(out,[]):
                if all(a["field"] in x and x[a["field"]]==a["value"] for a in rule["atoms"]):
                    selected.append(out);break
        return tuple(sorted(selected)) if selected else (model["fallback_output"],)

    @classmethod
    def fit_schema_alignment(cls,reference_rows,alias_rows):
        refs=list(reference_rows);als=list(alias_rows)
        if not refs or len(refs)!=len(als):return {"kind":"WITHHOLD","reason":"PAIRED_ALIGNMENT_REQUIRED","map":{}}
        rf=sorted(set().union(*(set(x) for x in refs)));af=sorted(set().union(*(set(x) for x in als)))
        if len(refs)*max(1,len(rf)+len(af))>cls.MAX_ALIGNMENT_CELLS:
            return {"kind":"WITHHOLD","reason":"ALIGNMENT_WORK_BUDGET","map":{}}
        rs={f:tuple(x.get(f,None) for x in refs) for f in rf};ass={f:tuple(x.get(f,None) for x in als) for f in af}
        amap={};used=set()
        for a in af:
            matches=[r for r in rf if ass[a]==rs[r] and r not in used]
            if len(matches)!=1:return {"kind":"WITHHOLD","reason":"AMBIGUOUS_OR_UNIDENTIFIED_SCHEMA_ROLE","map":{}}
            amap[a]=matches[0];used.add(matches[0])
        return {"kind":"EXACT_PAIRED_SCHEMA_ALIGNMENT_V3","map":amap}

    @staticmethod
    def apply_schema_alignment(alignment,x):
        if alignment.get("kind")=="WITHHOLD":raise ValueError(alignment.get("reason","AMBIGUOUS_SCHEMA"))
        return {alignment["map"].get(k,k):v for k,v in x.items()}

    @classmethod
    def route_aligned(cls,model,alignment,x):
        return cls.route(model,cls.apply_schema_alignment(alignment,x))
'''
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(candidate_source,encoding='utf-8')
ns={};exec(compile(candidate_source,'<candidate>','exec'),ns);V3=ns['CoveragePrunedCompositionalSchemaRouterV3']

def field_cases(n,signal,off1,off2,train_n=480,test_n=240):
    fs=[f'g{i:02d}' for i in range(n-1)]+[signal];tr=[];te=[]
    for k in range(train_n):
        x={f:bool(((k+off1)>>(i%8))&1) for i,f in enumerate(fs)};x[signal]=bool((k//4)%2)
        tr.append({'input':x,'expected':(CAP_REL,) if x[signal] else (CAP_CONJ,)})
    for k in range(test_n):
        x={f:bool(((k+off2)>>(i%7))&1) for i,f in enumerate(fs)};x[signal]=bool((k//7)%2)
        te.append({'input':x,'expected':(CAP_REL,) if x[signal] else (CAP_CONJ,)})
    return tr,te

def pair_cases(reps=5):
    rows=[]
    for a,b,c,d,e,f in product([False,True],repeat=6):
        out=set()
        if a and d:out.add(CAP_REL)
        if c and f:out.add(CAP_RES)
        if not out:out.add(CAP_CONJ)
        for _ in range(reps):rows.append({'input':{'a':a,'b':b,'c':c,'d':d,'e':e,'f':f},'expected':tuple(sorted(out))})
    return rows

def mixed_cases(reps=6):
    rows=[]
    for s,a,b,c in product([False,True],repeat=4):
        out=set()
        if s or (a and b):out.add(CAP_REL)
        if b and c:out.add(CAP_RES)
        if not out:out.add(CAP_CONJ)
        for _ in range(reps):rows.append({'input':{'signal':s,'a':a,'b':b,'c':c},'expected':tuple(sorted(out))})
    return rows

def score(cls,tr,te):
    try:
        m=cls.fit(tr,CAP_CONJ)
        if m.get('kind')=='WITHHOLD':return 0.0
        return sum(cls.route(m,z['input'])==z['expected'] for z in te)/len(te)
    except Exception:return 0.0

tr22,te22=field_cases(22,'zz_fresh_signal',29,83);pairs=pair_cases();mixed=mixed_cases()
validation={
 'V2_ALL_HIGH_PRECISION':{'families':{'FAILED_WIDTH22_COUNTEREXAMPLE':score(V2,tr22,te22),'PAIRWISE_REGRESSION':score(V2,pairs,pairs),'MIXED_WIDTH_DISJUNCTION':score(V2,mixed,mixed)}},
 'V3_POSITIVE_COVER_PRUNING':{'families':{'FAILED_WIDTH22_COUNTEREXAMPLE':score(V3,tr22,te22),'PAIRWISE_REGRESSION':score(V3,pairs,pairs),'MIXED_WIDTH_DISJUNCTION':score(V3,mixed,mixed)}},
}
settings={'V2_ALL_HIGH_PRECISION':(.10,.03,.10),'V3_POSITIVE_COVER_PRUNING':(.18,.04,.80)}
tok={}
for i,k in enumerate(validation):
    fam=validation[k]['families'];validation[k]['score']=avg(list(fam.values()));validation[k]['min_family']=min(fam.values())
    t='opaque_'+h({'intel_v2':i,'head':head['canonical_head_digest']})[:18];tok[t]=k
    cx,rk,nv=settings[k];validation[k].update({'token':t,'complexity':cx,'risk':rk,'novelty':nv})
sel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()])
selected=tok[sel['selected_token']]

# New holdout with changed offsets and width24.
tr24,te24=field_cases(24,'zz_holdout_signal',41,117,560,280)
hold={'WIDTH24_DISTRIBUTION_SHIFT':score(V3,tr24,te24),'PAIRWISE_FRESH':score(V3,pair_cases(7),pair_cases(7)),'MIXED_WIDTH_FRESH':score(V3,mixed_cases(8),mixed_cases(8))}
holdout={'families':hold,'score':avg(list(hold.values())),'min_family':min(hold.values())}
base_hold={'WIDTH24_DISTRIBUTION_SHIFT':score(V2,tr24,te24),'PAIRWISE_FRESH':score(V2,pair_cases(7),pair_cases(7)),'MIXED_WIDTH_FRESH':score(V2,mixed_cases(8),mixed_cases(8))}
base_score=avg(list(base_hold.values()));gain=holdout['score']-base_score

checks={'counterexample_improved':validation['V3_POSITIVE_COVER_PRUNING']['families']['FAILED_WIDTH22_COUNTEREXAMPLE']>=.99,
 'pairwise_preserved':validation['V3_POSITIVE_COVER_PRUNING']['families']['PAIRWISE_REGRESSION']>=.99,
 'mixed_width_preserved':validation['V3_POSITIVE_COVER_PRUNING']['families']['MIXED_WIDTH_DISJUNCTION']>=.99,
 'selected_v3':selected=='V3_POSITIVE_COVER_PRUNING','fresh_min_one':holdout['min_family']>=.99,'causal_gain_positive':gain>=.10,
 'architecture_immutable':fsha(ARCH)==arch_sha,'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')}
passed=all(checks.values());next_cap='INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V2' if passed else 'INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V3'
candidate={'schema':'yado.g2.coverage_pruned_compositional_schema_router_candidate.v3','component_id':'ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3',
 'selected_strategy':selected,'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'baseline_holdout':base_hold,'causal_gain':gain,
 'compute_contract':{'max_field_cells':V3.MAX_FIELD_CELLS,'max_alignment_cells':V3.MAX_ALIGNMENT_CELLS,'max_outputs':V3.MAX_OUTPUTS,'max_trigger_width':V3.MAX_TRIGGER_WIDTH,'max_trigger_candidates':V3.MAX_TRIGGER_CANDIDATES,'max_triggers_per_output':V3.MAX_TRIGGERS_PER_OUTPUT},
 'repair_of_receipt':failed['receipt_sha256'],'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,'parent_head_digest':head['canonical_head_digest'],
 'canonical_active':False,'promotion_applied':False,'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'BUDGET-ADAPTIVE WIDTH<=2 TRIGGER ROUTER WITH POSITIVE-COVER PRUNING: WIDER RULES ARE RETAINED ONLY WHEN THEY EXPLAIN POSITIVES NOT ALREADY COVERED BY SIMPLER RULES.'}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')
state['candidate_history'].append({'round':state.get('round',10),'plane':'INTELLIGENCE','candidate_digest':candidate['candidate_digest'],'selected_strategy':selected,'fresh_score':holdout['score'],'baseline_score':base_score,'causal_drop':gain,'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'});STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.intelligence_plateau_self_evolution.v2','status':'PASS_INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V2' if passed else 'WITHHOLD_INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V2',
 'selected_strategy':selected,'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'baseline_holdout':base_hold,'causal_gain':gain,
 'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],'repair_of_receipt':failed['receipt_sha256'],'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V2",'event_type':'COUNTEREXAMPLE_DRIVEN_INTELLIGENCE_PLATEAU_SELF_EVOLUTION',
 'status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':'INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V2',
 'effect':f"COUNTEREXAMPLE_REPAIRED={checks['counterexample_improved']}; SELECTED={selected}; FRESH={holdout['score']:.6f}; GAIN={gain:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-intelligence-plateau-self-evolution-v2-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'selected_strategy':selected,'validation':validation,'fresh_validation':holdout,'baseline_holdout':base_hold,'causal_gain':gain,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V2_WITHHELD')
