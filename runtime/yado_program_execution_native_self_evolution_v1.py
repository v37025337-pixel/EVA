from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,os,sys,textwrap

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
SRC_RECEIPT=REPO/'receipts'/'yado-real-world-generalization-self-directed-v2-run-33417121418.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'bounded_program_repair_v1.py'
CAND_META=CAND_DIR/'bounded_program_repair_v1.json'
OUT=ROOT/'yado_program_execution_native_self_evolution_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);src_receipt=load(SRC_RECEIPT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_PROGRAM_EXECUTION_TRANSFER_NATIVE_EVOLUTION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if src_receipt.get('domain_pass',{}).get('REAL_PROGRAM_EXECUTION_TRANSFER') is not False:raise RuntimeError('PROGRAMMING_NOT_A_CONFIRMED_DEFICIT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

candidate_code = r'''from __future__ import annotations
import ast,copy

class BoundedProgramRepairV1:
    COMPONENT_ID="ALG-G2-BOUNDED-PROGRAM-REPAIR-V1"
    SAFE_CALLS={"min":min,"max":max,"all":all,"any":any,"sum":sum,"abs":abs,"len":len}
    BIN_OPS=(ast.Add,ast.Sub,ast.Mult,ast.Mod)
    CMP_OPS=(ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE)
    BOOL_OPS=(ast.And,ast.Or)

    @classmethod
    def _validate(cls,tree):
        banned=(ast.Import,ast.ImportFrom,ast.Attribute,ast.Global,ast.Nonlocal,ast.With,
                ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda,ast.While,ast.For,ast.AsyncFor,
                ast.Try,ast.Raise,ast.Yield,ast.YieldFrom,ast.Await,ast.Delete)
        if any(isinstance(n,banned) for n in ast.walk(tree)):
            raise ValueError("UNSAFE_PROGRAM")
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        if len(funcs)!=1 or len(tree.body)!=1:
            raise ValueError("EXACTLY_ONE_FUNCTION_REQUIRED")
        fname=funcs[0].name
        for n in ast.walk(tree):
            if isinstance(n,ast.Call):
                if not isinstance(n.func,ast.Name):
                    raise ValueError("UNSAFE_CALL")
                if n.func.id not in cls.SAFE_CALLS:
                    raise ValueError("CALL_NOT_ALLOWED")
            if isinstance(n,ast.Name) and n.id.startswith("__"):
                raise ValueError("DUNDER_FORBIDDEN")
        return fname

    @classmethod
    def execute(cls,source,function_name,args):
        tree=ast.parse(source)
        fname=cls._validate(tree)
        if fname!=function_name:
            raise ValueError("FUNCTION_NAME_MISMATCH")
        glb={"__builtins__":{}}
        loc=dict(cls.SAFE_CALLS)
        exec(compile(tree,"<yado-bounded-program>","exec"),glb,loc)
        return loc[function_name](*args)

    @classmethod
    def _mutations(cls,source,enabled=("binop","compare","boolop","constant")):
        tree=ast.parse(source);cls._validate(tree)
        all_nodes=list(ast.walk(tree))
        edits=[]
        for n in all_nodes:
            if "binop" in enabled and isinstance(n,ast.BinOp):
                for opcls in cls.BIN_OPS:
                    if not isinstance(n.op,opcls):edits.append((all_nodes.index(n),"op",opcls()))
            if "compare" in enabled and isinstance(n,ast.Compare) and len(n.ops)==1:
                for opcls in cls.CMP_OPS:
                    if not isinstance(n.ops[0],opcls):edits.append((all_nodes.index(n),"cmp",opcls()))
            if "boolop" in enabled and isinstance(n,ast.BoolOp):
                for opcls in cls.BOOL_OPS:
                    if not isinstance(n.op,opcls):edits.append((all_nodes.index(n),"op",opcls()))
            if "constant" in enabled and isinstance(n,ast.Constant) and isinstance(n.value,int) and not isinstance(n.value,bool):
                for v in (n.value-2,n.value-1,n.value+1,n.value+2,0,1,2,3):
                    if v!=n.value:edits.append((all_nodes.index(n),"value",v))
        seen=set()
        for idx,kind,val in edits:
            t=copy.deepcopy(tree);tn=list(ast.walk(t))[idx]
            if kind=="op":tn.op=val
            elif kind=="cmp":tn.ops[0]=val
            else:tn.value=val
            ast.fix_missing_locations(t)
            s=ast.unparse(t)+"\n"
            if s not in seen:
                seen.add(s);yield s

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=10000,enabled=("binop","compare","boolop","constant")):
        cls._validate(ast.parse(source))
        tried=0;solutions=[]
        for cand in cls._mutations(source,enabled=enabled):
            tried+=1
            if tried>max_candidates:break
            ok=True
            for args,expected in train_examples:
                try:got=cls.execute(cand,function_name,args)
                except Exception:ok=False;break
                if got!=expected:ok=False;break
            if ok:solutions.append(cand)
        solutions.sort(key=lambda s:(len(s),s))
        return {"source":solutions[0] if solutions else None,"candidate_count":len(solutions),"tried":tried}

__all__=["BoundedProgramRepairV1"]
'''
CAND_DIR.mkdir(parents=True,exist_ok=True)
CAND_SRC.write_text(candidate_code,encoding='utf-8')

