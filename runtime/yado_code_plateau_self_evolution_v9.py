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
FAILED=REPO/'receipts'/'yado-code-plateau-self-evolution-v8-run-33491526539.json'
V10SRC=REPO/'candidates'/'g2-self-evolution'/'canonical_split_recursive_program_repair_v10.py'
EXP=REPO/'experience'/'yado-external-agent-systems-learning-v1.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'ambiguity_aware_program_repair_v11.py'
CAND_META=CAND_DIR/'ambiguity_aware_program_repair_v11.json'
OUT=ROOT/'yado_code_plateau_self_evolution_v9_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE);failed=load(FAILED);experience=load(EXP)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['CODE_PLATEAU_SELF_EVOLUTION_V9']:raise RuntimeError('UNEXPECTED_FRONTIER')
if failed.get('status')!='WITHHOLD_CODE_PLATEAU_SELF_EVOLUTION_V8':raise RuntimeError('EXPECTED_PRIOR_WITHHOLD')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

v10=V10SRC.read_text(encoding='utf-8')
base=v10.replace('class CanonicalSplitRecursiveProgramRepairV10:','class _CanonicalSplitBaseV10:')
base=base.replace('COMPONENT_ID="ALG-G2-CANONICAL-SPLIT-RECURSIVE-PROGRAM-REPAIR-V10"','COMPONENT_ID="INTERNAL-CANONICAL-SPLIT-BASE-V10"')
base=base.replace("__all__=['CanonicalSplitRecursiveProgramRepairV10']","__all__=[]")
append=r'''

class AmbiguityAwareProgramRepairV11(_CanonicalSplitBaseV10):
    COMPONENT_ID="ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11"

    @classmethod
    def _mutate_threshold(cls,source,node_index,new_value):
        tree=ast.parse(source)
        comps=[n for n in ast.walk(tree) if isinstance(n,ast.Compare) and len(n.ops)==1 and len(n.comparators)==1 and isinstance(n.comparators[0],ast.Constant)]
        if node_index>=len(comps):return None
        comps[node_index].comparators[0].value=new_value
        ast.fix_missing_locations(tree)
        try:cls.BASE._validate(tree)
        except Exception:return None
        return ast.unparse(tree)+"\n"

    @classmethod
    def _threshold_ambiguity(cls,source,function_name,examples):
        tree=ast.parse(source)
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
        arg_names=[a.arg for a in func.args.args]
        comps=[n for n in ast.walk(tree) if isinstance(n,ast.Compare) and len(n.ops)==1 and len(n.comparators)==1 and isinstance(n.left,ast.Name) and isinstance(n.comparators[0],ast.Constant)]
        for idx,node in enumerate(comps):
            name=node.left.id
            if name not in arg_names:continue
            pos=arg_names.index(name);k=node.comparators[0].value
            if not isinstance(k,int) or isinstance(k,bool):continue
            observed=sorted(set(args[pos] for args,_ in examples if pos<len(args) and isinstance(args[pos],int) and not isinstance(args[pos],bool)))
            if not observed:continue
            for alt_k in (k-1,k+1):
                alt=cls._mutate_threshold(source,idx,alt_k)
                if not alt or not cls._passes(alt,function_name,examples):continue
                # Find an integer probe in/near the unobserved threshold gap on which the programs disagree.
                probe_values=sorted(set([k-1,k,k+1,alt_k-1,alt_k,alt_k+1]))
                for pv in probe_values:
                    if pv in observed:continue
                    base_args=list(examples[0][0])
                    if pos>=len(base_args):continue
                    base_args[pos]=pv;args=tuple(base_args)
                    try:
                        a=cls.execute(source,function_name,args);b=cls.execute(alt,function_name,args)
                    except Exception:continue
                    if a!=b:
                        return {'ambiguous':True,'arg':name,'threshold':k,'alternative_threshold':alt_k,'probe_value':pv,'outputs':[a,b]}
        return {'ambiguous':False}

    @classmethod
    def repair(cls,source,function_name,train_examples,max_candidates=None,max_edit_depth=None,enabled=('binop','compare','boolop','constant','structural')):
        r=super().repair(source,function_name,train_examples,max_candidates=max_candidates,max_edit_depth=max_edit_depth,enabled=enabled)
        if not r.get('source'):return r
        ambiguity=cls._threshold_ambiguity(r['source'],function_name,train_examples)
        if ambiguity.get('ambiguous'):
            return {'source':None,'reason':'AMBIGUOUS_UNSEEN_THRESHOLD','ambiguity':ambiguity,'repair_mode':'AMBIGUITY_AWARE_WITHHOLD'}
        out=dict(r);out['ambiguity_checked']=True;return out

__all__=['AmbiguityAwareProgramRepairV11']
'''
candidate_source=base+append
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(candidate_source,encoding='utf-8')

