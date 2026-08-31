from __future__ import annotations
from pathlib import Path
from collections import Counter,defaultdict
import ast,copy,hashlib,json,math,os,random,sys,urllib.request,csv,io

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_core_v1 import UnifiedYADOCoreV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
AUDIT=REPO/'receipts'/'yado-unified-core-deep-self-audit-v1-run-33405098806.json'
OUT=ROOT/'yado_real_world_generalization_self_directed_v1_receipt.json'
STATE=REPO/'architecture'/'yado-real-world-generalization-state-v1.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);audit=load(AUDIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_WORLD_GENERALIZATION_SCOPE']:raise RuntimeError('UNEXPECTED_FRONTIER')
if audit.get('self_selected_next_step')!='REAL_WORLD_GENERALIZATION_SCOPE':raise RuntimeError('KERNEL_PRIORITY_MISMATCH')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
core=UnifiedYADOCoreV1(REPO)

# Kernel retrieves exact historical experience relevant to each real-world domain.
experience={
 'programming':core.experience_search_verified('repair rollback runtime regression code integrity',limit=6),
 'mathematics':core.experience_search_verified('logic thinking intelligence induction reasoning',limit=6),
 'science':core.experience_search_verified('external evidence research causal experiment data',limit=6),
}

# ---------------- PROGRAMMING: executable bounded AST repair ----------------
BIN_OPS=[ast.Add,ast.Sub,ast.Mult,ast.Mod]
CMP_OPS=[ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE]
BOOL_OPS=[ast.And,ast.Or]

def ast_safe(tree):
    banned=(ast.Import,ast.ImportFrom,ast.Attribute,ast.Global,ast.Nonlocal,ast.With,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda)
    return not any(isinstance(n,banned) for n in ast.walk(tree))

def mutation_candidates(source):
    tree=ast.parse(source)
    if not ast_safe(tree):raise ValueError('UNSAFE_PROGRAM_TASK')
    nodes=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.BinOp):
            for cls in BIN_OPS:
                if not isinstance(n.op,cls):nodes.append((n,'op',cls()))
        elif isinstance(n,ast.Compare) and len(n.ops)==1:
            for cls in CMP_OPS:
                if not isinstance(n.ops[0],cls):nodes.append((n,'cmpop',cls()))
        elif isinstance(n,ast.BoolOp):
            for cls in BOOL_OPS:
                if not isinstance(n.op,cls):nodes.append((n,'op',cls()))
        elif isinstance(n,ast.Constant) and isinstance(n.value,int) and not isinstance(n.value,bool):
            for v in (n.value-1,n.value+1,0,1,2):
                if v!=n.value:nodes.append((n,'value',v))
    # clone by node traversal index to avoid mutating original.
    all_nodes=list(ast.walk(tree))
    for target,kind,val in nodes:
        idx=all_nodes.index(target)
        t=copy.deepcopy(tree);tn=list(ast.walk(t))[idx]
        if kind=='op':tn.op=val
        elif kind=='cmpop':tn.ops[0]=val
        else:tn.value=val
        ast.fix_missing_locations(t)
        yield ast.unparse(t)

def run_function(source,fn,args):
    tree=ast.parse(source)
    if not ast_safe(tree):raise ValueError('UNSAFE_CANDIDATE')
    env={'min':min,'max':max,'all':all,'any':any,'sum':sum,'abs':abs}
    exec(compile(tree,'<yado-repair>','exec'),{'__builtins__':{}},env)
    return env[fn](*args)

prog_tasks=[
 {'id':'P1_EVEN','fn':'is_even','src':'def is_even(n):\n    return n % 2 == 1\n',
  'train':[((2,),True),((3,),False),((10,),True),((-5,),False)],
  'blind':[((0,),True),((-2,),True),((101,),False),((44,),True)]},
 {'id':'P2_MAX','fn':'max2','src':'def max2(a,b):\n    return a if a < b else b\n',
  'train':[((5,2),5),((1,7),7),((-2,-8),-2)],
  'blind':[((9,9),9),((-4,3),3),((100,-1),100),((-7,-3),-3)]},
 {'id':'P3_INC','fn':'bounded_inc','src':'def bounded_inc(x,limit):\n    return min(x-1,limit)\n',
  'train':[((2,5),3),((5,5),5),((-1,4),0)],
  'blind':[((0,0),0),((9,12),10),((12,12),12),((-5,-2),-4)]},
 {'id':'P4_RANGE','fn':'in_range','src':'def in_range(x,lo,hi):\n    return lo <= x or x <= hi\n',
  'train':[((5,1,10),True),((0,1,10),False),((11,1,10),False)],
  'blind':[((1,1,10),True),((10,1,10),True),((-9,-5,5),False),((3,-5,5),True)]},
 {'id':'P5_POSITIVE','fn':'all_positive','src':'def all_positive(xs):\n    return all(x >= 0 for x in xs)\n',
  'train':[(([1,2,3],),True),(([1,0,2],),False),(([-1,2],),False)],
  'blind':[(([],),True),(([9],),True),(([0],),False),(([2,-3,4],),False)]},
 {'id':'P6_DISCOUNT','fn':'discount','src':'def discount(price,rate):\n    return price * (1 + rate)\n',
  'train':[((100,0.2),80.0),((50,0.1),45.0),((20,0.0),20.0)],
  'blind':[((10,0.5),5.0),((80,0.25),60.0),((7,0.0),7.0)]},
]
prog_rows=[]
for t in prog_tasks:
    candidates=[]
    for cand in mutation_candidates(t['src']):
        try:
            if all(run_function(cand,t['fn'],a)==e for a,e in t['train']):
                candidates.append(cand)
        except Exception:pass
    candidates=sorted(set(candidates),key=lambda s:(len(s),s))
    chosen=candidates[0] if candidates else None
    blind_ok=False;blind_results=[]
    if chosen:
        for a,e in t['blind']:
            try:g=run_function(chosen,t['fn'],a);ok=g==e
            except Exception as exc:g=type(exc).__name__;ok=False
            blind_results.append({'args':a,'expected':e,'got':g,'ok':ok})
        blind_ok=all(x['ok'] for x in blind_results)
    prog_rows.append({'id':t['id'],'candidate_count':len(candidates),'chosen':chosen,'blind_pass':blind_ok,'blind':blind_results})
