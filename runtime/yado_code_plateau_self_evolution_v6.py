from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys,importlib.util

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
FAILED=REPO/'receipts'/'yado-code-plateau-self-evolution-v5-run-33490832111.json'
V7SRC=REPO/'candidates'/'g2-self-evolution'/'induced_branch_structural_program_repair_v7.py'
EXP=REPO/'experience'/'yado-external-agent-systems-learning-v1.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'recursive_partition_structural_program_repair_v8.py'
CAND_META=CAND_DIR/'recursive_partition_structural_program_repair_v8.json'
OUT=ROOT/'yado_code_plateau_self_evolution_v6_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE);failed=load(FAILED);experience=load(EXP)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['CODE_PLATEAU_SELF_EVOLUTION_V6']:raise RuntimeError('UNEXPECTED_FRONTIER')
if failed.get('status')!='WITHHOLD_CODE_PLATEAU_SELF_EVOLUTION_V5':raise RuntimeError('EXPECTED_PRIOR_WITHHOLD')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

sp=importlib.util.spec_from_file_location('_v7_shadow',V7SRC)
m7=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m7;sp.loader.exec_module(m7)
V7=m7.InducedBranchStructuralProgramRepairV7

candidate_source=r'''from __future__ import annotations
import ast,copy
from fractions import Fraction
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3

class RecursivePartitionStructuralProgramRepairV8:
    COMPONENT_ID="ALG-G2-RECURSIVE-PARTITION-STRUCTURAL-PROGRAM-REPAIR-V8"
    BASE=BoundedCompositionalProgramRepairV3
    MAX_EDIT_DEPTH=2
    MAX_CANDIDATES=24000
    BASE_SEARCH_BUDGET=6000
    STRUCTURAL_SEARCH_BUDGET=18000
    MAX_CONDITIONAL_DEPTH=2
    MAX_SPLIT_TESTS=640
    MAX_BRANCH_MODELS=8
    MAX_SEARCH_NODES=4000

    @classmethod
    def execute(cls,source,function_name,args):
        return cls.BASE.execute(source,function_name,args)

    @classmethod
    def _passes(cls,source,function_name,examples):
        return cls.BASE._passes(source,function_name,examples)

    @staticmethod
    def _emit(tree,expr):
        t=copy.deepcopy(tree)
        ret=next(n for n in ast.walk(t) if isinstance(n,ast.Return) and n.value is not None)
        ret.value=copy.deepcopy(expr);ast.fix_missing_locations(t)
        BoundedCompositionalProgramRepairV3._validate(t)
        return ast.unparse(t)+"\n"

    @classmethod
    def _base_values(cls,tree,function_name,base,examples):
        src=cls._emit(tree,base);out=[]
        for args,expected in examples:
            try:out.append((cls.execute(src,function_name,args),expected))
            except Exception:return None
        return out

    @staticmethod
    def _mul(base,k):
        return ast.BinOp(left=copy.deepcopy(base),op=ast.Mult(),right=ast.Constant(k))

    @staticmethod
    def _add(expr,b):
        return ast.BinOp(left=copy.deepcopy(expr),op=ast.Add(),right=ast.Constant(b))

    @classmethod
    def _induce_exprs(cls,tree,function_name,base,examples):
        vals=cls._base_values(tree,function_name,base,examples)
        if vals is None or not vals:return []
        out=[copy.deepcopy(base),ast.Call(func=ast.Name(id="abs",ctx=ast.Load()),args=[copy.deepcopy(base)],keywords=[])]
        ys=[e for _,e in vals]
        if all(y==ys[0] for y in ys):out.append(ast.Constant(ys[0]))
        try:
            diffs=[Fraction(y)-Fraction(x) for x,y in vals]
            if diffs and all(d==diffs[0] for d in diffs) and diffs[0].denominator==1:
                out.append(cls._add(base,int(diffs[0])))
        except Exception:pass
        try:
            ratio=None;ok=True
            for x,y in vals:
                fx,fy=Fraction(x),Fraction(y)
                if fx==0:
                    if fy!=0:ok=False;break
                    continue
                r=fy/fx
                if ratio is None:ratio=r
                elif r!=ratio:ok=False;break
            if ok and ratio is not None and ratio.denominator==1:
                out.append(cls._mul(base,int(ratio)))
        except Exception:pass
        try:
            distinct={}
            for x,y in vals:distinct.setdefault(Fraction(x),Fraction(y))
            if len(distinct)>=2:
                items=list(distinct.items());x1,y1=items[0]
                for x2,y2 in items[1:]:
                    if x2==x1:continue
                    a=(y2-y1)/(x2-x1);b=y1-a*x1
                    if a.denominator==1 and b.denominator==1 and all(Fraction(y)==a*Fraction(x)+b for x,y in vals):
                        e=cls._mul(base,int(a))
                        if int(b)!=0:e=cls._add(e,int(b))
                        out.append(e)
                    break
        except Exception:pass
        uniq=[];seen=set()
        for e in out:
            try:
                s=cls._emit(tree,e)
                if all(cls.execute(s,function_name,args)==expected for args,expected in examples):
                    d=ast.dump(e)
                    if d not in seen:seen.add(d);uniq.append(e)
            except Exception:continue
        return uniq[:cls.MAX_BRANCH_MODELS]

    @classmethod
    def _test_value(cls,tree,function_name,test,args):
        return bool(cls.execute(cls._emit(tree,test),function_name,args))

    @classmethod
    def _tests(cls,func,examples):
        vals={-3,-2,-1,0,1,2,3}
        for args,_ in examples:
            for v in args[:len(func.args.args)]:
                if isinstance(v,int) and not isinstance(v,bool) and abs(v)<=100:
                    vals.update({v,v-1,v+1})
        constants=tuple(sorted(vals,key=lambda z:(abs(z),z)))[:24]
        out=[]
        for name in [a.arg for a in func.args.args]:
            for k in constants:
                for op in (ast.Lt(),ast.LtE(),ast.Gt(),ast.GtE(),ast.Eq()):
                    out.append(ast.Compare(left=ast.Name(id=name,ctx=ast.Load()),ops=[op],comparators=[ast.Constant(k)]))
                    if len(out)>=cls.MAX_SPLIT_TESTS:return out
        return out

    @classmethod
    def _solve_subset(cls,tree,function_name,func,base,examples,depth,counter):
        counter[0]+=1
        if counter[0]>cls.MAX_SEARCH_NODES:return None
        direct=cls._induce_exprs(tree,function_name,base,examples)
        if direct:return direct[0]
        if depth<=0:return None
        for test in cls._tests(func,examples):
            try:
                yes=[z for z in examples if cls._test_value(tree,function_name,test,z[0])]
                no=[z for z in examples if not cls._test_value(tree,function_name,test,z[0])]
            except Exception:continue
            if not yes or not no or len(yes)==len(examples) or len(no)==len(examples):continue
            left=cls._solve_subset(tree,function_name,func,base,yes,depth-1,counter)
            if left is None:continue
            right=cls._solve_subset(tree,function_name,func,base,no,depth-1,counter)
            if right is None:continue
            return ast.IfExp(test=copy.deepcopy(test),body=left,orelse=right)
        return None

    @classmethod
    def _structural_candidate(cls,source,function_name,examples):
        tree=ast.parse(source);fname=cls.BASE._validate(tree)
        if fname!=function_name:raise ValueError("FUNCTION_NAME_MISMATCH")
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        returns=[n for n in ast.walk(func) if isinstance(n,ast.Return) and n.value is not None]
        if len(returns)!=1:return None,0
        counter=[0]
        expr=cls._solve_subset(tree,function_name,func,returns[0].value,examples,cls.MAX_CONDITIONAL_DEPTH,counter)
        if expr is None:return None,counter[0]
        return cls._emit(tree,expr),counter[0]

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=None,max_edit_depth=None,enabled=("binop","compare","boolop","constant","structural")):
        total=min(int(max_candidates or cls.MAX_CANDIDATES),cls.MAX_CANDIDATES)
        depth=min(int(max_edit_depth or cls.MAX_EDIT_DEPTH),cls.MAX_EDIT_DEPTH)
        base_budget=min(cls.BASE_SEARCH_BUDGET,total)
        base=cls.BASE.repair(source,function_name,train_examples,max_candidates=base_budget,max_edit_depth=depth,enabled=enabled)
        if base.get("source"):
            out=dict(base);out["repair_mode"]="BASE_PORTFOLIO";return out
        cand,nodes=cls._structural_candidate(source,function_name,train_examples)
        if nodes>cls.STRUCTURAL_SEARCH_BUDGET:
            return {"source":None,"reason":"STRUCTURAL_SEARCH_BUDGET","search_nodes":nodes,"repair_mode":"RECURSIVE_PARTITION"}
        if cand and cls._passes(cand,function_name,train_examples):
            return {"source":cand,"search_nodes":nodes,"repair_mode":"RECURSIVE_PARTITION","conditional_depth":cls.MAX_CONDITIONAL_DEPTH}
        return {"source":None,"reason":"NO_REPAIR_WITHIN_RECURSIVE_PARTITION_BUDGET","search_nodes":nodes,"repair_mode":"RECURSIVE_PARTITION"}

__all__=["RecursivePartitionStructuralProgramRepairV8"]
'''
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(candidate_source,encoding='utf-8')
ns={};exec(compile(candidate_source,'<candidate>','exec'),ns);V8=ns['RecursivePartitionStructuralProgramRepairV8']

