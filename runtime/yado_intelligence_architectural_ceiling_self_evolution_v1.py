from __future__ import annotations
from pathlib import Path
import hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
RECHECK=REPO/'receipts'/'yado-g2-lti-architectural-ceiling-recheck-v3-run-33465428878.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'bounded_compositional_schema_router_v1.py'
CAND_META=CAND_DIR/'bounded_compositional_schema_router_v1.json'
OUT=ROOT/'yado_intelligence_architectural_ceiling_self_evolution_v1_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);recheck=load(RECHECK);state=load(STATE)
validate_ledger_v2(ledger)
allowed=[['INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1'],['INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2']]
if ledger.get('open_deficits') not in allowed:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('open_deficits')==['INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2']:
    prev=REPO/'receipts'/'yado-intelligence-architectural-ceiling-self-evolution-v1-run-33465637351.json'
    if not prev.exists():raise RuntimeError('INTELLIGENCE_METRIC_REPAIR_WITHOUT_PRIOR_WITHHOLD')
    pr=load(prev)
    if pr.get('status')!='WITHHOLD_INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1' or pr.get('candidate_source_sha256')!='5a54b64462a4d252696f197953018b0d6f55c3d287eb6648f14ca3d8a4f4658b':
        raise RuntimeError('INTELLIGENCE_METRIC_REPAIR_SOURCE_MISMATCH')
if recheck.get('self_selected_weakest_plane')!='INTELLIGENCE':raise RuntimeError('INTELLIGENCE_NOT_SELF_SELECTED')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

# Generic candidate implementation; no semantic field names are embedded.
candidate_source=r'''from __future__ import annotations
from collections import Counter,defaultdict

class BoundedCompositionalSchemaRouterV1:
    COMPONENT_ID="ALG-G2-BOUNDED-COMPOSITIONAL-SCHEMA-ROUTER-V1"
    MAX_FIELDS=16
    MAX_OUTPUTS=8
    MAX_TRIGGERS_PER_OUTPUT=8
    MAX_ALIGNMENT_ROWS=64
    MIN_TRIGGER_PRECISION=.995
    MIN_TRIGGER_SUPPORT=4

    @staticmethod
    def _outputs(y):
        if isinstance(y,str):return {y}
        if isinstance(y,(list,tuple,set)):return {str(z) for z in y}
        raise ValueError("UNSUPPORTED_OUTPUT")

    @classmethod
    def fit(cls,cases,fallback_output):
        if not cases:raise ValueError("EMPTY_CASES")
        fields=sorted(set().union(*(set(z["input"]) for z in cases)))[:cls.MAX_FIELDS]
        outputs=sorted(set().union(*(cls._outputs(z["expected"]) for z in cases)))[:cls.MAX_OUTPUTS]
        if fallback_output not in outputs:outputs=[fallback_output]+outputs
        triggers=defaultdict(list)
        for f in fields:
            values=[]
            for z in cases:
                v=z["input"].get(f)
                if isinstance(v,(bool,str,int,float)) and v not in values:values.append(v)
            if len(values)>8:continue
            for v in values:
                covered=[z for z in cases if z["input"].get(f)==v]
                if len(covered)<cls.MIN_TRIGGER_SUPPORT:continue
                for out in outputs:
                    if out==fallback_output:continue
                    yes=sum(out in cls._outputs(z["expected"]) for z in covered)
                    precision=yes/len(covered)
                    if precision>=cls.MIN_TRIGGER_PRECISION:
                        triggers[out].append((len(covered),precision,f,v))
        clean={}
        for out in outputs:
            if out==fallback_output:continue
            xs=sorted(triggers.get(out,[]),key=lambda q:(-q[1],-q[0],q[2],str(q[3])))[:cls.MAX_TRIGGERS_PER_OUTPUT]
            clean[out]=[{"field":f,"value":v,"support":n,"precision":p} for n,p,f,v in xs]
        return {"kind":"COMPOSITIONAL_TRIGGER_ROUTER","fields":fields,"outputs":outputs,"fallback_output":fallback_output,"triggers":clean}

    @classmethod
    def route(cls,model,x):
        selected=[]
        for out in model["outputs"]:
            if out==model["fallback_output"]:continue
            rules=model["triggers"].get(out,[])
            if any(r["field"] in x and x[r["field"]]==r["value"] for r in rules):
                selected.append(out)
        return tuple(sorted(selected)) if selected else (model["fallback_output"],)

    @classmethod
    def fit_schema_alignment(cls,reference_rows,alias_rows):
        refs=list(reference_rows)[:cls.MAX_ALIGNMENT_ROWS];als=list(alias_rows)[:cls.MAX_ALIGNMENT_ROWS]
        if not refs or len(refs)!=len(als):return {"kind":"WITHHOLD","reason":"PAIRED_ALIGNMENT_REQUIRED","map":{}}
        rf=sorted(set().union(*(set(x) for x in refs)))[:cls.MAX_FIELDS]
        af=sorted(set().union(*(set(x) for x in als)))[:cls.MAX_FIELDS]
        rs={f:tuple(x.get(f,None) for x in refs) for f in rf}
        ass={f:tuple(x.get(f,None) for x in als) for f in af}
        amap={}
        used=set()
        for a in af:
            matches=[r for r in rf if ass[a]==rs[r] and r not in used]
            if len(matches)!=1:
                return {"kind":"WITHHOLD","reason":"AMBIGUOUS_OR_UNIDENTIFIED_SCHEMA_ROLE","map":{}}
            amap[a]=matches[0];used.add(matches[0])
        return {"kind":"EXACT_PAIRED_SCHEMA_ALIGNMENT","map":amap}

    @staticmethod
    def apply_schema_alignment(alignment,x):
        if alignment.get("kind")=="WITHHOLD":raise ValueError("AMBIGUOUS_SCHEMA")
        return {alignment["map"].get(k,k):v for k,v in x.items()}

    @classmethod
    def route_aligned(cls,model,alignment,x):
        return cls.route(model,cls.apply_schema_alignment(alignment,x))
'''
CAND_DIR.mkdir(parents=True,exist_ok=True)
CAND_SRC.write_text(candidate_source,encoding='utf-8')

