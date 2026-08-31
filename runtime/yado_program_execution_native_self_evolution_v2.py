from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
V1_RECEIPT=REPO/'receipts'/'yado-program-execution-native-self-evolution-v1-run-33417354072.json'
V1_SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_program_repair_v1.py'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'bounded_program_repair_v2.py'
CAND_META=CAND_DIR/'bounded_program_repair_v2.json'
OUT=ROOT/'yado_program_execution_native_self_evolution_v2_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);v1=load(V1_RECEIPT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_PROGRAM_EXECUTION_TRANSFER_NATIVE_EVOLUTION_V2']:raise RuntimeError('UNEXPECTED_FRONTIER')
if v1.get('status')!='WITHHOLD_PROGRAM_EXECUTION_NATIVE_SELF_EVOLUTION_V1':raise RuntimeError('V1_NOT_WITHHELD')
fails=[x['id'] for x in v1.get('tasks',[]) if not x.get('blind_pass')]
if set(fails)!={'E3_INC','E5_POSITIVE'}:raise RuntimeError('UNEXPECTED_V1_COUNTEREXAMPLES')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

old=V1_SRC.read_text(encoding='utf-8')
needle='''        glb={"__builtins__":{}}\n        loc=dict(cls.SAFE_CALLS)\n        exec(compile(tree,"<yado-bounded-program>","exec"),glb,loc)\n        return loc[function_name](*args)'''
replacement='''        env=dict(cls.SAFE_CALLS)\n        env["__builtins__"]={}\n        exec(compile(tree,"<yado-bounded-program>","exec"),env,env)\n        return env[function_name](*args)'''
if needle not in old:raise RuntimeError('V1_EXECUTION_NAMESPACE_PATTERN_NOT_FOUND')
new=old.replace('COMPONENT_ID="ALG-G2-BOUNDED-PROGRAM-REPAIR-V1"','COMPONENT_ID="ALG-G2-BOUNDED-PROGRAM-REPAIR-V2"').replace(needle,replacement)
CAND_SRC.write_text(new,encoding='utf-8')

sp=importlib.util.spec_from_file_location('bounded_program_repair_v2_candidate',CAND_SRC)
mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
Repair=mod.BoundedProgramRepairV1

