from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'bounded_program_repair_v2.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_program_repair_v2.py'
OUT=ROOT/'yado_program_execution_native_fresh_admission_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_PROGRAM_EXECUTION_TRANSFER_FRESH_ADMISSION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

sp=importlib.util.spec_from_file_location('bounded_program_repair_fresh',SRC)
mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
Repair=mod.BoundedProgramRepairV1

tasks=[
 {'id':'F1_ODD','family':'compare','fn':'is_odd','src':'def is_odd(n):\n    return n % 2 == 0\n',
  'train':[((1,),True),((2,),False),((-3,),True),((8,),False)],'blind':[((0,),False),((7,),True),((-10,),False),((101,),True)]},
 {'id':'F2_MIN','family':'compare','fn':'min2','src':'def min2(a,b):\n    return a if a > b else b\n',
  'train':[((5,2),2),((1,7),1),((-2,-8),-8)],'blind':[((9,9),9),((-4,3),-4),((100,-1),-1)]},
 {'id':'F3_FLOOR_DEC','family':'binop','fn':'floor_dec','src':'def floor_dec(x,floor):\n    return max(x+1,floor)\n',
  'train':[((5,0),4),((0,0),0),((-2,-5),-3)],'blind':[((9,3),8),((3,3),3),((-8,-10),-9)]},
 {'id':'F4_OUTSIDE','family':'boolop','fn':'outside','src':'def outside(x,lo,hi):\n    return x < lo and x > hi\n',
  'train':[((0,1,10),True),((5,1,10),False),((11,1,10),True)],'blind':[((1,1,10),False),((10,1,10),False),((-9,-5,5),True)]},
 {'id':'F5_ANY_ZERO','family':'compare','fn':'any_zero','src':'def any_zero(xs):\n    return any(x != 0 for x in xs)\n',
  'train':[(([0,2],),True),(([1,2],),False),(([],),False)],'blind':[(([-1,0],),True),(([5],),False),(([0],),True)]},
 {'id':'F6_LEN_AT_LEAST','family':'compare','fn':'enough','src':'def enough(xs):\n    return len(xs) > 2\n',
  'train':[(([1,2],),True),(([1],),False),(([1,2,3],),True)],'blind':[(([],),False),(([9,8],),True),(([1,2,3,4],),True)]},
 {'id':'F7_SHIFT_DOWN','family':'binop','fn':'shift','src':'def shift(x):\n    return x + 2\n',
  'train':[((5,),3),((0,),-2),((-4,),-6)],'blind':[((10,),8),((2,),0),((-9,),-11)]},
 {'id':'F8_NONNEG','family':'compare','fn':'nonnegative','src':'def nonnegative(x):\n    return x > 0\n',
  'train':[((0,),True),((1,),True),((-1,),False)],'blind':[((7,),True),((-8,),False),((0,),True)]},
]
rows=[]
for t in tasks:
    res=Repair.repair(t['src'],t['fn'],t['train'])
    blind=[]
    if res['source']:
        for args,exp in t['blind']:
            try:got=Repair.execute(res['source'],t['fn'],args);ok=got==exp
            except Exception as exc:got=type(exc).__name__;ok=False
            blind.append({'args':args,'expected':exp,'got':got,'ok':ok})
    rows.append({'id':t['id'],'family':t['family'],'found':res['source'] is not None,'candidate_count':res['candidate_count'],
                 'tried':res['tried'],'blind_pass':bool(blind) and all(x['ok'] for x in blind),'blind':blind,'source':res['source']})
score=sum(x['blind_pass'] for x in rows)/len(rows)

# Family ablation on family-specific tasks: removing the nominated family should reduce successful held-out repairs.
ablation=[]
for t in tasks:
    enabled=tuple(x for x in ('binop','compare','boolop','constant') if x!=t['family'])
    res=Repair.repair(t['src'],t['fn'],t['train'],enabled=enabled)
    ok=False
    if res['source']:
        try:ok=all(Repair.execute(res['source'],t['fn'],a)==e for a,e in t['blind'])
        except Exception:ok=False
    ablation.append({'id':t['id'],'removed_family':t['family'],'passes_without_family':ok})
causal=sum(not x['passes_without_family'] for x in ablation)>=4

negative_sources=[
 'import os\ndef f(x):\n    return x\n',
 'def f(x):\n    return x.real\n',
 'def f(x):\n    print(x)\n    return x\n',
 'def f(x):\n    while x:\n        x-=1\n    return x\n',
]
neg=[]
for s in negative_sources:
    try:
        Repair.execute(s,'f',(1,));neg.append(False)
    except Exception:neg.append(True)

checks={
 'fresh_hidden_score':score>=.875,
 'causal_family_ablation':causal,
 'negative_safety_rejection':all(neg),
 'bounded_candidate_budget':all(x['tried']<=10000 for x in rows),
 'source_unchanged':fsha(SRC)==meta['candidate_source_sha256'],
 'canonical_head_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='REAL_PROGRAM_EXECUTION_TRANSFER_CANONICAL_INTEGRATION_V1' if passed else 'REAL_PROGRAM_EXECUTION_TRANSFER_NATIVE_EVOLUTION_V3'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.program_execution_native_fresh_admission.v1',
 'status':'PASS_PROGRAM_EXECUTION_NATIVE_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_PROGRAM_EXECUTION_NATIVE_FRESH_ADMISSION_V1',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'fresh_score':score,'fresh_tasks':rows,'ablation':ablation,'negative_safety':neg,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':meta['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_PROGRAM_EXECUTION_NATIVE_FRESH_ADMISSION",
 'event_type':'KERNEL_EVOLVED_PROGRAM_REPAIR_FRESH_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_PROGRAM_EXECUTION_TRANSFER_FRESH_ADMISSION_V1',
 'effect':f"PROGRAM_REPAIR_FRESH_ADMISSION; SCORE={score}; CAUSAL={causal}; NEXT={next_cap}",
 'source_path':f'receipts/yado-program-execution-native-fresh-admission-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'fresh_score':score,'causal':causal,'negative_safety':neg,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('PROGRAM_NATIVE_FRESH_ADMISSION_WITHHELD')