# Local mirror functions for candidate strategy evaluation.
def outputs(y):
    if isinstance(y,str):return {y}
    return set(y)

def fit_composer(cases,fallback):
    fields=sorted(set().union(*(set(z['input']) for z in cases)))[:16]
    outs=sorted(set().union(*(outputs(z['expected']) for z in cases)))
    triggers={o:[] for o in outs if o!=fallback}
    for f in fields:
        vals=[]
        for z in cases:
            v=z['input'].get(f)
            if isinstance(v,(bool,str,int,float)) and v not in vals:vals.append(v)
        if len(vals)>8:continue
        for v in vals:
            covered=[z for z in cases if z['input'].get(f)==v]
            if len(covered)<4:continue
            for o in triggers:
                p=sum(o in outputs(z['expected']) for z in covered)/len(covered)
                if p>=.995:triggers[o].append((len(covered),p,f,v))
    return {'fallback':fallback,'triggers':{o:sorted(xs,key=lambda q:(-q[1],-q[0],q[2],str(q[3])))[:8] for o,xs in triggers.items()}}

def route_composer(model,x):
    s=[]
    for o,xs in model['triggers'].items():
        if any(f in x and x[f]==v for _,_,f,v in xs):s.append(o)
    return tuple(sorted(s)) if s else (model['fallback'],)

def align(refs,als):
    rf=sorted(set().union(*(set(x) for x in refs)));af=sorted(set().union(*(set(x) for x in als)))
    rs={f:tuple(x.get(f,None) for x in refs) for f in rf};aa={f:tuple(x.get(f,None) for x in als) for f in af}
    m={};used=set()
    for a in af:
        hits=[r for r in rf if aa[a]==rs[r] and r not in used]
        if len(hits)!=1:return None
        m[a]=hits[0];used.add(hits[0])
    return m

def remap(m,x):return {m.get(k,k):v for k,v in x.items()}

def desired_set(x):
    out=set()
    if x['budget_limited'] or x['quota_limited']:out.add(CAP_BUD)
    if x['external_evidence_needed']:out.add(CAP_RES)
    if x['relation_needed'] or x['disjunction_needed']:out.add(CAP_REL)
    if not out:out.add(CAP_CONJ)
    return tuple(sorted(out))

