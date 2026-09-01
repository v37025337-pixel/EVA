from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys,importlib.util

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_bounded_program_repair_v2 import BoundedProgramRepairV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
PROBE=REPO/'receipts'/'yado-g2-lti-code-architectural-ceiling-plateau-probe-v3-run-33485921544.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'bounded_compositional_program_repair_v3.py'
CAND_META=CAND_DIR/'bounded_compositional_program_repair_v3.json'
OUT=ROOT/'yado_code_plateau_self_evolution_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE);probe=load(PROBE)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['CODE_PLATEAU_SELF_EVOLUTION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if probe.get('self_selected_plane')!='CODE':raise RuntimeError('CODE_NOT_SELF_SELECTED')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

candidate_source=r'''from __future__ import annotations
import ast,copy

class BoundedCompositionalProgramRepairV3:
    COMPONENT_ID="ALG-G2-BOUNDED-COMPOSITIONAL-PROGRAM-REPAIR-V3"
    SAFE_CALLS={"min":min,"max":max,"all":all,"any":any,"sum":sum,"abs":abs,"len":len}
    BIN_OPS=(ast.Add,ast.Sub,ast.Mult,ast.Mod)
    CMP_OPS=(ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE)
    BOOL_OPS=(ast.And,ast.Or)
    MAX_EDIT_DEPTH=2
    MAX_CANDIDATES=20000
    MAX_STRUCTURAL_CONSTANTS=12

    @classmethod
    def _validate(cls,tree):
        banned=(ast.Import,ast.ImportFrom,ast.Attribute,ast.Global,ast.Nonlocal,ast.With,
                ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda,ast.While,ast.For,ast.AsyncFor,
                ast.Try,ast.Raise,ast.Yield,ast.YieldFrom,ast.Await,ast.Delete)
        if any(isinstance(n,banned) for n in ast.walk(tree)):raise ValueError("UNSAFE_PROGRAM")
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        if len(funcs)!=1 or len(tree.body)!=1:raise ValueError("EXACTLY_ONE_FUNCTION_REQUIRED")
        fname=funcs[0].name
        for n in ast.walk(tree):
            if isinstance(n,ast.Call):
                if not isinstance(n.func,ast.Name):raise ValueError("UNSAFE_CALL")
                if n.func.id not in cls.SAFE_CALLS:raise ValueError("CALL_NOT_ALLOWED")
            if isinstance(n,ast.Name) and n.id.startswith("__"):raise ValueError("DUNDER_FORBIDDEN")
        return fname

    @classmethod
    def execute(cls,source,function_name,args):
        tree=ast.parse(source);fname=cls._validate(tree)
        if fname!=function_name:raise ValueError("FUNCTION_NAME_MISMATCH")
        env=dict(cls.SAFE_CALLS);env["__builtins__"]={}
        exec(compile(tree,"<yado-bounded-program-v3>","exec"),env,env)
        return env[function_name](*args)

    @staticmethod
    def _const_pool(tree,train_examples):
        vals={-2,-1,0,1,2,3}
        for n in ast.walk(tree):
            if isinstance(n,ast.Constant) and isinstance(n.value,int) and not isinstance(n.value,bool):
                vals.update({n.value,n.value-1,n.value+1,n.value-2,n.value+2})
        for args,expected in train_examples:
            for x in tuple(args)+(expected,):
                if isinstance(x,int) and not isinstance(x,bool) and abs(x)<=100:
                    vals.add(x)
        return tuple(sorted(vals,key=lambda x:(abs(x),x)))[:BoundedCompositionalProgramRepairV3.MAX_STRUCTURAL_CONSTANTS]

    @classmethod
    def _atomic_mutations(cls,source,train_examples,enable=("binop","compare","boolop","constant","structural")):
        tree=ast.parse(source);cls._validate(tree);nodes=list(ast.walk(tree));pool=cls._const_pool(tree,train_examples)
        edits=[]
        for idx,n in enumerate(nodes):
            if "binop" in enable and isinstance(n,ast.BinOp):
                for opcls in cls.BIN_OPS:
                    if not isinstance(n.op,opcls):edits.append((idx,"op",opcls()))
            if "compare" in enable and isinstance(n,ast.Compare) and len(n.ops)==1:
                for opcls in cls.CMP_OPS:
                    if not isinstance(n.ops[0],opcls):edits.append((idx,"cmp",opcls()))
            if "boolop" in enable and isinstance(n,ast.BoolOp):
                for opcls in cls.BOOL_OPS:
                    if not isinstance(n.op,opcls):edits.append((idx,"op",opcls()))
            if "constant" in enable and isinstance(n,ast.Constant) and isinstance(n.value,int) and not isinstance(n.value,bool):
                for v in pool:
                    if v!=n.value:edits.append((idx,"value",v))
            if "structural" in enable and isinstance(n,ast.Return) and n.value is not None:
                edits.append((idx,"wrap_abs",None))
                for fn in ("min","max"):
                    for v in pool:edits.append((idx,"wrap_call",(fn,v)))
        seen=set()
        for idx,kind,val in edits:
            t=copy.deepcopy(tree);tn=list(ast.walk(t))[idx]
            if kind=="op":tn.op=val
            elif kind=="cmp":tn.ops[0]=val
            elif kind=="value":tn.value=val
            elif kind=="wrap_abs":
                tn.value=ast.Call(func=ast.Name(id="abs",ctx=ast.Load()),args=[tn.value],keywords=[])
            elif kind=="wrap_call":
                fn,v=val
                tn.value=ast.Call(func=ast.Name(id=fn,ctx=ast.Load()),args=[tn.value,ast.Constant(v)],keywords=[])
            ast.fix_missing_locations(t)
            try:cls._validate(t)
            except Exception:continue
            s=ast.unparse(t)+"\n"
            if s not in seen:
                seen.add(s);yield s

    @classmethod
    def _passes(cls,source,function_name,examples):
        for args,expected in examples:
            try:got=cls.execute(source,function_name,args)
            except Exception:return False
            if got!=expected:return False
        return True

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=None,max_edit_depth=None,
               enabled=("binop","compare","boolop","constant","structural")):
        cls._validate(ast.parse(source))
        max_candidates=min(int(max_candidates or cls.MAX_CANDIDATES),cls.MAX_CANDIDATES)
        max_depth=min(int(max_edit_depth or cls.MAX_EDIT_DEPTH),cls.MAX_EDIT_DEPTH)
        if cls._passes(source,function_name,train_examples):
            return {"source":source,"candidate_count":1,"tried":0,"edit_depth":0}
        frontier=[source];seen={source};tried=0;solutions=[]
        for depth in range(1,max_depth+1):
            nxt=[]
            for base in frontier:
                for cand in cls._atomic_mutations(base,train_examples,enable=enabled):
                    if cand in seen:continue
                    seen.add(cand);tried+=1
                    if tried>max_candidates:
                        return {"source":None,"candidate_count":len(solutions),"tried":tried-1,"edit_depth":None,"reason":"SEARCH_BUDGET"}
                    if cls._passes(cand,function_name,train_examples):
                        solutions.append((depth,cand))
                    else:nxt.append(cand)
            if solutions:
                solutions.sort(key=lambda z:(z[0],len(z[1]),z[1]))
                d,s=solutions[0]
                return {"source":s,"candidate_count":len(solutions),"tried":tried,"edit_depth":d}
            frontier=nxt
        return {"source":None,"candidate_count":0,"tried":tried,"edit_depth":None,"reason":"NO_REPAIR_WITHIN_EDIT_BUDGET"}

__all__=["BoundedCompositionalProgramRepairV3"]
'''
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(candidate_source,encoding='utf-8')
ns={};exec(compile(candidate_source,'<candidate>','exec'),ns);V3=ns['BoundedCompositionalProgramRepairV3'];V2=BoundedProgramRepairV1

