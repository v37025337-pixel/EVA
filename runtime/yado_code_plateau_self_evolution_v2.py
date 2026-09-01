from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys

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
PROBE=REPO/'receipts'/'yado-g2-lti-code-architectural-ceiling-plateau-probe-v4-run-33489912500.json'
EXP=REPO/'experience'/'yado-external-agent-systems-learning-v1.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'bounded_structural_program_repair_v4.py'
CAND_META=CAND_DIR/'bounded_structural_program_repair_v4.json'
OUT=ROOT/'yado_code_plateau_self_evolution_v2_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE);probe=load(PROBE);experience=load(EXP)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['CODE_PLATEAU_SELF_EVOLUTION_V2']:raise RuntimeError('UNEXPECTED_FRONTIER')
if probe.get('self_selected_plane')!='CODE':raise RuntimeError('CODE_NOT_SELF_SELECTED')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

candidate_source=r'''from __future__ import annotations
import ast,copy
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3

class BoundedStructuralProgramRepairV4:
    COMPONENT_ID="ALG-G2-BOUNDED-STRUCTURAL-PROGRAM-REPAIR-V4"
    BASE=BoundedCompositionalProgramRepairV3
    MAX_EDIT_DEPTH=2
    MAX_CANDIDATES=24000
    MAX_STRUCTURAL_CANDIDATES=12000
    STRUCTURAL_MODES=("arithmetic_wrapper","conditional_expression")

    @classmethod
    def execute(cls,source,function_name,args):
        return cls.BASE.execute(source,function_name,args)

    @classmethod
    def _passes(cls,source,function_name,examples):
        return cls.BASE._passes(source,function_name,examples)

    @staticmethod
    def _copy_expr(expr):
        return copy.deepcopy(expr)

    @classmethod
    def _const_pool(cls,tree,train_examples):
        vals=set(cls.BASE._const_pool(tree,train_examples))
        vals.update({-3,-2,-1,0,1,2,3,4,5})
        return tuple(sorted(vals,key=lambda x:(abs(x),x)))[:14]

    @classmethod
    def _base_transforms(cls,expr,pool,mode_arithmetic=True):
        out=[cls._copy_expr(expr)]
        out.append(ast.Call(func=ast.Name(id="abs",ctx=ast.Load()),args=[cls._copy_expr(expr)],keywords=[]))
        for k in pool:
            if not mode_arithmetic:continue
            out.extend([
              ast.BinOp(left=cls._copy_expr(expr),op=ast.Mult(),right=ast.Constant(k)),
              ast.BinOp(left=cls._copy_expr(expr),op=ast.Add(),right=ast.Constant(k)),
              ast.BinOp(left=cls._copy_expr(expr),op=ast.Sub(),right=ast.Constant(k)),
              ast.Call(func=ast.Name(id="max",ctx=ast.Load()),args=[cls._copy_expr(expr),ast.Constant(k)],keywords=[]),
              ast.Call(func=ast.Name(id="min",ctx=ast.Load()),args=[cls._copy_expr(expr),ast.Constant(k)],keywords=[]),
            ])
        return out

    @classmethod
    def _structural_candidates(cls,source,function_name,train_examples,modes):
        tree=ast.parse(source)
        fname=cls.BASE._validate(tree)
        if fname!=function_name:raise ValueError("FUNCTION_NAME_MISMATCH")
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        returns=[n for n in ast.walk(func) if isinstance(n,ast.Return) and n.value is not None]
        if len(returns)!=1:return
        ret=returns[0]
        args=[a.arg for a in func.args.args]
        pool=cls._const_pool(tree,train_examples)
        arithmetic="arithmetic_wrapper" in modes
        conditional="conditional_expression" in modes
        expressions=cls._base_transforms(ret.value,pool,arithmetic)
        seen=set();count=0

        def emit(expr):
            nonlocal count
            t=copy.deepcopy(tree)
            tret=next(n for n in ast.walk(t) if isinstance(n,ast.Return) and n.value is not None)
            tret.value=expr
            ast.fix_missing_locations(t)
            try:cls.BASE._validate(t)
            except Exception:return None
            s=ast.unparse(t)+"\n"
            if s in seen:return None
            seen.add(s);count+=1
            if count>cls.MAX_STRUCTURAL_CANDIDATES:return "__BUDGET__"
            return s

        for expr in expressions:
            s=emit(copy.deepcopy(expr))
            if s=="__BUDGET__":return
            if s:yield s

        if conditional:
            branch_pool=expressions[:]
            # Keep conditional search bounded around semantically simple transforms.
            if len(branch_pool)>48:branch_pool=branch_pool[:48]
            tests=[]
            for name in args:
                for k in pool:
                    left=ast.Name(id=name,ctx=ast.Load())
                    for op in (ast.Lt(),ast.LtE(),ast.Gt(),ast.GtE(),ast.Eq()):
                        tests.append(ast.Compare(left=copy.deepcopy(left),ops=[op],comparators=[ast.Constant(k)]))
            for test in tests:
                for body in branch_pool:
                    for other in branch_pool:
                        if ast.dump(body)==ast.dump(other):continue
                        s=emit(ast.IfExp(test=copy.deepcopy(test),body=copy.deepcopy(body),orelse=copy.deepcopy(other)))
                        if s=="__BUDGET__":return
                        if s:yield s

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=None,max_edit_depth=None,
               structural_modes=None,enabled=("binop","compare","boolop","constant","structural")):
        max_candidates=min(int(max_candidates or cls.MAX_CANDIDATES),cls.MAX_CANDIDATES)
        max_depth=min(int(max_edit_depth or cls.MAX_EDIT_DEPTH),cls.MAX_EDIT_DEPTH)
        base=cls.BASE.repair(source,function_name,train_examples,max_candidates=max_candidates,max_edit_depth=max_depth,enabled=enabled)
        if base.get("source"):
            base=dict(base);base["repair_mode"]="BASE_COMPOSITIONAL";return base
        modes=tuple(structural_modes or cls.STRUCTURAL_MODES)
        tried=int(base.get("tried") or 0)
        for cand in cls._structural_candidates(source,function_name,train_examples,modes):
            tried+=1
            if tried>max_candidates:
                return {"source":None,"tried":tried-1,"reason":"SEARCH_BUDGET","repair_mode":"STRUCTURAL"}
            if cls._passes(cand,function_name,train_examples):
                return {"source":cand,"tried":tried,"edit_depth":None,"repair_mode":"STRUCTURAL_EXPRESSION"}
        return {"source":None,"tried":tried,"reason":"NO_REPAIR_WITHIN_STRUCTURAL_BUDGET","repair_mode":"STRUCTURAL"}

__all__=["BoundedStructuralProgramRepairV4"]
'''
CAND_DIR.mkdir(parents=True,exist_ok=True)
CAND_SRC.write_text(candidate_source,encoding='utf-8')
ns={}
exec(compile(candidate_source,'<candidate>','exec'),ns)
V4=ns['BoundedStructuralProgramRepairV4'];V3=BoundedCompositionalProgramRepairV3