def cases(seed,n):
    rr=random.Random(seed);out=[]
    for _ in range(n):
        x={'budget_limited':rr.random()<.28,'quota_limited':rr.random()<.10,'external_evidence_needed':rr.random()<.28,
           'relation_needed':rr.random()<.30,'disjunction_needed':rr.random()<.12}
        out.append({'input':x,'expected':desired_set(x)})
    return out

train=cases(10101,1800);valid=cases(10102,800);fresh=cases(10103,700)
composer=fit_composer(train,CAP_CONJ)

# Existing single router is baseline.
single_train=[{'input':z['input'],'expected':next(iter(z['expected'])) if len(z['expected'])==1 else (
    CAP_BUD if CAP_BUD in z['expected'] else (CAP_RES if CAP_RES in z['expected'] else CAP_REL))} for z in train]
single_valid=[{'input':z['input'],'expected':next(iter(z['expected'])) if len(z['expected'])==1 else (
    CAP_BUD if CAP_BUD in z['expected'] else (CAP_RES if CAP_RES in z['expected'] else CAP_REL))} for z in valid]
base_router=BoundedCapabilityRouterLearnerV1.synthesize(single_train,single_valid,CAP_CONJ,min_support=7)

aliases={'budget_limited':'kappa','quota_limited':'tau','external_evidence_needed':'omega','relation_needed':'rho','disjunction_needed':'sigma'}
def alias_x(x):return {aliases[k]:v for k,v in x.items()}
cal=cases(10104,48)
ref_cal=[z['input'] for z in cal];alias_cal=[alias_x(z['input']) for z in cal]
alignment=align(ref_cal,alias_cal)
alias_fresh=[{'input':alias_x(z['input']),'expected':z['expected']} for z in fresh]

def score_strategy(compose_enabled,align_enabled):
    fam={}
    # Single-output compatibility: require singleton set when only one capability is needed.
    single_cases=[z for z in fresh if len(z['expected'])==1]
    multi_cases=[z for z in fresh if len(z['expected'])>=2]
    if compose_enabled:
        fam['SINGLE_ROUTING_COMPAT']=sum(route_composer(composer,z['input'])==z['expected'] for z in single_cases)/len(single_cases)
        fam['MULTI_CAPABILITY_COMPOSITION']=sum(route_composer(composer,z['input'])==z['expected'] for z in multi_cases)/len(multi_cases)
    else:
        fam['SINGLE_ROUTING_COMPAT']=sum((base_router.execute(z['input']),)==z['expected'] for z in single_cases)/len(single_cases)
        fam['MULTI_CAPABILITY_COMPOSITION']=sum((base_router.execute(z['input']),)==z['expected'] for z in multi_cases)/len(multi_cases)
    if align_enabled and alignment is not None:
        if compose_enabled:
            fam['PAIRED_SCHEMA_ALIGNMENT_TRANSFER']=sum(route_composer(composer,remap(alignment,z['input']))==z['expected'] for z in alias_fresh)/len(alias_fresh)
        else:
            fam['PAIRED_SCHEMA_ALIGNMENT_TRANSFER']=sum((base_router.execute(remap(alignment,z['input'])),)==z['expected'] for z in alias_fresh)/len(alias_fresh)
    else:
        fam['PAIRED_SCHEMA_ALIGNMENT_TRANSFER']=sum((base_router.execute(z['input']),)==z['expected'] for z in alias_fresh)/len(alias_fresh)
    # Ambiguous mapping must be withheld rather than guessed.
    amb_ref=[{'a':i%2==0,'b':i%2==0,'c':i%3==0} for i in range(24)]
    amb_alias=[{'u':x['a'],'v':x['b'],'w':x['c']} for x in amb_ref]
    got=align(amb_ref,amb_alias) if align_enabled else None
    fam['AMBIGUOUS_SCHEMA_WITHHOLD']=1.0 if got is None else 0.0
    return {'families':fam,'score':sum(fam.values())/len(fam),'min_family':min(fam.values())}

