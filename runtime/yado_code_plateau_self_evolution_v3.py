from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys,importlib.util

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
FAILED=REPO/'receipts'/'yado-code-plateau-self-evolution-v2-run-33490131807.json'
V4SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_structural_program_repair_v4.py'
EXP=REPO/'experience'/'yado-external-agent-systems-learning-v1.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'evidence_guided_structural_program_repair_v5.py'
CAND_META=CAND_DIR/'evidence_guided_structural_program_repair_v5.json'
OUT=ROOT/'yado_code_plateau_self_evolution_v3_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE);failed=load(FAILED);experience=load(EXP)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['CODE_PLATEAU_SELF_EVOLUTION_V3']:raise RuntimeError('UNEXPECTED_FRONTIER')
if failed.get('status')!='WITHHOLD_CODE_PLATEAU_SELF_EVOLUTION_V2':raise RuntimeError('EXPECTED_PRIOR_WITHHOLD')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

sp=importlib.util.spec_from_file_location('_v4_shadow',V4SRC)
m4=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m4;sp.loader.exec_module(m4)
V4=m4.BoundedStructuralProgramRepairV4
V3=BoundedCompositionalProgramRepairV3

candidate_source=r'''from __future__ import annotations
import ast,copy
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3

class EvidenceGuidedStructuralProgramRepairV5:
    COMPONENT_ID="ALG-G2-EVIDENCE-GUIDED-STRUCTURAL-PROGRAM-REPAIR-V5"
    BASE=BoundedCompositionalProgramRepairV3
    MAX_EDIT_DEPTH=2
    MAX_CANDIDATES=24000
    MAX_STRUCTURAL_CANDIDATES=12000
    MAX_BRANCH_EXPRESSIONS=64

    @classmethod
    def execute(cls,source,function_name,args):
        return cls.BASE.execute(source,function_name,args)

    @classmethod
    def _passes(cls,source,function_name,examples):
        return cls.BASE._passes(source,function_name,examples)

    @classmethod
    def _const_pool(cls,tree,examples):
        vals=set(cls.BASE._const_pool(tree,examples));vals.update({-4,-3,-2,-1,0,1,2,3,4,5})
        return tuple(sorted(vals,key=lambda x:(abs(x),x)))[:16]

    @staticmethod
    def _emit(tree,expr):
        t=copy.deepcopy(tree)
        ret=next(n for n in ast.walk(t) if isinstance(n,ast.Return) and n.value is not None)
        ret.value=copy.deepcopy(expr);ast.fix_missing_locations(t)
        BoundedCompositionalProgramRepairV3._validate(t)
        return ast.unparse(t)+"\n"

    @classmethod
    def _expressions(cls,base,pool):
        out=[copy.deepcopy(base),ast.Call(func=ast.Name(id="abs",ctx=ast.Load()),args=[copy.deepcopy(base)],keywords=[])]
        for k in pool:
            out.extend([
              ast.BinOp(left=copy.deepcopy(base),op=ast.Mult(),right=ast.Constant(k)),
              ast.BinOp(left=copy.deepcopy(base),op=ast.Add(),right=ast.Constant(k)),
              ast.BinOp(left=copy.deepcopy(base),op=ast.Sub(),right=ast.Constant(k)),
              ast.Call(func=ast.Name(id="max",ctx=ast.Load()),args=[copy.deepcopy(base),ast.Constant(k)],keywords=[]),
              ast.Call(func=ast.Name(id="min",ctx=ast.Load()),args=[copy.deepcopy(base),ast.Constant(k)],keywords=[]),
            ])
        uniq=[];seen=set()
        for e in out:
            d=ast.dump(e)
            if d not in seen:seen.add(d);uniq.append(e)
        return uniq[:cls.MAX_BRANCH_EXPRESSIONS]

    @classmethod
    def _test_value(cls,tree,function_name,test,args):
        src=cls._emit(tree,test)
        return bool(cls.execute(src,function_name,args))

    @classmethod
    def _expr_fits_subset(cls,tree,function_name,expr,examples):
        src=cls._emit(tree,expr)
        for args,expected in examples:
            try:
                if cls.execute(src,function_name,args)!=expected:return False
            except Exception:return False
        return True

    @classmethod
    def _guided_structural_candidates(cls,source,function_name,examples):
        tree=ast.parse(source);fname=cls.BASE._validate(tree)
        if fname!=function_name:raise ValueError("FUNCTION_NAME_MISMATCH")
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        returns=[n for n in ast.walk(func) if isinstance(n,ast.Return) and n.value is not None]
        if len(returns)!=1:return
        base=returns[0].value;args=[a.arg for a in func.args.args];pool=cls._const_pool(tree,examples)
        exprs=cls._expressions(base,pool)
        emitted=0;seen=set()

        # Whole-dataset structural arithmetic first.
        for expr in exprs:
            s=cls._emit(tree,expr)
            if s in seen:continue
            seen.add(s);emitted+=1
            if emitted>cls.MAX_STRUCTURAL_CANDIDATES:return
            yield s

        # Evidence-guided conditional decomposition.
        tests=[]
        for name in args:
            for k in pool:
                for op in (ast.Lt(),ast.LtE(),ast.Gt(),ast.GtE(),ast.Eq()):
                    tests.append(ast.Compare(left=ast.Name(id=name,ctx=ast.Load()),ops=[op],comparators=[ast.Constant(k)]))
        for test in tests:
            try:
                yes=[z for z in examples if cls._test_value(tree,function_name,test,z[0])]
                no=[z for z in examples if not cls._test_value(tree,function_name,test,z[0])]
            except Exception:
                continue
            if not yes or not no:continue
            yes_fit=[e for e in exprs if cls._expr_fits_subset(tree,function_name,e,yes)]
            if not yes_fit:continue
            no_fit=[e for e in exprs if cls._expr_fits_subset(tree,function_name,e,no)]
            if not no_fit:continue
            # Prefer simplest exact branch models; no Cartesian brute force.
            for body in yes_fit[:3]:
                for other in no_fit[:3]:
                    cond=ast.IfExp(test=copy.deepcopy(test),body=copy.deepcopy(body),orelse=copy.deepcopy(other))
                    s=cls._emit(tree,cond)
                    if s in seen:continue
                    seen.add(s);emitted+=1
                    if emitted>cls.MAX_STRUCTURAL_CANDIDATES:return
                    yield s

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=None,max_edit_depth=None,enabled=("binop","compare","boolop","constant","structural")):
        max_candidates=min(int(max_candidates or cls.MAX_CANDIDATES),cls.MAX_CANDIDATES)
        max_depth=min(int(max_edit_depth or cls.MAX_EDIT_DEPTH),cls.MAX_EDIT_DEPTH)
        base=cls.BASE.repair(source,function_name,train_examples,max_candidates=max_candidates,max_edit_depth=max_depth,enabled=enabled)
        if base.get("source"):
            out=dict(base);out["repair_mode"]="BASE_COMPOSITIONAL";return out
        tried=int(base.get("tried") or 0)
        for cand in cls._guided_structural_candidates(source,function_name,train_examples):
            tried+=1
            if tried>max_candidates:return {"source":None,"tried":tried-1,"reason":"SEARCH_BUDGET","repair_mode":"GUIDED_STRUCTURAL"}
            if cls._passes(cand,function_name,train_examples):
                return {"source":cand,"tried":tried,"edit_depth":None,"repair_mode":"EVIDENCE_GUIDED_STRUCTURAL"}
        return {"source":None,"tried":tried,"reason":"NO_REPAIR_WITHIN_GUIDED_STRUCTURAL_BUDGET","repair_mode":"GUIDED_STRUCTURAL"}

__all__=["EvidenceGuidedStructuralProgramRepairV5"]
'''
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(candidate_source,encoding='utf-8')
ns={};exec(compile(candidate_source,'<candidate>','exec'),ns);V5=ns['EvidenceGuidedStructuralProgramRepairV5']