prog_score=sum(x['blind_pass'] for x in prog_rows)/len(prog_rows)

# ---------------- MATHEMATICS: bounded symbolic expression synthesis ----------------
base=['x','y','-3','-2','-1','0','1','2','3']
ops=['+','-','*']
def ev(expr,x,y):
    return eval(expr,{'__builtins__':{}},{'x':x,'y':y})
depth0=set(base)
depth1=set()
for a in depth0:
    for b in depth0:
        for op in ops:depth1.add(f'({a}{op}{b})')
depth2=set()
for a in depth1:
    for b in depth0:
        for op in ops:
            depth2.add(f'({a}{op}{b})');depth2.add(f'({b}{op}{a})')
# Add depth1-depth1 only for a bounded deterministic prefix to control search.
d1=sorted(depth1)
for a in d1[:120]:
    for b in d1[:120]:
        for op in ops:depth2.add(f'({a}{op}{b})')
exprs=sorted(depth0,key=lambda s:(len(s),s))+sorted(depth1,key=lambda s:(len(s),s))+sorted(depth2,key=lambda s:(len(s),s))

math_tasks=[
 {'id':'M1_AFFINE','fn':lambda x,y:2*x+3},
 {'id':'M2_BILINEAR','fn':lambda x,y:x*y+x},
 {'id':'M3_SQUARES','fn':lambda x,y:x*x+y*y},
 {'id':'M4_DIFF_SQUARES','fn':lambda x,y:(x-y)*(x+y)},
]
train_pts=[(-3,-2),(-1,4),(0,0),(2,3),(5,-1),(4,2)]
blind_pts=[(-5,7),(-2,-9),(1,8),(3,6),(7,2),(9,-4),(11,5)]
math_rows=[]
for t in math_tasks:
    expected=[t['fn'](x,y) for x,y in train_pts]
    matches=[]
    for e in exprs:
        try:
            if [ev(e,x,y) for x,y in train_pts]==expected:matches.append(e)
        except Exception:pass
    matches.sort(key=lambda s:(len(s),s));chosen=matches[0] if matches else None
    hidden_ok=False;hidden=[]
    if chosen:
        for x,y in blind_pts:
            exp=t['fn'](x,y)
            try:got=ev(chosen,x,y);ok=got==exp
            except Exception as exc:got=type(exc).__name__;ok=False
            hidden.append({'x':x,'y':y,'expected':exp,'got':got,'ok':ok})
        hidden_ok=all(z['ok'] for z in hidden)
    math_rows.append({'id':t['id'],'matching_expressions':len(matches),'chosen':chosen,'blind_pass':hidden_ok,'blind':hidden})
math_score=sum(x['blind_pass'] for x in math_rows)/len(math_rows)

