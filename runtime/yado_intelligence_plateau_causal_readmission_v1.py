from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,os,random,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json';ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json';LEDGER=REPO/'architecture'/'evolution-ledger.json';STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
FAILED=REPO/'receipts'/'yado-intelligence-plateau-fresh-admission-v2-run-33477399296.json'
V2SRC=REPO/'candidates'/'g2-self-evolution'/'budget_adaptive_compositional_schema_router_v2.py';V3SRC=REPO/'candidates'/'g2-self-evolution'/'coverage_pruned_compositional_schema_router_v3.py';META=REPO/'candidates'/'g2-self-evolution'/'coverage_pruned_compositional_schema_router_v3.json'
OUT=ROOT/'yado_intelligence_plateau_causal_readmission_v1_receipt.json'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
head=load(HEAD);ledger=load(LEDGER);state=load(STATE);failed=load(FAILED);meta=load(META);validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V3']:raise RuntimeError('UNEXPECTED_FRONTIER')
if failed.get('status')!='WITHHOLD_INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V2':raise RuntimeError('EXPECTED_FAILED_FRESH_GATE')
if not all(v>=.99 for v in failed.get('fresh_families',{}).values()):raise RuntimeError('NOT_CAUSAL_ONLY_WITHHOLD')
if failed.get('causal',{}).get('coverage_pruning') is not False:raise RuntimeError('CAUSAL_GAP_NOT_MISSING')
if fsha(V3SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('CANDIDATE_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

def load_cls(path,name,modname):
    sp=importlib.util.spec_from_file_location(modname,path);m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m);return getattr(m,name)
V2=load_cls(V2SRC,'BudgetAdaptiveCompositionalSchemaRouterV2','_v2causal')
V3=load_cls(V3SRC,'CoveragePrunedCompositionalSchemaRouterV3','_v3causal')

# Guaranteed differentiator:
# - true signal is a perfect width-1 rule and covers ALL positives.
# - p_spurious&q_spurious is also perfect in train and has high support, but neither atom alone is precise.
# - in test, p&q sometimes occurs in negatives.
def make_rows(train,count=720,n_noise=20):
    rng=random.Random(33001 if train else 33002);rows=[]
    for k in range(count):
        s=bool(k%2);x={f'n{i:02d}':bool(rng.getrandbits(1)) for i in range(n_noise)}
        if train:
            if s:p=q=True
            else:
                p,q=((True,False) if (k//2)%2==0 else (False,True))
        else:
            if s:p=q=True
            else:
                mode=(k//2)%3
                p,q=((True,True) if mode==0 else ((True,False) if mode==1 else (False,True)))
        x.update({'p_spurious':p,'q_spurious':q,'zz_true_signal':s})
        rows.append({'input':x,'expected':(CAP_REL,) if s else (CAP_CONJ,)})
    return rows
tr=make_rows(True,720);te=make_rows(False,360)
m2=V2.fit(tr,CAP_CONJ);m3=V3.fit(tr,CAP_CONJ)
s2=sum(V2.route(m2,z['input'])==z['expected'] for z in te)/len(te)
s3=sum(V3.route(m3,z['input'])==z['expected'] for z in te)/len(te)
gap=s3-s2

# Verify the mechanism difference directly in serialized learned rules.
def has_pair(model,out):
    return any(len(r.get('atoms',[]))==2 and {a['field'] for a in r['atoms']}=={'p_spurious','q_spurious'} for r in model.get('triggers',{}).get(out,[]))
old_keeps_spurious=has_pair(m2,CAP_REL)
new_prunes_spurious=not has_pair(m3,CAP_REL)
new_keeps_true_signal=any(len(r.get('atoms',[]))==1 and r['atoms'][0].get('field')=='zz_true_signal' for r in m3.get('triggers',{}).get(CAP_REL,[]))

checks={'failed_gate_was_causal_only':all(v>=.99 for v in failed.get('fresh_families',{}).values()) and failed.get('causal',{}).get('coverage_pruning') is False,
 'candidate_source_unchanged':fsha(V3SRC)==meta.get('candidate_source_sha256'),
 'v3_fresh_differentiator_pass':s3>=.99,'v2_fresh_differentiator_below':s2<=.90,'causal_gap':gap>=.10,
 'v2_keeps_spurious_pair':old_keeps_spurious,'v3_prunes_spurious_pair':new_prunes_spurious,'v3_keeps_true_signal':new_keeps_true_signal,
 'architecture_immutable':fsha(ARCH)==arch_sha,'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')}
passed=all(checks.values());next_cap='INTELLIGENCE_PLATEAU_CANONICAL_INTEGRATION_V1' if passed else 'INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V3'

state['candidate_history'].append({'round':state.get('round',11),'plane':'INTELLIGENCE','candidate_digest':meta['candidate_digest'],'status':'CAUSAL_READMISSION_PASS' if passed else 'CAUSAL_READMISSION_WITHHOLD','fresh_score':s3,'baseline_score':s2,'causal_drop':gap})
state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'});STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.intelligence_plateau_causal_readmission.v1','status':'PASS_INTELLIGENCE_PLATEAU_CAUSAL_READMISSION_V1' if passed else 'WITHHOLD_INTELLIGENCE_PLATEAU_CAUSAL_READMISSION_V1',
 'classification':'INSUFFICIENT_CAUSAL_DISCRIMINATION_IN_PRIOR_FRESH_GATE','candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'prior_fresh_receipt':failed['receipt_sha256'],'differentiator':{'v2_score':s2,'v3_score':s3,'gap':gap,'v2_keeps_spurious_pair':old_keeps_spurious,'v3_prunes_spurious_pair':new_prunes_spurious,'v3_keeps_true_signal':new_keeps_true_signal},
 'checks':checks,'architecture_sha256':arch_sha,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'CAUSAL READMISSION ONLY. CANDIDATE SOURCE IS UNCHANGED; NEW EVIDENCE DISTINGUISHES COVERAGE PRUNING FROM ITS UNPRUNED PREDECESSOR AFTER PRIOR FRESH FUNCTIONAL SCORE WAS ALREADY 1.0.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_INTELLIGENCE_PLATEAU_CAUSAL_READMISSION",'event_type':'CAUSAL_EVIDENCE_READMISSION',
 'status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':'INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V3',
 'effect':f"CLASS=CAUSAL_EVIDENCE_GAP; V2={s2:.6f}; V3={s3:.6f}; GAP={gap:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-intelligence-plateau-causal-readmission-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'classification':receipt['classification'],'differentiator':receipt['differentiator'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('INTELLIGENCE_PLATEAU_CAUSAL_READMISSION_WITHHELD')
