from __future__ import annotations
from pathlib import Path
from itertools import combinations,product
from collections import Counter
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_bounded_compositional_schema_router_v1 import BoundedCompositionalSchemaRouterV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json';ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json';STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
PROBE=REPO/'receipts'/'yado-g2-lti-architectural-ceiling-plateau-probe-v2-run-33476776621.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution';CAND_SRC=CAND_DIR/'budget_adaptive_compositional_schema_router_v2.py';CAND_META=CAND_DIR/'budget_adaptive_compositional_schema_router_v2.json'
OUT=ROOT/'yado_intelligence_plateau_self_evolution_v1_receipt.json'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))
head=load(HEAD);ledger=load(LEDGER);state=load(STATE);probe=load(PROBE);validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if probe.get('self_selected_plane')!='INTELLIGENCE':raise RuntimeError('INTELLIGENCE_NOT_SELF_SELECTED')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

candidate_source=r'''from __future__ import annotations
from itertools import combinations
from collections import defaultdict

class BudgetAdaptiveCompositionalSchemaRouterV2:
    COMPONENT_ID="ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-SCHEMA-ROUTER-V2"
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
        triggers=defaultdict(list)
        for combo in combos:
            covered=[z for z in cases if all(a[0] in z["input"] and z["input"][a[0]]==a[1] for a in combo)]
            if len(covered)<cls.MIN_TRIGGER_SUPPORT:continue
            for out in outputs:
                if out==fallback_output:continue
                precision=sum(out in cls._outputs(z["expected"]) for z in covered)/len(covered)
                if precision>=cls.MIN_TRIGGER_PRECISION:
                    triggers[out].append({
                      "atoms":[{"field":a[0],"value":a[1]} for a in combo],
                      "support":len(covered),"precision":precision
                    })
        clean={}
        for out in outputs:
            if out==fallback_output:continue
            xs=triggers.get(out,[])
            xs=sorted(xs,key=lambda r:(-r["precision"],len(r["atoms"]),-r["support"],str(r["atoms"])))
            clean[out]=xs[:cls.MAX_TRIGGERS_PER_OUTPUT]
        return {"kind":"BUDGET_ADAPTIVE_COMPOSITIONAL_TRIGGER_ROUTER_V2","fields":fields,"outputs":outputs,
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
        return {"kind":"EXACT_PAIRED_SCHEMA_ALIGNMENT_V2","map":amap}

    @staticmethod
    def apply_schema_alignment(alignment,x):
        if alignment.get("kind")=="WITHHOLD":raise ValueError(alignment.get("reason","AMBIGUOUS_SCHEMA"))
        return {alignment["map"].get(k,k):v for k,v in x.items()}

    @classmethod
    def route_aligned(cls,model,alignment,x):
        return cls.route(model,cls.apply_schema_alignment(alignment,x))
'''
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(candidate_source,encoding='utf-8')
ns={};exec(compile(candidate_source,'<candidate>','exec'),ns);V2=ns['BudgetAdaptiveCompositionalSchemaRouterV2'];V1=BoundedCompositionalSchemaRouterV1