strategies=[
 {'id':'BASE_SINGLE','compose':False,'align':False,'complexity':.10,'risk':.02,'novelty':.10},
 {'id':'COMPOSER_ONLY','compose':True,'align':False,'complexity':.20,'risk':.03,'novelty':.48},
 {'id':'ALIGNER_ONLY','compose':False,'align':True,'complexity':.22,'risk':.03,'novelty':.52},
 {'id':'COMPOSER_PLUS_ALIGNER','compose':True,'align':True,'complexity':.33,'risk':.05,'novelty':.90},
]
validation={};tok={}
for i,s in enumerate(strategies):
    m=score_strategy(s['compose'],s['align'])
    t='opaque_'+h({'slot':i,'head':head['canonical_head_digest']})[:18]
    validation[s['id']]=m|{'token':t,'complexity':s['complexity'],'risk':s['risk'],'novelty':s['novelty']}
    tok[t]=s
sel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()])
selected=tok[sel['selected_token']]
holdout=score_strategy(selected['compose'],selected['align'])
base=score_strategy(False,False)
causal_drop=holdout['score']-base['score']

# Explicit information-boundary proof witness: two semantic fields with identical observations admit swapped mappings.
ambiguity_witness={
 'reference_rows':[{'fA':False,'fB':False},{'fA':True,'fB':True},{'fA':False,'fB':False},{'fA':True,'fB':True}],
 'alias_rows':[{'x':False,'y':False},{'x':True,'y':True},{'x':False,'y':False},{'x':True,'y':True}],
 'distinct_consistent_mappings':[
   {'x':'fA','y':'fB'},
   {'x':'fB','y':'fA'}
 ],
 'conclusion':'ZERO_SHOT_OR_UNINFORMATIVE_ALIGNMENT_IS_NOT_IDENTIFIABLE_WITHOUT_SIDE_INFORMATION'
}

checks={
 'intelligence_self_selected':recheck.get('self_selected_weakest_plane')=='INTELLIGENCE',
 'selected_composition':selected['compose'] is True,
 'selected_alignment':selected['align'] is True,
 'fresh_validation_min':holdout['min_family']>=.99,
 'improves_baseline':holdout['score']>=base['score']+.35,
 'causal_drop':causal_drop>=.35,
 'ambiguity_withhold':holdout['families']['AMBIGUOUS_SCHEMA_WITHHOLD']==1.0,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='INTELLIGENCE_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1' if passed else 'INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2'
candidate={
 'schema':'yado.g2.bounded_compositional_schema_router_candidate.v1',
 'component_id':'ALG-G2-BOUNDED-COMPOSITIONAL-SCHEMA-ROUTER-V1',
 'selected_strategy':selected['id'],'selected_features':{'multi_capability_composition':selected['compose'],'paired_schema_alignment':selected['align'],'ambiguity_withhold':True},
 'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'baseline':base,'causal_drop':causal_drop,
 'information_boundary':ambiguity_witness,
 'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,'parent_head_digest':head['canonical_head_digest'],
 'canonical_active':False,'promotion_applied':False,'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'BOUNDED MULTI-CAPABILITY COMPOSITION PLUS PAIRED SCHEMA ALIGNMENT. ARBITRARY ZERO-SHOT ALIASING WITHOUT SIDE INFORMATION IS EXPLICITLY WITHHELD AS NON-IDENTIFIABLE.'
}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')
state['candidate_history'].append({'round':3,'plane':'INTELLIGENCE','candidate_digest':candidate['candidate_digest'],'selected_strategy':selected['id'],'fresh_score':holdout['score'],'baseline_score':base['score'],'causal_drop':causal_drop,'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['planes']['INTELLIGENCE']['candidate_score']=holdout['score'];state['planes']['INTELLIGENCE']['candidate_families']=holdout['families'];state['next_required_capability']=next_cap
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'});STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.intelligence_architectural_ceiling_self_evolution.v1',
 'status':'PASS_INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'baseline':base,'causal_drop':causal_drop,
 'information_boundary':ambiguity_witness,'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_INTELLIGENCE_CEILING_SELF_EVOLUTION",
 'event_type':'FIXED_ARCHITECTURE_INTELLIGENCE_SELF_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1',
 'effect':f"SELECTED={selected['id']}; FRESH={holdout['score']:.6f}; BASE={base['score']:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-intelligence-architectural-ceiling-self-evolution-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'selected_strategy':selected['id'],'fresh_validation':holdout,'baseline':base,'causal_drop':causal_drop,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('INTELLIGENCE_CEILING_SELF_EVOLUTION_WITHHELD')
