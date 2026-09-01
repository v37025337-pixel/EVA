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
FAILED=REPO/'receipts'/'yado-code-plateau-self-evolution-v7-run-33491295651.json'
V9SRC=REPO/'candidates'/'g2-self-evolution'/'support_ranked_recursive_program_repair_v9.py'
EXP=REPO/'experience'/'yado-external-agent-systems-learning-v1.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'canonical_split_recursive_program_repair_v10.py'
CAND_META=CAND_DIR/'canonical_split_recursive_program_repair_v10.json'
OUT=ROOT/'yado_code_plateau_self_evolution_v8_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE);failed=load(FAILED);experience=load(EXP)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['CODE_PLATEAU_SELF_EVOLUTION_V8']:raise RuntimeError('UNEXPECTED_FRONTIER')
if failed.get('status')!='WITHHOLD_CODE_PLATEAU_SELF_EVOLUTION_V7':raise RuntimeError('EXPECTED_PRIOR_WITHHOLD')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

# Build V10 as a self-contained evolution of V9: same model induction/ranking,
# only the split generator changes to observed-boundary canonical splits.
v9_source=V9SRC.read_text(encoding='utf-8')
candidate_source=v9_source.replace(
    'class SupportRankedRecursiveProgramRepairV9:',
    'class CanonicalSplitRecursiveProgramRepairV10:'
).replace(
    'COMPONENT_ID="ALG-G2-SUPPORT-RANKED-RECURSIVE-PROGRAM-REPAIR-V9"',
    'COMPONENT_ID="ALG-G2-CANONICAL-SPLIT-RECURSIVE-PROGRAM-REPAIR-V10"'
)
start=candidate_source.index('    @classmethod\n    def _tests')
end=candidate_source.index('    @classmethod\n    def _solve_subset',start)
new_tests='''    @classmethod
    def _tests(cls,func,examples):
        out=[]
        argc=len(func.args.args)
        for pos,name in enumerate([a.arg for a in func.args.args]):
            vals=[]
            for args,_ in examples:
                if pos < len(args):
                    v=args[pos]
                    if isinstance(v,(int,float)) and not isinstance(v,bool):
                        vals.append(v)
            uniq=sorted(set(vals))
            # Canonical numeric partitions: boundary is anchored on an observed
            # value, never invented inside an unseen gap.
            for v in uniq[:-1]:
                out.append(ast.Compare(left=ast.Name(id=name,ctx=ast.Load()),ops=[ast.LtE()],comparators=[ast.Constant(v)]))
                out.append(ast.Compare(left=ast.Name(id=name,ctx=ast.Load()),ops=[ast.Gt()],comparators=[ast.Constant(v)]))
                if len(out)>=cls.MAX_SPLIT_TESTS:return out
        return out

'''
candidate_source=candidate_source[:start]+new_tests+candidate_source[end:]
candidate_source=candidate_source.replace(
    "__all__=['SupportRankedRecursiveProgramRepairV9']",
    "__all__=['CanonicalSplitRecursiveProgramRepairV10']"
)
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(candidate_source,encoding='utf-8')

sp9=importlib.util.spec_from_file_location('_v9_shadow',V9SRC)
m9=importlib.util.module_from_spec(sp9);sys.modules[sp9.name]=m9;sp9.loader.exec_module(m9)
V9=m9.SupportRankedRecursiveProgramRepairV9
ns={};exec(compile(candidate_source,'<candidate>','exec'),ns);V10=ns['CanonicalSplitRecursiveProgramRepairV10']

def score(cls,src,fn,tr,ho):
    try:
        r=cls.repair(src,fn,tr,max_candidates=24000,max_edit_depth=2)
        if not r.get('source'):return 0.0,r
        return sum(cls.execute(r['source'],fn,args)==exp for args,exp in ho)/len(ho),r
    except Exception as e:return 0.0,{'error':type(e).__name__}

# Failed sparse-boundary B from V9.
b=[((-6,),-12),((-3,),-6),((-1,),-1),((0,),0),((2,),2),((3,),10),((5,),16)]
bh=[((-8,),-16),((-2,),-2),((1,),1),((4,),13),((7,),22)]

strategies=[
 {'id':'GAP_SPLITS_V9','cls':V9,'complexity':.49,'risk':.05,'novelty':.25},
 {'id':'OBSERVED_BOUNDARY_V10','cls':V10,'complexity':.50,'risk':.04,'novelty':.96},
]
validation={};tok={}
for i,s in enumerate(strategies):
    sc,detail=score(s['cls'],'def f(x):\n    return x\n','f',b,bh)
    # V9 fixed previous nested B; preserve it.
    tr=[((-6,),6),((-3,),3),((-2,),-4),((0,),0),((1,),2),((2,),9),((5,),21)]
    ho=[((-8,),8),((-1,),-2),((1,),2),((3,),13),((7,),29)]
    reg,rd=score(s['cls'],'def f(x):\n    return x\n','f',tr,ho)
    fam={'FAILED_GAP_BOUNDARY_B':sc,'SUPPORT_RANKING_REGRESSION':reg}
    token='opaque_'+h({'code_plateau_v8':i,'head':head['canonical_head_digest']})[:18]
    validation[s['id']]={'families':fam,'score':avg(list(fam.values())),'min_family':min(fam.values()),
                         'details':{'failed_b':detail,'regression':rd},'token':token,
                         'complexity':s['complexity'],'risk':s['risk'],'novelty':s['novelty']}
    tok[token]=s