def score(cls,src,fn,train,hold,**kw):
    try:
        r=cls.repair(src,fn,train,**kw)
        if not r.get('source'):return 0.0,r
        s=sum(cls.execute(r['source'],fn,args)==exp for args,exp in hold)/len(hold)
        return s,r
    except Exception as e:return 0.0,{'error':type(e).__name__}

# Counterexamples from V4 probe.
tri=[((-3,),3),((-1,),1),((0,),0),((2,),4),((5,),10)]
hoi=[((-7,),7),((3,),6),((8,),16)]
mult_tr=[((1,2),9),((2,4),18),((-2,3),3)]
mult_ho=[((5,6),33),((-3,-4),-21)]
counterexamples={
 'CONDITIONAL_EXPRESSION':('def f(x):\n    return x\n','f',tri,hoi),
 'MULT_WRAP':('def f(x,y):\n    return x+y\n','f',mult_tr,mult_ho)
}
# Regression: old V3 two-edit.
two_tr=[((1,2),6),((2,4),9),((-2,3),4),((0,0),3)]
two_ho=[((5,6),14),((-3,-4),-4),((0,7),10)]

strategies=[
 {'id':'BASE_V3','modes':(), 'complexity':.10,'risk':.02,'novelty':.10},
 {'id':'ARITHMETIC_WRAPPER','modes':('arithmetic_wrapper',),'complexity':.20,'risk':.03,'novelty':.50},
 {'id':'CONDITIONAL_ONLY','modes':('conditional_expression',),'complexity':.27,'risk':.05,'novelty':.68},
 {'id':'BOUNDED_STRUCTURAL_GRAMMAR','modes':('arithmetic_wrapper','conditional_expression'),'complexity':.36,'risk':.06,'novelty':.94},
]
validation={};tok={}
for i,s in enumerate(strategies):
    fam={}
    for name,(src,fn,tr,ho) in counterexamples.items():
        if s['id']=='BASE_V3':
            sc,_=score(V3,src,fn,tr,ho,max_candidates=20000,max_edit_depth=2)
        else:
            sc,_=score(V4,src,fn,tr,ho,max_candidates=24000,max_edit_depth=2,structural_modes=s['modes'])
        fam[name]=sc
    reg,_=score(V3 if s['id']=='BASE_V3' else V4,'def f(x,y):\n    return x-y+1\n','f',two_tr,two_ho,max_candidates=24000,max_edit_depth=2,**({} if s['id']=='BASE_V3' else {'structural_modes':s['modes']}))
    fam['TWO_EDIT_REGRESSION']=reg
    token='opaque_'+h({'code_plateau_v2':i,'head':head['canonical_head_digest']})[:18]
    validation[s['id']]={'families':fam,'score':avg(list(fam.values())),'min_family':min(fam.values()),
                         'token':token,'complexity':s['complexity'],'risk':s['risk'],'novelty':s['novelty']}
    tok[token]=s