sp=importlib.util.spec_from_file_location('_v10_shadow',V10SRC)
m10=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m10;sp.loader.exec_module(m10)
V10=m10.CanonicalSplitRecursiveProgramRepairV10
ns={};exec(compile(candidate_source,'<candidate>','exec'),ns);V11=ns['AmbiguityAwareProgramRepairV11']

def run(cls,src,fn,tr):
    try:return cls.repair(src,fn,tr,max_candidates=24000,max_edit_depth=2)
    except Exception as e:return {'source':None,'error':type(e).__name__}

def score_source(cls,r,fn,hold):
    if not r.get('source'):return 0.0
    try:return sum(cls.execute(r['source'],fn,args)==exp for args,exp in hold)/len(hold)
    except Exception:return 0.0

# Prior ambiguous gap B: train cannot determine whether x=3 belongs low or high regime.
amb_tr=[((-5,),5),((-2,),2),((0,),0),((2,),2),((5,),16),((8,),25)]
amb_hold=[((-9,),9),((1,),1),((3,),3),((6,),19),((10,),31)]

strategies=[
 {'id':'COMMIT_FIRST_V10','cls':V10,'complexity':.50,'risk':.08,'novelty':.20},
 {'id':'AMBIGUITY_AWARE_V11','cls':V11,'complexity':.54,'risk':.04,'novelty':.98},
]
validation={};tok={}
for i,s in enumerate(strategies):
    r=run(s['cls'],'def f(x):\n    return x\n','f',amb_tr)
    ambiguity_score=1.0 if (s['id']=='AMBIGUITY_AWARE_V11' and r.get('reason')=='AMBIGUOUS_UNSEEN_THRESHOLD') else 0.0
    if s['id']=='COMMIT_FIRST_V10':
        ambiguity_score=0.0 if r.get('source') else 1.0
    # Resolved version explicitly observes the gap values, so a patch should be allowed.
    resolved=amb_tr+[((3,),3),((4,),4)]
    rr=run(s['cls'],'def f(x):\n    return x\n','f',resolved)
    resolved_hold=[((-9,),9),((1,),1),((3,),3),((4,),4),((6,),19),((10,),31)]
    resolved_score=score_source(s['cls'],rr,'f',resolved_hold)
    fam={'AMBIGUOUS_GAP_WITHHOLD':ambiguity_score,'RESOLVED_GAP_COMMIT':resolved_score}
    token='opaque_'+h({'code_plateau_v9':i,'head':head['canonical_head_digest']})[:18]
    validation[s['id']]={'families':fam,'score':avg(list(fam.values())),'min_family':min(fam.values()),
                         'details':{'ambiguous':r,'resolved':rr},'token':token,'complexity':s['complexity'],'risk':s['risk'],'novelty':s['novelty']}
    tok[token]=s
sel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()])
selected=tok[sel['selected_token']]

fresh={}
# Fresh ambiguous gap: missing x=2,3 between regimes.
a=[((-6,),-12),((-3,),-6),((0,),0),((1,),1),((4,),13),((7,),22)]
ra=run(V11,'def g(x):\n    return x\n','g',a)
fresh['AMBIGUOUS_GAP_FRESH']=1.0 if ra.get('reason')=='AMBIGUOUS_UNSEEN_THRESHOLD' else 0.0
# Resolve by adding the gap labels.
ar=a+[((2,),2),((3,),3)]
rar=run(V11,'def g(x):\n    return x\n','g',ar)
fresh['RESOLVED_GAP_FRESH']=score_source(V11,rar,'g',[((-8,),-16),((2,),2),((3,),3),((5,),16),((9,),28)])
# No-threshold affine should not be withheld.
b=[((-3,),-7),((0,),2),((2,),8),((5,),17)]
rb=run(V11,'def g(x):\n    return x\n','g',b)
fresh['AFFINE_NO_FALSE_WITHHOLD']=score_source(V11,rb,'g',[((-7,),-19),((1,),5),((9,),29)])
# Old two-edit repair.
c=[((1,2),6),((2,4),9),((-2,3),4),((0,0),3)]
rc=run(V11,'def g(x,y):\n    return x-y+1\n','g',c)
fresh['TWO_EDIT_NO_FALSE_WITHHOLD']=score_source(V11,rc,'g',[((5,6),14),((-3,-4),-4),((0,7),10)])
holdout={'families':fresh,'score':avg(list(fresh.values())),'min_family':min(fresh.values())}