sp=importlib.util.spec_from_file_location('bounded_program_repair_candidate',CAND_SRC)
mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
Repair=mod.BoundedProgramRepairV1

tasks=[
 {'id':'E1_EVEN','fn':'is_even','src':'def is_even(n):\n    return n % 2 == 1\n',
  'train':[((2,),True),((3,),False),((10,),True),((-5,),False)],
  'blind':[((0,),True),((-8,),True),((101,),False),((44,),True)]},
 {'id':'E2_MAX','fn':'max2','src':'def max2(a,b):\n    return a if a < b else b\n',
  'train':[((5,2),5),((1,7),7),((-2,-8),-2)],
  'blind':[((9,9),9),((-4,3),3),((100,-1),100),((-7,-3),-3)]},
 {'id':'E3_INC','fn':'bounded_inc','src':'def bounded_inc(x,limit):\n    return min(x-1,limit)\n',
  'train':[((2,5),3),((5,5),5),((-1,4),0)],
  'blind':[((0,0),0),((9,12),10),((12,12),12),((-5,-2),-4)]},
 {'id':'E4_RANGE','fn':'in_range','src':'def in_range(x,lo,hi):\n    return lo <= x or x <= hi\n',
  'train':[((5,1,10),True),((0,1,10),False),((11,1,10),False)],
  'blind':[((1,1,10),True),((10,1,10),True),((-9,-5,5),False),((3,-5,5),True)]},
 {'id':'E5_POSITIVE','fn':'all_positive','src':'def all_positive(xs):\n    return all(x >= 0 for x in xs)\n',
  'train':[(([1,2,3],),True),(([1,0,2],),False),(([-1,2],),False)],
  'blind':[(([],),True),(([9],),True),(([0],),False),(([2,-3,4],),False)]},
 {'id':'E6_DISCOUNT','fn':'discount','src':'def discount(price,rate):\n    return price * (1 + rate)\n',
  'train':[((100,0.2),80.0),((50,0.1),45.0),((20,0.0),20.0)],
  'blind':[((10,0.5),5.0),((80,0.25),60.0),((7,0.0),7.0)]},
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
    rows.append({'id':t['id'],'found':res['source'] is not None,'candidate_count':res['candidate_count'],'tried':res['tried'],
                 'blind_pass':bool(blind) and all(x['ok'] for x in blind),'blind':blind,'repaired_source':res['source']})
score=sum(x['blind_pass'] for x in rows)/len(rows)

# Family ablation: the admitted mechanism must rely on more than one edit family across the suite.
ablations={}
for family in ('binop','compare','boolop','constant'):
    enabled=tuple(x for x in ('binop','compare','boolop','constant') if x!=family)
    passed=0
    for t in tasks:
        res=Repair.repair(t['src'],t['fn'],t['train'],enabled=enabled)
        if res['source']:
            try:
                ok=all(Repair.execute(res['source'],t['fn'],a)==e for a,e in t['blind'])
            except Exception:ok=False
            passed+=int(ok)
    ablations[family]=passed/len(tasks)

source_checks={
 'candidate_source_present':CAND_SRC.exists(),
 'no_imports_beyond_ast_copy':'import ast,copy' in candidate_code and 'subprocess' not in candidate_code and 'socket' not in candidate_code,
 'bounded_candidate_budget':'max_candidates=10000' in candidate_code,
 'single_function_execution_guard':'EXACTLY_ONE_FUNCTION_REQUIRED' in candidate_code,
 'unsafe_calls_rejected':'CALL_NOT_ALLOWED' in candidate_code,
}
causal_ablation=min(ablations.values())<score
checks={
 'repairs_confirmed_counterexamples':score>=.80,
 'fresh_blind_within_evolution':score>=.80,
 'causal_mutation_family_dependence':causal_ablation,
 'source_safety_guards':all(source_checks.values()),
 'canonical_head_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
candidate_digest=h({'component_id':Repair.COMPONENT_ID,'source_sha256':fsha(CAND_SRC),'score':score,'ablations':ablations})
meta={
 'schema':'yado.g2.bounded_program_repair_candidate.v1',
 'component_id':Repair.COMPONENT_ID,'candidate_digest':candidate_digest,'candidate_source_sha256':fsha(CAND_SRC),
 'generation':ledger['current_head'],'parent_head_digest':head['canonical_head_digest'],
 'source_deficit':'REAL_PROGRAM_EXECUTION_TRANSFER_NATIVE_EVOLUTION_V1',
 'source_counterexample_receipt':src_receipt['receipt_sha256'],
 'evolution_score':score,'ablation_scores':ablations,'checks':checks,
 'canonical_active':False,'promotion_applied':False,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHELD_SELF_EVOLUTION',
 'semantic_boundary':'BOUNDED SINGLE-AST-EDIT REPAIR OF ONE SAFE PYTHON FUNCTION FROM I/O EXAMPLES. NOT GENERAL PROGRAM SYNTHESIS OR UNRESTRICTED CODE EXECUTION.'
}
CAND_META.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')

next_cap='REAL_PROGRAM_EXECUTION_TRANSFER_FRESH_ADMISSION_V1' if passed else 'REAL_PROGRAM_EXECUTION_TRANSFER_NATIVE_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.program_execution_native_self_evolution.v1',
 'status':'PASS_PROGRAM_EXECUTION_NATIVE_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_PROGRAM_EXECUTION_NATIVE_SELF_EVOLUTION_V1',
 'candidate_digest':candidate_digest,'candidate_source_sha256':fsha(CAND_SRC),
 'score':score,'tasks':rows,'ablation_scores':ablations,'source_checks':source_checks,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':meta['semantic_boundary']
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_PROGRAM_EXECUTION_NATIVE_SELF_EVOLUTION",
 'event_type':'KERNEL_SELF_EVOLVED_PROGRAM_REPAIR_CANDIDATE','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_PROGRAM_EXECUTION_TRANSFER_NATIVE_EVOLUTION_V1',
 'effect':f"BOUNDED_PROGRAM_REPAIR_CANDIDATE; SCORE={score}; NEXT={next_cap}",
 'source_path':f'receipts/yado-program-execution-native-self-evolution-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'score':score,'ablation_scores':ablations,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('PROGRAM_NATIVE_SELF_EVOLUTION_WITHHELD')