sel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()])
selected=tok[sel['selected_token']]

fresh={}
# Gap between -4 and -1: canonical boundary should stay at -4.
a=[((-8,),-16),((-4,),-8),((-1,),-1),((0,),0),((2,),2),((4,),13),((7,),22)]
ah=[((-10,),-20),((-3,),-3),((1,),1),((5,),16),((9,),28)]
fresh['OBSERVED_BOUNDARY_GAP_A'],_=score(V10,'def g(x):\n    return x\n','g',a,ah)
# Gap between 2 and 5 for upper regime.
c=[((-5,),5),((-2,),2),((0,),0),((2,),2),((5,),16),((8,),25)]
ch=[((-9,),9),((1,),1),((3,),3),((6,),19),((10,),31)]
fresh['OBSERVED_BOUNDARY_GAP_B'],_=score(V10,'def g(x):\n    return x\n','g',c,ch)
# Affine and two-edit regressions.
d=[((-3,),-7),((0,),2),((2,),8),((5,),17)]
dh=[((-7,),-19),((1,),5),((9,),29)]
fresh['AFFINE_REGRESSION'],_=score(V10,'def g(x):\n    return x\n','g',d,dh)
e=[((1,2),6),((2,4),9),((-2,3),4),((0,0),3)]
eh=[((5,6),14),((-3,-4),-4),((0,7),10)]
fresh['TWO_EDIT_REGRESSION'],_=score(V10,'def g(x,y):\n    return x-y+1\n','g',e,eh)
holdout={'families':fresh,'score':avg(list(fresh.values())),'min_family':min(fresh.values())}

old=validation['GAP_SPLITS_V9']['families']['FAILED_GAP_BOUNDARY_B']
new=validation['OBSERVED_BOUNDARY_V10']['families']['FAILED_GAP_BOUNDARY_B']
causal_gain=new-old

unsafe_ok=False
try:V10.repair('import os\ndef f(x):\n    return x\n','f',[((1,),1)])
except Exception:unsafe_ok=True
multi_ok=False
try:V10.repair('def f(x):\n    return x\ndef h(x):\n    return x\n','f',[((1,),1)])
except Exception:multi_ok=True

checks={
 'selected_observed_boundary':selected['id']=='OBSERVED_BOUNDARY_V10',
 'failed_gap_repaired':new>=.99,
 'causal_boundary_gain':causal_gain>=.19,
 'fresh_min_one':holdout['min_family']>=.99,
 'total_budget_not_increased':V10.MAX_CANDIDATES==24000,
 'unsafe_rejected':unsafe_ok,'multi_function_rejected':multi_ok,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')
}
passed=all(checks.values());next_cap='CODE_PLATEAU_FRESH_ADMISSION_V8' if passed else 'CODE_PLATEAU_SELF_EVOLUTION_V9'

candidate={'schema':'yado.g2.canonical_split_recursive_program_repair_candidate.v10',
 'component_id':'ALG-G2-CANONICAL-SPLIT-RECURSIVE-PROGRAM-REPAIR-V10','selected_strategy':selected['id'],
 'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'causal_gain':causal_gain,
 'compute_contract':{'max_candidates':V10.MAX_CANDIDATES,'base_search_budget':V10.BASE_SEARCH_BUDGET,
                     'structural_search_budget':V10.STRUCTURAL_SEARCH_BUDGET,'max_conditional_depth':V10.MAX_CONDITIONAL_DEPTH,
                     'max_split_tests':V10.MAX_SPLIT_TESTS,'max_search_nodes':V10.MAX_SEARCH_NODES},
 'experience_digest':experience['experience_digest'],'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,
 'parent_head_digest':head['canonical_head_digest'],'canonical_active':False,'promotion_applied':False,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'FIXED-BUDGET SUPPORT-RANKED RECURSIVE REPAIR WITH NUMERIC SPLITS CANONICALIZED TO OBSERVED BOUNDARIES, AVOIDING UNJUSTIFIED THRESHOLDS INSIDE UNSEEN GAPS.'
}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

state['candidate_history'].append({'round':state.get('round',16),'plane':'CODE','candidate_digest':candidate['candidate_digest'],
 'selected_strategy':selected['id'],'fresh_score':holdout['score'],'baseline_score':validation['GAP_SPLITS_V9']['score'],
 'causal_drop':causal_gain,'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.code_plateau_self_evolution.v8',
 'status':'PASS_CODE_PLATEAU_SELF_EVOLUTION_V8' if passed else 'WITHHOLD_CODE_PLATEAU_SELF_EVOLUTION_V8',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'causal_gain':causal_gain,
 'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CODE_PLATEAU_SELF_EVOLUTION_V8",
 'event_type':'CANONICAL_SPLIT_CODE_SELF_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'CODE_PLATEAU_SELF_EVOLUTION_V8',
 'effect':f"SELECTED={selected['id']}; FRESH={holdout['score']:.6f}; BOUNDARY_GAIN={causal_gain:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-code-plateau-self-evolution-v8-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'selected_strategy':selected['id'],'validation':validation,'fresh_validation':holdout,
 'causal_gain':causal_gain,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CODE_PLATEAU_SELF_EVOLUTION_V8_WITHHELD')
