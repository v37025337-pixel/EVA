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
FAILED=REPO/'receipts'/'yado-code-plateau-self-evolution-v4-run-33490582631.json'
V6SRC=REPO/'candidates'/'g2-self-evolution'/'budget_portfolio_structural_program_repair_v6.py'
EXP=REPO/'experience'/'yado-external-agent-systems-learning-v1.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'induced_branch_structural_program_repair_v7.py'
CAND_META=CAND_DIR/'induced_branch_structural_program_repair_v7.json'
OUT=ROOT/'yado_code_plateau_self_evolution_v5_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE);failed=load(FAILED);experience=load(EXP)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['CODE_PLATEAU_SELF_EVOLUTION_V5']:raise RuntimeError('UNEXPECTED_FRONTIER')
if failed.get('status')!='WITHHOLD_CODE_PLATEAU_SELF_EVOLUTION_V4':raise RuntimeError('EXPECTED_PRIOR_WITHHOLD')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

sp=importlib.util.spec_from_file_location('_v6_shadow',V6SRC)
m6=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m6;sp.loader.exec_module(m6)
V6=m6.BudgetPortfolioStructuralProgramRepairV6
V3=BoundedCompositionalProgramRepairV3

candidate_source=r'''from __future__ import annotations
import ast,copy
from fractions import Fraction
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3

class InducedBranchStructuralProgramRepairV7:
    COMPONENT_ID="ALG-G2-INDUCED-BRANCH-STRUCTURAL-PROGRAM-REPAIR-V7"
    BASE=BoundedCompositionalProgramRepairV3
    MAX_EDIT_DEPTH=2
    MAX_CANDIDATES=24000
    BASE_SEARCH_BUDGET=6000
    STRUCTURAL_SEARCH_BUDGET=18000
    MAX_SPLIT_TESTS=640
    MAX_BRANCH_MODELS=8

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
        src=cls._emit(tree,base)
        vals=[]
        for args,expected in examples:
            try:vals.append((cls.execute(src,function_name,args),expected))
            except Exception:return None
        return vals

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

        diffs=[]
        diff_ok=True
        for x,y in vals:
            try:diffs.append(Fraction(y)-Fraction(x))
            except Exception:diff_ok=False;break
        if diff_ok and diffs and all(d==diffs[0] for d in diffs) and diffs[0].denominator==1:
            out.append(cls._add(base,int(diffs[0])))

        ratio=None;ratio_ok=True
        for x,y in vals:
            try:
                fx,fy=Fraction(x),Fraction(y)
            except Exception:ratio_ok=False;break
            if fx==0:
                if fy!=0:ratio_ok=False;break
                continue
            r=fy/fx
            if ratio is None:ratio=r
            elif r!=ratio:ratio_ok=False;break
        if ratio_ok and ratio is not None and ratio.denominator==1:
            out.append(cls._mul(base,int(ratio)))

        distinct={}
        for x,y in vals:
            try:distinct.setdefault(Fraction(x),Fraction(y))
            except Exception:pass
        if len(distinct)>=2:
            items=list(distinct.items())
            x1,y1=items[0]
            for x2,y2 in items[1:]:
                if x2==x1:continue
                a=(y2-y1)/(x2-x1);b=y1-a*x1
                if a.denominator==1 and b.denominator==1 and all(Fraction(y)==a*Fraction(x)+b for x,y in vals):
                    expr=cls._mul(base,int(a))
                    if int(b)!=0:expr=cls._add(expr,int(b))
                    out.append(expr)
                break

        candidates=set(ys+[x for x,_ in vals])
        for c in sorted(candidates,key=lambda z:(abs(z) if isinstance(z,(int,float)) else 999999,str(z)))[:16]:
            if not isinstance(c,int) or isinstance(c,bool):continue
            try:
                if all(y==min(x,c) for x,y in vals):
                    out.append(ast.Call(func=ast.Name(id="min",ctx=ast.Load()),args=[copy.deepcopy(base),ast.Constant(c)],keywords=[]))
                if all(y==max(x,c) for x,y in vals):
                    out.append(ast.Call(func=ast.Name(id="max",ctx=ast.Load()),args=[copy.deepcopy(base),ast.Constant(c)],keywords=[]))
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
    def _split_constants(cls,func,examples):
        vals={-3,-2,-1,0,1,2,3}
        argc=len(func.args.args)
        for args,_ in examples:
            for v in tuple(args)[:argc]:
                if isinstance(v,int) and not isinstance(v,bool) and abs(v)<=100:
                    vals.update({v,v-1,v+1})
        return tuple(sorted(vals,key=lambda z:(abs(z),z)))[:24]

    @classmethod
    def _structural_candidates(cls,source,function_name,examples):
        tree=ast.parse(source);fname=cls.BASE._validate(tree)
        if fname!=function_name:raise ValueError("FUNCTION_NAME_MISMATCH")
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        returns=[n for n in ast.walk(func) if isinstance(n,ast.Return) and n.value is not None]
        if len(returns)!=1:return
        base=returns[0].value
        emitted=0;seen=set()

        for expr in cls._induce_exprs(tree,function_name,base,examples):
            s=cls._emit(tree,expr)
            if s not in seen:
                seen.add(s);emitted+=1;yield s

        tests=[]
        for name in [a.arg for a in func.args.args]:
            for k in cls._split_constants(func,examples):
                for op in (ast.Lt(),ast.LtE(),ast.Gt(),ast.GtE(),ast.Eq()):
                    tests.append(ast.Compare(left=ast.Name(id=name,ctx=ast.Load()),ops=[op],comparators=[ast.Constant(k)]))
                    if len(tests)>=cls.MAX_SPLIT_TESTS:break
                if len(tests)>=cls.MAX_SPLIT_TESTS:break
            if len(tests)>=cls.MAX_SPLIT_TESTS:break

        for test in tests:
            try:
                yes=[z for z in examples if cls._test_value(tree,function_name,test,z[0])]
                no=[z for z in examples if not cls._test_value(tree,function_name,test,z[0])]
            except Exception:continue
            if not yes or not no:continue
            yes_models=cls._induce_exprs(tree,function_name,base,yes)
            if not yes_models:continue
            no_models=cls._induce_exprs(tree,function_name,base,no)
            if not no_models:continue
            for body in yes_models:
                for other in no_models:
                    cond=ast.IfExp(test=copy.deepcopy(test),body=copy.deepcopy(body),orelse=copy.deepcopy(other))
                    s=cls._emit(tree,cond)
                    if s in seen:continue
                    seen.add(s);emitted+=1
                    if emitted>cls.STRUCTURAL_SEARCH_BUDGET:return
                    yield s

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=None,max_edit_depth=None,enabled=("binop","compare","boolop","constant","structural")):
        total=min(int(max_candidates or cls.MAX_CANDIDATES),cls.MAX_CANDIDATES)
        depth=min(int(max_edit_depth or cls.MAX_EDIT_DEPTH),cls.MAX_EDIT_DEPTH)
        base_budget=min(cls.BASE_SEARCH_BUDGET,total)
        base=cls.BASE.repair(source,function_name,train_examples,max_candidates=base_budget,max_edit_depth=depth,enabled=enabled)
        if base.get("source"):
            out=dict(base);out["repair_mode"]="BASE_PORTFOLIO";return out
        remaining=max(0,total-base_budget);tried=0
        for cand in cls._structural_candidates(source,function_name,train_examples):
            tried+=1
            if tried>remaining:return {"source":None,"tried":tried-1,"reason":"STRUCTURAL_SEARCH_BUDGET","repair_mode":"INDUCED_BRANCH"}
            if cls._passes(cand,function_name,train_examples):
                return {"source":cand,"tried":tried,"repair_mode":"INDUCED_BRANCH","edit_depth":None}
        return {"source":None,"tried":tried,"reason":"NO_REPAIR_WITHIN_INDUCED_BRANCH_BUDGET","repair_mode":"INDUCED_BRANCH"}

__all__=["InducedBranchStructuralProgramRepairV7"]
'''
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(candidate_source,encoding='utf-8')
ns={};exec(compile(candidate_source,'<candidate>','exec'),ns);V7=ns['InducedBranchStructuralProgramRepairV7']