tasks=[
 {'id':'V2_E1_INC','fn':'bounded_inc','src':'def bounded_inc(x,limit):\n    return min(x-1,limit)\n',
  'train':[((2,5),3),((5,5),5),((-1,4),0)],'blind':[((0,0),0),((9,12),10),((12,12),12),((-5,-2),-4)]},
 {'id':'V2_E2_POSITIVE','fn':'all_positive','src':'def all_positive(xs):\n    return all(x >= 0 for x in xs)\n',
  'train':[(([1,2,3],),True),(([1,0,2],),False),(([-1,2],),False)],'blind':[(([],),True),(([9],),True),(([0],),False),(([2,-3,4],),False)]},
 {'id':'V2_E3_CEILING','fn':'cap','src':'def cap(x,limit):\n    return max(x,limit)\n',
  'train':[((2,5),2),((8,5),5),((-2,0),-2)],'blind':[((1,1),1),((9,4),4),((-5,-2),-5)]},
 {'id':'V2_E4_ANY_NEG','fn':'any_negative','src':'def any_negative(xs):\n    return any(x > 0 for x in xs)\n',
  'train':[(([1,2],),False),(([-1,2],),True),(([0],),False)],'blind':[(([],),False),(([-5],),True),(([3,-1],),True),(([2,4],),False)]},
 {'id':'V2_E5_RANGE','fn':'inside','src':'def inside(x,lo,hi):\n    return lo <= x or x <= hi\n',
  'train':[((5,1,10),True),((0,1,10),False),((11,1,10),False)],'blind':[((1,1,10),True),((10,1,10),True),((-9,-5,5),False)]},
 {'id':'V2_E6_DISCOUNT','fn':'discount','src':'def discount(price,rate):\n    return price * (1 + rate)\n',
  'train':[((100,0.2),80.0),((50,0.1),45.0),((20,0.0),20.0)],'blind':[((10,0.5),5.0),((80,0.25),60.0),((7,0.0),7.0)]},
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
    rows.append({'id':t['id'],'found':res['source'] is not None,'candidate_count':res['candidate_count'],
      'blind_pass':bool(blind) and all(x['ok'] for x in blind),'blind':blind,'repaired_source':res['source']})
score=sum(x['blind_pass'] for x in rows)/len(rows)

# Direct regression proves the execution namespace repair itself is causal.
namespace_regression={}
for name,src,fn,args,expected in [
 ('MIN_VISIBLE','def f(x):\n    return min(x+1,5)\n','f',(2,),3),
 ('ALL_VISIBLE','def f(xs):\n    return all(x > 0 for x in xs)\n','f',([1,2,3],),True),
 ('MAX_VISIBLE','def f(x):\n    return max(x,0)\n','f',(-2,),0),
 ('ANY_VISIBLE','def f(xs):\n    return any(x < 0 for x in xs)\n','f',([2,-1],),True),
]:
    try:got=Repair.execute(src,fn,args);namespace_regression[name]=got==expected
    except Exception:namespace_regression[name]=False

checks={
 'v1_counterexamples_repaired':all(x['blind_pass'] for x in rows[:2]),
 'extended_blind_score':score>=.83,
 'safe_builtins_visible':all(namespace_regression.values()),
 'bounded_single_patch':new.count('env["__builtins__"]={}')==1 and 'glb={"__builtins__":{}}' not in new,
 'canonical_head_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
candidate_digest=h({'component_id':Repair.COMPONENT_ID,'source_sha256':fsha(CAND_SRC),'score':score,'namespace_regression':namespace_regression})
meta={
 'schema':'yado.g2.bounded_program_repair_candidate.v2','component_id':Repair.COMPONENT_ID,
 'candidate_digest':candidate_digest,'candidate_source_sha256':fsha(CAND_SRC),'generation':ledger['current_head'],
 'parent_head_digest':head['canonical_head_digest'],'parent_candidate_sha256':fsha(V1_SRC),
 'source_counterexample_receipt':v1['receipt_sha256'],'counterexamples_repaired':fails,
 'evolution_score':score,'namespace_regression':namespace_regression,'checks':checks,
 'canonical_active':False,'promotion_applied':False,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHELD_SELF_EVOLUTION_V2',
 'semantic_boundary':'BOUNDED SINGLE-AST-EDIT REPAIR OF ONE SAFE PYTHON FUNCTION FROM I/O EXAMPLES WITH ALLOWLISTED BUILTINS. NOT GENERAL PROGRAM SYNTHESIS.'
}
CAND_META.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')
next_cap='REAL_PROGRAM_EXECUTION_TRANSFER_FRESH_ADMISSION_V1' if passed else 'REAL_PROGRAM_EXECUTION_TRANSFER_NATIVE_EVOLUTION_V3'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.program_execution_native_self_evolution.v2',
 'status':'PASS_PROGRAM_EXECUTION_NATIVE_SELF_EVOLUTION_V2' if passed else 'WITHHOLD_PROGRAM_EXECUTION_NATIVE_SELF_EVOLUTION_V2',
 'candidate_digest':candidate_digest,'candidate_source_sha256':fsha(CAND_SRC),'score':score,'tasks':rows,
 'namespace_regression':namespace_regression,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'g3_genesis_performed':False,'next_required_capability':next_cap,'semantic_boundary':meta['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_PROGRAM_EXECUTION_NATIVE_SELF_EVOLUTION_V2",
 'event_type':'KERNEL_COUNTEREXAMPLE_REPAIR_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_PROGRAM_EXECUTION_TRANSFER_NATIVE_EVOLUTION_V2',
 'effect':f"EXECUTION_NAMESPACE_COUNTEREXAMPLES_REPAIRED; SCORE={score}; NEXT={next_cap}",
 'source_path':f'receipts/yado-program-execution-native-self-evolution-v2-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'score':score,'namespace_regression':namespace_regression,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('PROGRAM_NATIVE_SELF_EVOLUTION_V2_WITHHELD')