def score(cls,src,fn,tr,ho,**kw):
    try:
        r=cls.repair(src,fn,tr,**kw)
        if not r.get('source'):return 0.0,r
        return sum(cls.execute(r['source'],fn,args)==exp for args,exp in ho)/len(ho),r
    except Exception as e:return 0.0,{'error':type(e).__name__}

# Exact failed fresh counterexample from V2.
fb=[((-4,),4),((-1,),1),((0,),0),((1,),1),((2,),6),((5,),15)]
fbh=[((-9,),9),((1,),1),((3,),9),((8,),24)]
# Arithmetic structural regression.
fa=[((1,2),-4),((3,1),8),((-2,3),-20)]
fah=[((7,4),12),((-3,-5),8),((0,6),-24)]
# Base two-edit regression.
t2=[((1,2),6),((2,4),9),((-2,3),4),((0,0),3)]
h2=[((5,6),14),((-3,-4),-4),((0,7),10)]

strategies=[
 {'id':'UNGUIDED_V4','cls':V4,'complexity':.36,'risk':.06,'novelty':.20},
 {'id':'EVIDENCE_GUIDED_V5','cls':V5,'complexity':.38,'risk':.05,'novelty':.92},
]
validation={};tok={}
for i,s in enumerate(strategies):
    fam={}
    fam['FAILED_CONDITIONAL_FRESH'],_=score(s['cls'],'def g(x):\n    return x\n','g',fb,fbh,max_candidates=24000,max_edit_depth=2)
    fam['ARITHMETIC_STRUCTURAL'],_=score(s['cls'],'def g(x,y):\n    return x-y\n','g',fa,fah,max_candidates=24000,max_edit_depth=2)
    fam['TWO_EDIT_REGRESSION'],_=score(s['cls'],'def g(x,y):\n    return x-y+1\n','g',t2,h2,max_candidates=24000,max_edit_depth=2)
    token='opaque_'+h({'code_plateau_v3':i,'head':head['canonical_head_digest']})[:18]
    validation[s['id']]={'families':fam,'score':avg(list(fam.values())),'min_family':min(fam.values()),
                         'token':token,'complexity':s['complexity'],'risk':s['risk'],'novelty':s['novelty']}
    tok[token]=s