def score(cls,src,fn,tr,ho):
    try:
        r=cls.repair(src,fn,tr,max_candidates=24000,max_edit_depth=2)
        if not r.get('source'):return 0.0,r
        return sum(cls.execute(r['source'],fn,args)==exp for args,exp in ho)/len(ho),r
    except Exception as e:return 0.0,{'error':type(e).__name__}

# Prior valid conditional that V6 failed.
ctr=[((-6,),12),((-2,),4),((0,),0),((2,),2),((3,),3),((4,),16),((7,),28)]
cho=[((-9,),18),((1,),1),((4,),16),((8,),32)]

strategies=[
 {'id':'ENUMERATED_BRANCH_V6','cls':V6,'complexity':.40,'risk':.05,'novelty':.25},
 {'id':'INDUCED_BRANCH_V7','cls':V7,'complexity':.43,'risk':.05,'novelty':.95},
]
validation={};tok={}
for i,s in enumerate(strategies):
    cscore,cr=score(s['cls'],'def f(x):\n    return x\n','f',ctr,cho)
    atr=[((1,2),-5),((3,1),10),((-2,3),-25)]
    aho=[((7,4),15),((-3,-5),10),((0,6),-30)]
    ascore,ar=score(s['cls'],'def f(x,y):\n    return x-y\n','f',atr,aho)
    fam={'PRIOR_CONDITIONAL_COUNTEREXAMPLE':cscore,'ARITHMETIC_FACTOR':ascore}
    token='opaque_'+h({'code_plateau_v5':i,'head':head['canonical_head_digest']})[:18]
    validation[s['id']]={'families':fam,'score':avg(list(fam.values())),'min_family':min(fam.values()),
                         'details':{'conditional':cr,'arithmetic':ar},'token':token,
                         'complexity':s['complexity'],'risk':s['risk'],'novelty':s['novelty']}
    tok[token]=s
sel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()])
selected=tok[sel['selected_token']]