def score(cls,src,fn,tr,ho):
    try:
        r=cls.repair(src,fn,tr,max_candidates=24000,max_edit_depth=2)
        if not r.get('source'):return 0.0,r
        return sum(cls.execute(r['source'],fn,args)==exp for args,exp in ho)/len(ho),r
    except Exception as e:return 0.0,{'error':type(e).__name__}

# Nested counterexample from prior rounds: x<0 -> -2x, 0..3 -> x, >3 -> 4x.
ctr=[((-6,),12),((-2,),4),((0,),0),((2,),2),((3,),3),((4,),16),((7,),28)]
cho=[((-9,),18),((1,),1),((4,),16),((8,),32)]

strategies=[
 {'id':'SINGLE_SPLIT_V7','cls':V7,'complexity':.43,'risk':.05,'novelty':.25},
 {'id':'RECURSIVE_DEPTH2_V8','cls':V8,'complexity':.47,'risk':.06,'novelty':.96},
]
validation={};tok={}
for i,s in enumerate(strategies):
    cscore,cr=score(s['cls'],'def f(x):\n    return x\n','f',ctr,cho)
    # Single conditional regression.
    tr=[((-6,),6),((-2,),2),((0,),0),((1,),1),((2,),10),((5,),25)]
    ho=[((-9,),9),((1,),1),((3,),15),((8,),40)]
    rscore,rr=score(s['cls'],'def f(x):\n    return x\n','f',tr,ho)
    fam={'NESTED_COUNTEREXAMPLE':cscore,'SINGLE_CONDITIONAL_REGRESSION':rscore}
    token='opaque_'+h({'code_plateau_v6':i,'head':head['canonical_head_digest']})[:18]
    validation[s['id']]={'families':fam,'score':avg(list(fam.values())),'min_family':min(fam.values()),
                         'details':{'nested':cr,'single':rr},'token':token,'complexity':s['complexity'],'risk':s['risk'],'novelty':s['novelty']}
    tok[token]=s