def score(cls,src,fn,train,hold,**kw):
    try:
        r=cls.repair(src,fn,train,**kw)
        if not r.get('source'):return 0.0,r
        s=sum(cls.execute(r['source'],fn,args)==expected for args,expected in hold)/len(hold)
        return s,r
    except Exception as e:return 0.0,{'error':type(e).__name__}

cases={}
# Original plateau counterexamples.
tr=[((1,),4),((5,),8),((-2,),1)];ho=[((9,),12),((-5,),-2),((0,),3)]
cases['TWO_EDIT_COUNTEREXAMPLE']=('def f(x):\n    return x-1\n','f',tr,ho)
trg=[((-3,),0),((-1,),0),((0,),0),((2,),2),((7,),7)];hog=[((-9,),0),((4,),4),((11,),11)]
cases['STRUCTURAL_GUARD_COUNTEREXAMPLE']=('def f(x):\n    return x\n','f',trg,hog)
# Fresh multi-edit and structural transforms.
tr2=[((1,),1),((2,),4),((5,),13),((-2,),-8)];ho2=[((3,),7),((7,),19),((-4,),-14)]
cases['TWO_EDIT_FRESH']=('def f(x):\n    return x*2-1\n','f',tr2,ho2)
tr3=[((-5,),-2),((-2,),-2),((0,),0),((4,),4),((9,),5)];ho3=[((-9,),-2),((2,),2),((8,),5)]
cases['STRUCTURAL_CLAMP_FRESH']=('def f(x):\n    return x\n','f',tr3,ho3)