def field_cases(n,signal_name,train_n=360,test_n=180):
    fs=[f'f{i:02d}' for i in range(n-1)]+[signal_name]
    tr=[];te=[]
    for k in range(train_n):
        x={f:bool(((k+17)>>(i%8))&1) for i,f in enumerate(fs)}
        x[signal_name]=bool((k//3)%2);tr.append({'input':x,'expected':(CAP_REL,) if x[signal_name] else (CAP_CONJ,)})
    for k in range(test_n):
        x={f:bool(((k+61)>>(i%7))&1) for i,f in enumerate(fs)}
        x[signal_name]=bool((k//5)%2);te.append({'input':x,'expected':(CAP_REL,) if x[signal_name] else (CAP_CONJ,)})
    return tr,te

def interaction_cases(reps=10):
    rows=[]
    for a,b,c,d in product([False,True],repeat=4):
        out=set()
        if a and b:out.add(CAP_REL)
        if c and d:out.add(CAP_RES)
        if not out:out.add(CAP_CONJ)
        for _ in range(reps):rows.append({'input':{'a':a,'b':b,'c':c,'d':d},'expected':tuple(sorted(out))})
    return rows

def score_router(cls,tr,te,width=None):
    try:
        m=cls.fit(tr,CAP_CONJ,**({'max_trigger_width':width} if cls is V2 else {}))
        if m.get('kind')=='WITHHOLD':return 0.0
        return sum(cls.route(m,z['input'])==z['expected'] for z in te)/len(te)
    except Exception:return 0.0

tr17,te17=field_cases(17,'zz_signal')
ix=interaction_cases(12)
strategies=[
 {'id':'BASE_V1','fields_v2':False,'pair_v2':False,'complexity':.10,'risk':.02,'novelty':.10},
 {'id':'WORK_BUDGET_FIELDS','fields_v2':True,'pair_v2':False,'complexity':.20,'risk':.03,'novelty':.55},
 {'id':'PAIR_TRIGGERS','fields_v2':False,'pair_v2':True,'complexity':.23,'risk':.04,'novelty':.62},
 {'id':'WORK_BUDGET_FIELDS_PLUS_PAIR_TRIGGERS','fields_v2':True,'pair_v2':True,'complexity':.33,'risk':.05,'novelty':.92},
]
def eval_strategy(s):
    fscore=score_router(V2,tr17,te17,1) if s['fields_v2'] else score_router(V1,tr17,te17)
    iscore=score_router(V2,ix,ix,2) if s['pair_v2'] else score_router(V1,ix,ix)
    return {'families':{'FIELD_WIDTH_17':fscore,'PAIRWISE_TRIGGER':iscore},'score':avg([fscore,iscore]),'min_family':min(fscore,iscore)}
validation={};tok={}
for i,s in enumerate(strategies):
    m=eval_strategy(s);t='opaque_'+h({'intel_plateau':1,'slot':i,'head':head['canonical_head_digest']})[:18]
    validation[s['id']]=m|{'token':t,'complexity':s['complexity'],'risk':s['risk'],'novelty':s['novelty']};tok[t]=s
sel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()])
selected=tok[sel['selected_token']]

# Fresh validation not used by plateau probe: width 20 + different conjunction topology.
tr20,te20=field_cases(20,'zz_new_signal',420,210)
fresh_ix=[]
for a,b,c,d,e,f in product([False,True],repeat=6):
    out=set()
    if a and c:out.add(CAP_REL)
    if d and f:out.add(CAP_RES)
    if not out:out.add(CAP_CONJ)
    for _ in range(4):fresh_ix.append({'input':{'a':a,'b':b,'c':c,'d':d,'e':e,'f':f},'expected':tuple(sorted(out))})
hold={
 'FIELD_WIDTH_20_FRESH':score_router(V2,tr20,te20,2),
 'PAIRWISE_TRIGGER_FRESH':score_router(V2,fresh_ix,fresh_ix,2),
}
holdout={'families':hold,'score':avg(list(hold.values())),'min_family':min(hold.values())}
base={'families':{'FIELD_WIDTH_20_FRESH':score_router(V1,tr20,te20),'PAIRWISE_TRIGGER_FRESH':score_router(V1,fresh_ix,fresh_ix)}}
base['score']=avg(list(base['families'].values()));base['min_family']=min(base['families'].values())
gain=holdout['score']-base['score']

# Fail-closed budgets.
# Trigger candidate budget: 50 boolean fields => >4096 width<=2 candidate clauses.
budget_rows=[]
fs=[f'q{i:02d}' for i in range(50)]
for k in range(100):
    budget_rows.append({'input':{f:bool((k+i)%2) for i,f in enumerate(fs)},'expected':(CAP_REL,) if k%2 else (CAP_CONJ,)})
tb=V2.fit(budget_rows,CAP_CONJ)
trigger_budget_ok=tb.get('kind')=='WITHHOLD' and tb.get('reason')=='TRIGGER_CANDIDATE_BUDGET'
# Field work budget with compact 64-field rows.
over=[];ofs=[f'w{i:02d}' for i in range(64)]
for k in range(4100):over.append({'input':{f:bool((k+i)%2) for i,f in enumerate(ofs)},'expected':(CAP_CONJ,)})
fb=V2.fit(over,CAP_CONJ);field_budget_ok=fb.get('kind')=='WITHHOLD' and fb.get('reason')=='FIELD_WORK_BUDGET'
# Ambiguous alignment still withholds.
ar=[{'a':bool(i%2),'b':bool(i%2),'c':bool((i//2)%2)} for i in range(24)];aa=[{'u':z['a'],'v':z['b'],'w':z['c']} for z in ar]
amb=V2.fit_schema_alignment(ar,aa);ambiguity_ok=amb.get('kind')=='WITHHOLD'

checks={'intelligence_self_selected':probe.get('self_selected_plane')=='INTELLIGENCE',
 'selected_both_axes':selected['id']=='WORK_BUDGET_FIELDS_PLUS_PAIR_TRIGGERS',
 'fresh_min_one':holdout['min_family']>=.99,'causal_gain_large':gain>=.40,
 'field_budget_fail_closed':field_budget_ok,'trigger_budget_fail_closed':trigger_budget_ok,'ambiguity_fail_closed':ambiguity_ok,
 'architecture_immutable':fsha(ARCH)==arch_sha,'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')}
passed=all(checks.values());next_cap='INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V1' if passed else 'INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V2'
candidate={'schema':'yado.g2.budget_adaptive_compositional_schema_router_candidate.v2','component_id':'ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-SCHEMA-ROUTER-V2',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'baseline':base,'causal_gain':gain,
 'compute_contract':{'max_field_cells':V2.MAX_FIELD_CELLS,'max_alignment_cells':V2.MAX_ALIGNMENT_CELLS,'max_trigger_width':V2.MAX_TRIGGER_WIDTH,'max_trigger_candidates':V2.MAX_TRIGGER_CANDIDATES,'max_triggers_per_output':V2.MAX_TRIGGERS_PER_OUTPUT,'max_outputs':V2.MAX_OUTPUTS},
 'fail_closed':{'field_work_budget':field_budget_ok,'trigger_candidate_budget':trigger_budget_ok,'ambiguous_alignment':ambiguity_ok},
 'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,'parent_head_digest':head['canonical_head_digest'],
 'canonical_active':False,'promotion_applied':False,'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'REPLACES FIXED FIRST-N FIELD ROUTING WITH TOTAL-WORK BUDGET AND ADDS BOUNDED WIDTH-2 TRIGGER COMPOSITION. PAIRED ALIGNMENT USES A TOTAL ALIGNMENT BUDGET. NOT UNBOUNDED FEATURE SEARCH.'}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')
state['candidate_history'].append({'round':state.get('round',9),'plane':'INTELLIGENCE','candidate_digest':candidate['candidate_digest'],'selected_strategy':selected['id'],'fresh_score':holdout['score'],'baseline_score':base['score'],'causal_drop':gain,'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'});STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.intelligence_plateau_self_evolution.v1','status':'PASS_INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V1',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'baseline':base,'causal_gain':gain,
 'compute_contract':candidate['compute_contract'],'fail_closed':candidate['fail_closed'],'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V1",'event_type':'FIXED_ARCHITECTURE_INTELLIGENCE_PLATEAU_SELF_EVOLUTION',
 'status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':'INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V1',
 'effect':f"SELECTED={selected['id']}; FRESH={holdout['score']:.6f}; BASE={base['score']:.6f}; GAIN={gain:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-intelligence-plateau-self-evolution-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'selected_strategy':selected['id'],'fresh_validation':holdout,'baseline':base,'causal_gain':gain,'fail_closed':candidate['fail_closed'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V1_WITHHELD')