sel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()])
selected=tok[sel['selected_token']]

fresh={}
# Three regimes: x<0 -> 3x, 0..2 -> x+1, >2 -> 5x
f1=[((-5,),-15),((-2,),-6),((0,),1),((1,),2),((2,),3),((3,),15),((6,),30)]
h1=[((-8,),-24),((0,),1),((2,),3),((4,),20),((9,),45)]
fresh['NESTED_THREE_REGIME_A'],_=score(V8,'def g(x):\n    return x\n','g',f1,h1)
# Three regimes: x<-2 -> abs(x), -2..1 -> 2x, >1 -> 4x+1
f2=[((-6,),6),((-3,),3),((-2,),-4),((0,),0),((1,),2),((2,),9),((5,),21)]
h2=[((-8,),8),((-1,),-2),((1,),2),((3,),13),((7,),29)]
fresh['NESTED_THREE_REGIME_B'],_=score(V8,'def g(x):\n    return x\n','g',f2,h2)
# Affine whole-set regression.
f3=[((-3,),-7),((0,),2),((2,),8),((5,),17)]
h3=[((-7,),-19),((1,),5),((9,),29)]
fresh['AFFINE_REGRESSION'],_=score(V8,'def g(x):\n    return x\n','g',f3,h3)
# Two-edit regression.
f4=[((1,2),6),((2,4),9),((-2,3),4),((0,0),3)]
h4=[((5,6),14),((-3,-4),-4),((0,7),10)]
fresh['TWO_EDIT_REGRESSION'],_=score(V8,'def g(x,y):\n    return x-y+1\n','g',f4,h4)
holdout={'families':fresh,'score':avg(list(fresh.values())),'min_family':min(fresh.values())}