strategies=[
 {'id':'BASE_ONE_EDIT','depth':1,'structural':False,'complexity':.10,'risk':.02,'novelty':.10},
 {'id':'DEPTH2_ONLY','depth':2,'structural':False,'complexity':.22,'risk':.04,'novelty':.55},
 {'id':'STRUCTURAL_ONLY','depth':1,'structural':True,'complexity':.24,'risk':.05,'novelty':.62},
 {'id':'DEPTH2_PLUS_STRUCTURAL','depth':2,'structural':True,'complexity':.34,'risk':.06,'novelty':.90},
]
validation={};tok={}
for i,s in enumerate(strategies):
    fam={}
    for name,(src,fn,tr,ho) in cases.items():
        cls=V2 if s['id']=='BASE_ONE_EDIT' else V3
        if cls is V2:
            sc,_=score(cls,src,fn,tr,ho,max_candidates=12000)
        else:
            enable=("binop","compare","boolop","constant","structural") if s['structural'] else ("binop","compare","boolop","constant")
            sc,_=score(cls,src,fn,tr,ho,max_candidates=16000,max_edit_depth=s['depth'],enabled=enable)
        fam[name]=sc
    token='opaque_'+h({'code_plateau':1,'slot':i,'head':head['canonical_head_digest']})[:18]
    validation[s['id']]={'families':fam,'score':avg(list(fam.values())),'min_family':min(fam.values()),
                         'token':token,'complexity':s['complexity'],'risk':s['risk'],'novelty':s['novelty']}
    tok[token]=s
sel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()])
selected=tok[sel['selected_token']]

# Holdout with different code shapes.
fresh={}
fa=[((1,2),5),((2,4),10),((-2,3),2)];fah=[((5,6),17),((-3,-4),-11),((0,7),7)]
fresh['TWO_EDIT_BINARY_FRESH'],r1=score(V3,'def g(x,y):\n    return x-y+1\n','g',fa,fah,max_candidates=20000,max_edit_depth=2)
fb=[((-5,),5),((-2,),2),((0,),0),((4,),4)];fbh=[((-9,),9),((3,),3),((8,),8)]
fresh['STRUCTURAL_ABS_FRESH'],r2=score(V3,'def g(x):\n    return x\n','g',fb,fbh,max_candidates=20000,max_edit_depth=2)
# Regression old easy cases.
fc=[((2,3),5),((8,1),9)];fch=[((4,7),11),((-2,5),3)]
fresh['SINGLE_EDIT_REGRESSION'],_=score(V3,'def g(x,y):\n    return x-y\n','g',fc,fch,max_candidates=20000,max_edit_depth=2)
holdout={'families':fresh,'score':avg(list(fresh.values())),'min_family':min(fresh.values())}

# Safety and budget.
unsafe_ok=False
try:V3.repair('import os\ndef f(x):\n return x\n','f',[((1,),1)])
except Exception:unsafe_ok=True
budget=V3.repair('def f(x):\n    return x-1\n','f',tr,max_candidates=1,max_edit_depth=2)
budget_ok=budget.get('source') is None and budget.get('reason')=='SEARCH_BUDGET'
checks={
 'code_self_selected':probe.get('self_selected_plane')=='CODE',
 'selected_compositional_strategy':selected['id']=='DEPTH2_PLUS_STRUCTURAL',
 'plateau_counterexamples_repaired':validation[selected['id']]['families']['TWO_EDIT_COUNTEREXAMPLE']>=.99 and validation[selected['id']]['families']['STRUCTURAL_GUARD_COUNTEREXAMPLE']>=.99,
 'fresh_min_one':holdout['min_family']>=.99,
 'unsafe_rejected':unsafe_ok,
 'search_budget_fail_closed':budget_ok,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')
}
passed=all(checks.values());next_cap='CODE_PLATEAU_FRESH_ADMISSION_V1' if passed else 'CODE_PLATEAU_SELF_EVOLUTION_V2'
candidate={
 'schema':'yado.g2.bounded_compositional_program_repair_candidate.v3',
 'component_id':'ALG-G2-BOUNDED-COMPOSITIONAL-PROGRAM-REPAIR-V3',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,
 'fresh_validation':holdout,
 'compute_contract':{'max_edit_depth':V3.MAX_EDIT_DEPTH,'max_candidates':V3.MAX_CANDIDATES,'max_structural_constants':V3.MAX_STRUCTURAL_CONSTANTS},
 'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,'parent_head_digest':head['canonical_head_digest'],
 'canonical_active':False,'promotion_applied':False,'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'BOUNDED SAFE SINGLE-FUNCTION PROGRAM REPAIR WITH UP TO TWO COMPOSED AST EDITS AND SAFE RETURN-EXPRESSION WRAPPERS. NOT GENERAL SELF-MODIFYING CODE EXECUTION.'
}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')
state['candidate_history'].append({'round':state.get('round',13),'plane':'CODE','candidate_digest':candidate['candidate_digest'],'selected_strategy':selected['id'],'fresh_score':holdout['score'],'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'});STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.code_plateau_self_evolution.v1','status':'PASS_CODE_PLATEAU_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_CODE_PLATEAU_SELF_EVOLUTION_V1',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,
 'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CODE_PLATEAU_SELF_EVOLUTION_V1",
 'event_type':'FIXED_ARCHITECTURE_CODE_SELF_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'CODE_PLATEAU_SELF_EVOLUTION_V1','effect':f"SELECTED={selected['id']}; FRESH={holdout['score']:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-code-plateau-self-evolution-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'selected_strategy':selected['id'],'validation':validation,'fresh_validation':holdout,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CODE_PLATEAU_SELF_EVOLUTION_V1_WITHHELD')