sel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()])
selected=tok[sel['selected_token']]

# Fresh unseen structural tasks.
fresh={}
# Fresh arithmetic wrapper: 4*(x-y)
fa=[((1,2),-4),((3,1),8),((-2,3),-20)]
fah=[((7,4),12),((-3,-5),8),((0,6),-24)]
fresh['ARITHMETIC_WRAP_FRESH'],ra=score(V4,'def g(x,y):\n    return x-y\n','g',fa,fah,max_candidates=24000,max_edit_depth=2)
# Fresh conditional: x<=1 -> abs(x), else 3*x
fb=[((-4,),4),((-1,),1),((0,),0),((1,),1),((2,),6),((5,),15)]
fbh=[((-9,),9),((1,),1),((3,),9),((8,),24)]
fresh['CONDITIONAL_FRESH'],rb=score(V4,'def g(x):\n    return x\n','g',fb,fbh,max_candidates=24000,max_edit_depth=2)
# Old capability regression.
fresh['TWO_EDIT_FRESH'],rc=score(V4,'def g(x):\n    return x*2-1\n','g',
 [((1,),1),((2,),4),((5,),13),((-2,),-8)],
 [((3,),7),((7,),19),((-4,),-14)],max_candidates=24000,max_edit_depth=2)
holdout={'families':fresh,'score':avg(list(fresh.values())),'min_family':min(fresh.values())}

base_counter={}
for name,(src,fn,tr,ho) in counterexamples.items():
    base_counter[name],_=score(V3,src,fn,tr,ho,max_candidates=20000,max_edit_depth=2)
causal_gain=(sum(validation[selected['id']]['families'][k]-base_counter[k] for k in counterexamples)/len(counterexamples))