fresh={}
# if x <= 1: abs(x), else 5*x
f1=[((-6,),6),((-2,),2),((0,),0),((1,),1),((2,),10),((5,),25)]
h1=[((-9,),9),((1,),1),((3,),15),((8,),40)]
fresh['INDUCED_CONDITIONAL_A'],_=score(V7,'def g(x):\n    return x\n','g',f1,h1)
# if x < 0: 3*x, else x
f2=[((-5,),-15),((-2,),-6),((0,),0),((1,),1),((3,),3),((6,),6)]
h2=[((-8,),-24),((2,),2),((7,),7)]
fresh['INDUCED_CONDITIONAL_B'],_=score(V7,'def g(x):\n    return x\n','g',f2,h2)
# whole-set affine 3*x+2
f3=[((-3,),-7),((0,),2),((2,),8),((5,),17)]
h3=[((-7,),-19),((1,),5),((9,),29)]
fresh['AFFINE_EXPRESSION_FRESH'],_=score(V7,'def g(x):\n    return x\n','g',f3,h3)
# old two-edit regression
f4=[((1,2),6),((2,4),9),((-2,3),4),((0,0),3)]
h4=[((5,6),14),((-3,-4),-4),((0,7),10)]
fresh['TWO_EDIT_REGRESSION'],_=score(V7,'def g(x,y):\n    return x-y+1\n','g',f4,h4)
holdout={'families':fresh,'score':avg(list(fresh.values())),'min_family':min(fresh.values())}

old=validation['ENUMERATED_BRANCH_V6']['families']['PRIOR_CONDITIONAL_COUNTEREXAMPLE']
new=validation['INDUCED_BRANCH_V7']['families']['PRIOR_CONDITIONAL_COUNTEREXAMPLE']
causal_gain=new-old

unsafe_ok=False
try:V7.repair('import os\ndef f(x):\n    return x\n','f',[((1,),1)])
except Exception:unsafe_ok=True
multi_ok=False
try:V7.repair('def f(x):\n    return x\ndef h(x):\n    return x\n','f',[((1,),1)])
except Exception:multi_ok=True

checks={
 'selected_induced_branch':selected['id']=='INDUCED_BRANCH_V7',
 'prior_counterexample_repaired':new>=.99,
 'causal_induction_gain':causal_gain>=.99,
 'fresh_min_one':holdout['min_family']>=.99,
 'total_budget_not_increased':V7.MAX_CANDIDATES==24000,
 'unsafe_rejected':unsafe_ok,'multi_function_rejected':multi_ok,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')
}
passed=all(checks.values());next_cap='CODE_PLATEAU_FRESH_ADMISSION_V5' if passed else 'CODE_PLATEAU_SELF_EVOLUTION_V6'

candidate={'schema':'yado.g2.induced_branch_structural_program_repair_candidate.v7',
 'component_id':'ALG-G2-INDUCED-BRANCH-STRUCTURAL-PROGRAM-REPAIR-V7','selected_strategy':selected['id'],
 'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'causal_gain':causal_gain,
 'compute_contract':{'max_candidates':V7.MAX_CANDIDATES,'base_search_budget':V7.BASE_SEARCH_BUDGET,
                     'structural_search_budget':V7.STRUCTURAL_SEARCH_BUDGET,'max_split_tests':V7.MAX_SPLIT_TESTS,
                     'max_branch_models':V7.MAX_BRANCH_MODELS,'max_edit_depth':V7.MAX_EDIT_DEPTH},
 'experience_digest':experience['experience_digest'],'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,
 'parent_head_digest':head['canonical_head_digest'],'canonical_active':False,'promotion_applied':False,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'FIXED-BUDGET SINGLE-FUNCTION STRUCTURAL REPAIR THAT INDUCES BRANCH EXPRESSIONS FROM SUBSET EVIDENCE (IDENTITY, ABS, CONSTANT, SCALE, OFFSET, INTEGER AFFINE, MIN/MAX) BEFORE CONDITIONAL COMPOSITION.'
}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

state['candidate_history'].append({'round':state.get('round',13),'plane':'CODE','candidate_digest':candidate['candidate_digest'],
 'selected_strategy':selected['id'],'fresh_score':holdout['score'],'baseline_score':validation['ENUMERATED_BRANCH_V6']['score'],
 'causal_drop':causal_gain,'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.code_plateau_self_evolution.v5',
 'status':'PASS_CODE_PLATEAU_SELF_EVOLUTION_V5' if passed else 'WITHHOLD_CODE_PLATEAU_SELF_EVOLUTION_V5',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'causal_gain':causal_gain,
 'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CODE_PLATEAU_SELF_EVOLUTION_V5",
 'event_type':'EVIDENCE_INDUCED_BRANCH_CODE_SELF_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'CODE_PLATEAU_SELF_EVOLUTION_V5',
 'effect':f"SELECTED={selected['id']}; FRESH={holdout['score']:.6f}; INDUCTION_GAIN={causal_gain:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-code-plateau-self-evolution-v5-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'selected_strategy':selected['id'],'validation':validation,'fresh_validation':holdout,
 'causal_gain':causal_gain,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CODE_PLATEAU_SELF_EVOLUTION_V5_WITHHELD')