sel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()])
selected=tok[sel['selected_token']]

# Fresh transfer: different threshold/factor and reversed branch geometry.
fresh={}
tr1=[((-6,),12),((-2,),4),((0,),0),((2,),2),((3,),3),((4,),16),((7,),28)]
ho1=[((-9,),18),((1,),1),((4,),16),((8,),32)]
fresh['CONDITIONAL_THRESHOLD_FACTOR_FRESH'],r1=score(V5,'def f(x):\n    return x\n','f',tr1,ho1,max_candidates=24000,max_edit_depth=2)
tr2=[((-5,),-15),((-2,),-6),((0,),0),((1,),1),((2,),2),((3,),3)]
ho2=[((-8,),-24),((2,),2),((6,),6)]
fresh['CONDITIONAL_REVERSED_FRESH'],r2=score(V5,'def f(x):\n    return x\n','f',tr2,ho2,max_candidates=24000,max_edit_depth=2)
tr3=[((1,2),15),((3,1),10),((-2,3),5)]
ho3=[((7,4),15),((-3,-5),10),((0,6),30)]
fresh['ARITHMETIC_FACTOR_FRESH'],r3=score(V5,'def f(x,y):\n    return x-y\n','f',tr3,ho3,max_candidates=24000,max_edit_depth=2)
holdout={'families':fresh,'score':avg(list(fresh.values())),'min_family':min(fresh.values())}