# Fail closed on unsafe/multi-function and budget.
unsafe_ok=False
try:V4.repair('import os\ndef f(x):\n    return x\n','f',[((1,),1)])
except Exception:unsafe_ok=True
multi_ok=False
try:V4.repair('def f(x):\n    return x\ndef h(x):\n    return x\n','f',[((1,),1)])
except Exception:multi_ok=True

checks={
 'code_self_selected':probe.get('self_selected_plane')=='CODE',
 'selected_structural_grammar':selected['id']=='BOUNDED_STRUCTURAL_GRAMMAR',
 'probe_counterexamples_repaired':all(validation[selected['id']]['families'][k]>=.99 for k in counterexamples),
 'two_edit_regression_preserved':validation[selected['id']]['families']['TWO_EDIT_REGRESSION']>=.99,
 'fresh_min_one':holdout['min_family']>=.99,
 'causal_gain_large':causal_gain>=.99,
 'unsafe_rejected':unsafe_ok,
 'multi_function_rejected':multi_ok,
 'external_repair_learning_present':any(x.get('name')=='RED_CAPABLE_SELF_REPAIR_LOOP' for x in experience.get('hypotheses',[])),
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')
}
passed=all(checks.values())
next_cap='CODE_PLATEAU_FRESH_ADMISSION_V2' if passed else 'CODE_PLATEAU_SELF_EVOLUTION_V3'

candidate={'schema':'yado.g2.bounded_structural_program_repair_candidate.v4',
 'component_id':'ALG-G2-BOUNDED-STRUCTURAL-PROGRAM-REPAIR-V4',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,
 'baseline_counterexamples':base_counter,'causal_gain':causal_gain,
 'compute_contract':{'max_edit_depth':V4.MAX_EDIT_DEPTH,'max_candidates':V4.MAX_CANDIDATES,'max_structural_candidates':V4.MAX_STRUCTURAL_CANDIDATES,
                     'structural_modes':list(V4.STRUCTURAL_MODES),'function_scope':'EXACTLY_ONE_FUNCTION'},
 'experience_digest':experience['experience_digest'],'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,
 'parent_head_digest':head['canonical_head_digest'],'canonical_active':False,'promotion_applied':False,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'BOUNDED SINGLE-FUNCTION REPAIR THAT ADDS SAFE RETURN-EXPRESSION STRUCTURAL SYNTHESIS (ARITHMETIC WRAPPERS AND CONDITIONAL EXPRESSIONS) ON TOP OF V3. NO LOOPS, IMPORTS, ATTRIBUTES, MULTI-FUNCTION OR MODULE REWRITES.'
}
candidate['candidate_digest']=h(candidate)
CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

state['candidate_history'].append({'round':state.get('round',10),'plane':'CODE','candidate_digest':candidate['candidate_digest'],
 'selected_strategy':selected['id'],'fresh_score':holdout['score'],'baseline_score':avg(list(base_counter.values())),
 'causal_drop':causal_gain,'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['next_required_capability']=next_cap
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.code_plateau_self_evolution.v2',
 'status':'PASS_CODE_PLATEAU_SELF_EVOLUTION_V2' if passed else 'WITHHOLD_CODE_PLATEAU_SELF_EVOLUTION_V2',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,
 'baseline_counterexamples':base_counter,'causal_gain':causal_gain,'candidate_digest':candidate['candidate_digest'],
 'candidate_source_sha256':candidate['candidate_source_sha256'],'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CODE_PLATEAU_SELF_EVOLUTION_V2",
 'event_type':'COUNTEREXAMPLE_DRIVEN_CODE_SELF_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'CODE_PLATEAU_SELF_EVOLUTION_V2',
 'effect':f"SELECTED={selected['id']}; FRESH={holdout['score']:.6f}; CAUSAL_GAIN={causal_gain:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-code-plateau-self-evolution-v2-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'selected_strategy':selected['id'],'validation':validation,'fresh_validation':holdout,
 'baseline_counterexamples':base_counter,'causal_gain':causal_gain,'checks':checks,'next_required_capability':next_cap,
 'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CODE_PLATEAU_SELF_EVOLUTION_V2_WITHHELD')
