from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'semantic_expression_synthesizer_v1.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'semantic_expression_synthesizer_v1.py'
OUT=ROOT/'yado_mathematical_reasoning_fresh_admission_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_MATHEMATICAL_REASONING_TRANSFER_FRESH_ADMISSION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('MATH_CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('MATH_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

sp=importlib.util.spec_from_file_location('semantic_expression_synthesizer_fresh',SRC)
mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
Syn=mod.SemanticExpressionSynthesizerV1

train_pts=[(-4,3),(-2,-5),(0,7),(1,-3),(3,2),(6,-1),(8,4)]
blind_pts=[(-7,2),(-3,-8),(2,9),(4,-5),(5,6),(10,-2),(12,7)]
tasks=[
 ('F1_SUM_SQUARE',lambda x,y:(x+y)*(x+y)),
 ('F2_FACTORED_X',lambda x,y:x*(x-y)),
 ('F3_SCALED_PRODUCT',lambda x,y:2*x*y+3),
 ('F4_QUADRATIC_LINEAR',lambda x,y:x*x+x+y),
 ('F5_LINEAR_MIX',lambda x,y:3*y+x),
 ('F6_FACTORED_Y',lambda x,y:y*(x-2)),
]

def run_task(tid,fn,max_ops=3):
    tr=[{'x':x,'y':y,'expected':fn(x,y)} for x,y in train_pts]
    res=Syn.synthesize(tr,max_ops=max_ops,max_states_per_level=30000)
    blind=[]
    if res['expression'] is not None:
        for x,y in blind_pts:
            got=Syn.predict(res,x,y);exp=fn(x,y)
            blind.append({'x':x,'y':y,'expected':exp,'got':got,'ok':got==exp})
    return {'id':tid,'expression':Syn.render(res['expression']) if res['expression'] is not None else None,
            'ops':res['ops'],'states':res['states'],'blind_pass':bool(blind) and all(z['ok'] for z in blind),'blind':blind}

rows=[run_task(*t) for t in tasks]
score=sum(x['blind_pass'] for x in rows)/len(rows)

# Unseen 3-op targets should depend on the admitted depth.
ablate=[]
for tid,fn in tasks[:4]:
    full=run_task(tid,fn,3);shallow=run_task(tid,fn,1)
    ablate.append({'id':tid,'full_found':full['expression'] is not None,'shallow_found':shallow['expression'] is not None})
causal=sum(x['full_found'] and not x['shallow_found'] for x in ablate)>=2

# Explicit bounded-withhold target needs >3 operations in this grammar.
hard_fn=lambda x,y:x*x+y*y+3
hard_train=[{'x':x,'y':y,'expected':hard_fn(x,y)} for x,y in train_pts]
hard=Syn.synthesize(hard_train,max_ops=3,max_states_per_level=30000)
bounded_withhold=hard['expression'] is None

checks={
 'fresh_hidden_accuracy':score>=.83,
 'causal_depth_dependence':causal,
 'bounded_withhold_beyond_depth':bounded_withhold,
 'state_budget_respected':all(max(x['states'])<=30000 for x in rows),
 'source_unchanged':fsha(SRC)==meta['candidate_source_sha256'],
 'canonical_head_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='REAL_MATHEMATICAL_REASONING_CANONICAL_INTEGRATION_V1' if passed else 'REAL_MATHEMATICAL_REASONING_SEARCH_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.mathematical_reasoning_fresh_admission.v1',
 'status':'PASS_MATHEMATICAL_REASONING_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_MATHEMATICAL_REASONING_FRESH_ADMISSION_V1',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'fresh_score':score,'fresh_tasks':rows,'ablation':ablate,
 'bounded_withhold':{'target':'x*x+y*y+3','found':hard['expression'] is not None,'states':hard['states']},
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'FRESH ADMISSION OF BOUNDED SEMANTIC-SIGNATURE EXPRESSION SYNTHESIS. PASS IS NOT GENERAL THEOREM PROVING.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_MATHEMATICAL_REASONING_FRESH_ADMISSION",
 'event_type':'KERNEL_EVOLVED_MATH_FRESH_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_MATHEMATICAL_REASONING_TRANSFER_FRESH_ADMISSION_V1',
 'effect':f"SEMANTIC_EXPRESSION_FRESH_ADMISSION; SCORE={score}; BOUNDED_WITHHOLD={bounded_withhold}",
 'source_path':f'receipts/yado-mathematical-reasoning-fresh-admission-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'fresh_score':score,'causal':causal,'bounded_withhold':bounded_withhold,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('MATH_FRESH_ADMISSION_WITHHELD')