old=validation['COMMIT_FIRST_V10']['families']['AMBIGUOUS_GAP_WITHHOLD']
new=validation['AMBIGUITY_AWARE_V11']['families']['AMBIGUOUS_GAP_WITHHOLD']
causal_gain=new-old

unsafe_ok=False
try:V11.repair('import os\ndef f(x):\n    return x\n','f',[((1,),1)])
except Exception:unsafe_ok=True
multi_ok=False
try:V11.repair('def f(x):\n    return x\ndef h(x):\n    return x\n','f',[((1,),1)])
except Exception:multi_ok=True

checks={
 'selected_ambiguity_aware':selected['id']=='AMBIGUITY_AWARE_V11',
 'prior_ambiguity_detected':validation['AMBIGUITY_AWARE_V11']['families']['AMBIGUOUS_GAP_WITHHOLD']>=.99,
 'resolved_gap_commits':validation['AMBIGUITY_AWARE_V11']['families']['RESOLVED_GAP_COMMIT']>=.99,
 'causal_ambiguity_gain':causal_gain>=.99,
 'fresh_min_one':holdout['min_family']>=.99,
 'total_budget_not_increased':V11.MAX_CANDIDATES==24000,
 'unsafe_rejected':unsafe_ok,'multi_function_rejected':multi_ok,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')
}
passed=all(checks.values());next_cap='CODE_PLATEAU_FRESH_ADMISSION_V9' if passed else 'CODE_PLATEAU_SELF_EVOLUTION_V10'

candidate={'schema':'yado.g2.ambiguity_aware_program_repair_candidate.v11',
 'component_id':'ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11','selected_strategy':selected['id'],
 'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'causal_gain':causal_gain,
 'compute_contract':{'max_candidates':V11.MAX_CANDIDATES,'base_search_budget':V11.BASE_SEARCH_BUDGET,
                     'structural_search_budget':V11.STRUCTURAL_SEARCH_BUDGET,'max_conditional_depth':V11.MAX_CONDITIONAL_DEPTH,
                     'max_split_tests':V11.MAX_SPLIT_TESTS,'max_search_nodes':V11.MAX_SEARCH_NODES},
 'experience_digest':experience['experience_digest'],'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,
 'parent_head_digest':head['canonical_head_digest'],'canonical_active':False,'promotion_applied':False,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'FIXED-BUDGET PROGRAM REPAIR THAT WITHHOLDS WHEN TRAINING-EQUIVALENT THRESHOLD VARIANTS DISAGREE ON UNOBSERVED INTEGER GAP VALUES; COMMITS AGAIN WHEN ADDED EVIDENCE REMOVES THE AMBIGUITY.'
}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

state['candidate_history'].append({'round':state.get('round',17),'plane':'CODE','candidate_digest':candidate['candidate_digest'],
 'selected_strategy':selected['id'],'fresh_score':holdout['score'],'baseline_score':validation['COMMIT_FIRST_V10']['score'],
 'causal_drop':causal_gain,'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.code_plateau_self_evolution.v9',
 'status':'PASS_CODE_PLATEAU_SELF_EVOLUTION_V9' if passed else 'WITHHOLD_CODE_PLATEAU_SELF_EVOLUTION_V9',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'causal_gain':causal_gain,
 'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CODE_PLATEAU_SELF_EVOLUTION_V9",
 'event_type':'AMBIGUITY_AWARE_CODE_SELF_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'CODE_PLATEAU_SELF_EVOLUTION_V9',
 'effect':f"SELECTED={selected['id']}; FRESH={holdout['score']:.6f}; AMBIGUITY_GAIN={causal_gain:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-code-plateau-self-evolution-v9-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'selected_strategy':selected['id'],'validation':validation,'fresh_validation':holdout,
 'causal_gain':causal_gain,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CODE_PLATEAU_SELF_EVOLUTION_V9_WITHHELD')