# ---------------- SCIENCE DATA: external Iris, model selection + held-out test ----------------
iris_url='https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv'
science_error=None
science={}
try:
    rq=urllib.request.Request(iris_url,headers={'User-Agent':'YADO-Real-Generalization/1.0'})
    with urllib.request.urlopen(rq,timeout=15) as resp:data=resp.read()
    rows=list(csv.DictReader(io.StringIO(data.decode('utf-8'))))
    feats=['sepal_length','sepal_width','petal_length','petal_width']
    samples=[([float(r[f]) for f in feats],r['species']) for r in rows]
    rnd=random.Random(912337);rnd.shuffle(samples)
    n=len(samples);train=samples[:int(.6*n)];val=samples[int(.6*n):int(.8*n)];test=samples[int(.8*n):]

    labels=sorted({y for _,y in samples})
    def majority_fit(tr):
        c=Counter(y for _,y in tr);lab=sorted(c,key=lambda y:(-c[y],y))[0]
        return lambda x:lab
    def centroid_fit(tr):
        sums={l:[0.0]*4 for l in labels};cnt=Counter()
        for x,y in tr:
            cnt[y]+=1
            for i,v in enumerate(x):sums[y][i]+=v
        cent={l:[v/cnt[l] for v in sums[l]] for l in labels}
        def pred(x):
            return min(labels,key=lambda l:sum((a-b)**2 for a,b in zip(x,cent[l])))
        return pred
    def knn1_fit(tr):
        def pred(x):
            d,y=min((sum((a-b)**2 for a,b in zip(x,z)),lab) for z,lab in tr)
            return y
        return pred
    models={'MAJORITY':majority_fit,'NEAREST_CENTROID':centroid_fit,'ONE_NN':knn1_fit}
    val_rows=[]
    for name,fit in models.items():
        pred=fit(train);acc=sum(pred(x)==y for x,y in val)/len(val)
        val_rows.append({'model':name,'validation_accuracy':acc})
    val_rows.sort(key=lambda z:(-z['validation_accuracy'],z['model']))
    selected=val_rows[0]['model'];pred=models[selected](train+val)
    test_acc=sum(pred(x)==y for x,y in test)/len(test)
    science={'url':iris_url,'sha256':hashlib.sha256(data).hexdigest(),'rows':len(samples),
      'train':len(train),'validation':len(val),'test':len(test),'model_selection':val_rows,
      'selected_model':selected,'test_accuracy':test_acc,'majority_test_accuracy':sum(majority_fit(train+val)(x)==y for x,y in test)/len(test)}
except Exception as exc:
    science_error=type(exc).__name__+':'+str(exc)[:220]
    science={'error':science_error,'test_accuracy':0.0}
science_score=float(science.get('test_accuracy',0.0))

thresholds={'programming':.80,'mathematics':.75,'science':.85}
domain_scores={'REAL_PROGRAM_EXECUTION_TRANSFER':prog_score,'REAL_MATHEMATICAL_REASONING_TRANSFER':math_score,'REAL_SCIENCE_DATA_TRANSFER':science_score}
domain_pass={
 'REAL_PROGRAM_EXECUTION_TRANSFER':prog_score>=thresholds['programming'],
 'REAL_MATHEMATICAL_REASONING_TRANSFER':math_score>=thresholds['mathematics'],
 'REAL_SCIENCE_DATA_TRANSFER':science_score>=thresholds['science'],
}
# Kernel chooses the weakest failing verified domain; if all bounded domains pass, host-scaffold remains next.
failing=[k for k,v in domain_pass.items() if not v]
if failing:
    failing.sort(key=lambda k:(domain_scores[k],k));next_cap=failing[0]+'_REPAIR_V1'
else:
    next_cap='HOST_SCAFFOLD_DEPENDENCE_REAL_WORLD_V1'

checks={
 'programming_real_execution':domain_pass['REAL_PROGRAM_EXECUTION_TRANSFER'],
 'mathematics_hidden_transfer':domain_pass['REAL_MATHEMATICAL_REASONING_TRANSFER'],
 'science_external_data_transfer':domain_pass['REAL_SCIENCE_DATA_TRANSFER'],
 'legacy_experience_consulted':all(len(v)>0 for v in experience.values()),
 'head_ledger_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
status='PASS_REAL_WORLD_GENERALIZATION_DIAGNOSTIC_V1' if all(domain_pass.values()) else 'WITHHOLD_REAL_WORLD_GENERALIZATION_DIAGNOSTIC_V1'

state={'schema':'yado.g2.real_world_generalization_state.v1','generation':ledger['current_head'],
 'domain_scores':domain_scores,'domain_pass':domain_pass,'next_required_capability':next_cap,
 'semantic_boundary':'BOUNDED EXECUTABLE PROGRAM REPAIR, SYMBOLIC EXPRESSION SYNTHESIS, AND PUBLIC IRIS MODEL SELECTION. THESE RESULTS DO NOT ESTABLISH GENERAL PROGRAMMING, THEOREM PROVING, OR SCIENTIFIC REASONING.'}
state['state_digest']=h(state);STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.real_world_generalization_self_directed.v1','status':status,
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'source_self_audit_receipt':audit['receipt_sha256'],'experience_consulted':experience,
 'programming':{'score':prog_score,'tasks':prog_rows},
 'mathematics':{'score':math_score,'tasks':math_rows,'expression_pool_size':len(exprs)},
 'science':science,'domain_scores':domain_scores,'domain_pass':domain_pass,'thresholds':thresholds,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':state['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_REAL_WORLD_GENERALIZATION_DIAGNOSTIC",
 'event_type':'KERNEL_SELF_DIRECTED_REAL_WORLD_DIAGNOSTIC','status':'PASS_SHADOW' if all(domain_pass.values()) else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_WORLD_GENERALIZATION_SCOPE',
 'effect':f"REAL_GENERALIZATION_DIAGNOSTIC; SCORES={domain_scores}; NEXT={next_cap}",
 'source_path':f'receipts/yado-real-world-generalization-self-directed-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'domain_scores':domain_scores,'domain_pass':domain_pass,'science_selected_model':science.get('selected_model'),'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