old=validation['SINGLE_SPLIT_V7']['families']['NESTED_COUNTEREXAMPLE']
new=validation['RECURSIVE_DEPTH2_V8']['families']['NESTED_COUNTEREXAMPLE']
causal_gain=new-old

unsafe_ok=False
try:V8.repair('import os\ndef f(x):\n    return x\n','f',[((1,),1)])
except Exception:unsafe_ok=True
multi_ok=False
try:V8.repair('def f(x):\n    return x\ndef h(x):\n    return x\n','f',[((1,),1)])
except Exception:multi_ok=True

checks={
 'selected_recursive_partition':selected['id']=='RECURSIVE_DEPTH2_V8',
 'nested_counterexample_repaired':new>=.99,
 'causal_nested_gain':causal_gain>=.99,
 'fresh_min_one':holdout['min_family']>=.99,
 'total_budget_not_increased':V8.MAX_CANDIDATES==24000,
 'bounded_conditional_depth':V8.MAX_CONDITIONAL_DEPTH==2,
 'unsafe_rejected':unsafe_ok,'multi_function_rejected':multi_ok,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')
}
passed=all(checks.values());next_cap='CODE_PLATEAU_FRESH_ADMISSION_V6' if passed else 'CODE_PLATEAU_SELF_EVOLUTION_V7'

candidate={'schema':'yado.g2.recursive_partition_structural_program_repair_candidate.v8',
 'component_id':'ALG-G2-RECURSIVE-PARTITION-STRUCTURAL-PROGRAM-REPAIR-V8','selected_strategy':selected['id'],
 'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'causal_gain':causal_gain,
 'compute_contract':{'max_candidates':V8.MAX_CANDIDATES,'base_search_budget':V8.BASE_SEARCH_BUDGET,
                     'structural_search_budget':V8.STRUCTURAL_SEARCH_BUDGET,'max_conditional_depth':V8.MAX_CONDITIONAL_DEPTH,
                     'max_split_tests':V8.MAX_SPLIT_TESTS,'max_search_nodes':V8.MAX_SEARCH_NODES},
 'experience_digest':experience['experience_digest'],'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,
 'parent_head_digest':head['canonical_head_digest'],'canonical_active':False,'promotion_applied':False,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'FIXED-BUDGET SINGLE-FUNCTION STRUCTURAL REPAIR WITH RECURSIVE EVIDENCE PARTITIONING UP TO CONDITIONAL DEPTH 2. BRANCH MODELS ARE INDUCED FROM SUBSET EVIDENCE; NO MODULE/MULTI-FUNCTION REWRITE.'
}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

state['candidate_history'].append({'round':state.get('round',14),'plane':'CODE','candidate_digest':candidate['candidate_digest'],
 'selected_strategy':selected['id'],'fresh_score':holdout['score'],'baseline_score':validation['SINGLE_SPLIT_V7']['score'],
 'causal_drop':causal_gain,'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.code_plateau_self_evolution.v6',
 'status':'PASS_CODE_PLATEAU_SELF_EVOLUTION_V6' if passed else 'WITHHOLD_CODE_PLATEAU_SELF_EVOLUTION_V6',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'causal_gain':causal_gain,
 'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CODE_PLATEAU_SELF_EVOLUTION_V6",
 'event_type':'RECURSIVE_PARTITION_CODE_SELF_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'CODE_PLATEAU_SELF_EVOLUTION_V6',
 'effect':f"SELECTED={selected['id']}; FRESH={holdout['score']:.6f}; NESTED_GAIN={causal_gain:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-code-plateau-self-evolution-v6-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'selected_strategy':selected['id'],'validation':validation,'fresh_validation':holdout,
 'causal_gain':causal_gain,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CODE_PLATEAU_SELF_EVOLUTION_V6_WITHHELD')