old_failed=validation['UNGUIDED_V4']['families']['FAILED_CONDITIONAL_FRESH']
new_fixed=validation['EVIDENCE_GUIDED_V5']['families']['FAILED_CONDITIONAL_FRESH']
causal_gain=new_fixed-old_failed

unsafe_ok=False
try:V5.repair('import os\ndef f(x):\n    return x\n','f',[((1,),1)])
except Exception:unsafe_ok=True
multi_ok=False
try:V5.repair('def f(x):\n    return x\ndef h(x):\n    return x\n','f',[((1,),1)])
except Exception:multi_ok=True

checks={
 'prior_failure_is_search_order_counterexample':failed.get('fresh_validation',{}).get('families',{}).get('CONDITIONAL_FRESH')==0,
 'selected_guided_search':selected['id']=='EVIDENCE_GUIDED_V5',
 'failed_counterexample_repaired':new_fixed>=.99,
 'causal_search_order_gain':causal_gain>=.99,
 'fresh_min_one':holdout['min_family']>=.99,
 'unsafe_rejected':unsafe_ok,'multi_function_rejected':multi_ok,
 'red_capable_learning_used':any(x.get('name')=='RED_CAPABLE_SELF_REPAIR_LOOP' for x in experience.get('hypotheses',[])),
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')
}
passed=all(checks.values());next_cap='CODE_PLATEAU_FRESH_ADMISSION_V3' if passed else 'CODE_PLATEAU_SELF_EVOLUTION_V4'

candidate={'schema':'yado.g2.evidence_guided_structural_program_repair_candidate.v5',
 'component_id':'ALG-G2-EVIDENCE-GUIDED-STRUCTURAL-PROGRAM-REPAIR-V5','selected_strategy':selected['id'],
 'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'causal_gain':causal_gain,
 'compute_contract':{'max_edit_depth':V5.MAX_EDIT_DEPTH,'max_candidates':V5.MAX_CANDIDATES,'max_structural_candidates':V5.MAX_STRUCTURAL_CANDIDATES,
                     'max_branch_expressions':V5.MAX_BRANCH_EXPRESSIONS,'function_scope':'EXACTLY_ONE_FUNCTION'},
 'experience_digest':experience['experience_digest'],'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,
 'parent_head_digest':head['canonical_head_digest'],'canonical_active':False,'promotion_applied':False,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'BOUNDED SINGLE-FUNCTION STRUCTURAL REPAIR WITH EVIDENCE-GUIDED CONDITIONAL DECOMPOSITION. IT NARROWS SEARCH BY FITTING EACH BRANCH ON ITS OWN SUBSET BEFORE COMPOSITION; BUDGET IS NOT INCREASED.'
}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

state['candidate_history'].append({'round':state.get('round',11),'plane':'CODE','candidate_digest':candidate['candidate_digest'],
 'selected_strategy':selected['id'],'fresh_score':holdout['score'],'baseline_score':validation['UNGUIDED_V4']['score'],
 'causal_drop':causal_gain,'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.code_plateau_self_evolution.v3',
 'status':'PASS_CODE_PLATEAU_SELF_EVOLUTION_V3' if passed else 'WITHHOLD_CODE_PLATEAU_SELF_EVOLUTION_V3',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'causal_gain':causal_gain,
 'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CODE_PLATEAU_SELF_EVOLUTION_V3",
 'event_type':'SEARCH_ORDER_COUNTEREXAMPLE_DRIVEN_CODE_SELF_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'CODE_PLATEAU_SELF_EVOLUTION_V3',
 'effect':f"SELECTED={selected['id']}; FRESH={holdout['score']:.6f}; SEARCH_GAIN={causal_gain:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-code-plateau-self-evolution-v3-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'selected_strategy':selected['id'],'validation':validation,'fresh_validation':holdout,
 'causal_gain':causal_gain,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CODE_PLATEAU_SELF_EVOLUTION_V3_WITHHELD')
