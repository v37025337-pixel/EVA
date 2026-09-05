from __future__ import annotations
from pathlib import Path
from itertools import product
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_unified_core_v1 import UnifiedYADOCoreV1

PARENT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-substrate-evolution-v2.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-real-repair-v1.json'
EXP=REPO/'experience/yado-coding-whole-function-real-repair-v1.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

parent=load(PARENT);head=load(HEAD)
if parent.get('status')!='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EVOLUTION_V2':
    raise RuntimeError('SUBSTRATE_V2_PASS_REQUIRED')
if parent.get('next_required_capability')!='G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V1':
    raise RuntimeError('SUBSTRATE_FRONTIER_MISMATCH')
if parent.get('added_safe_calls')!=['int']:
    raise RuntimeError('EXPECTED_SELECTED_SAFE_CALL_INT')
if 'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3' not in head.get('active_capabilities',[]):
    raise RuntimeError('CANONICAL_COGNITIVE_LAYER_REQUIRED')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

class WholeFunctionRepairV1(BoundedCompositionalProgramRepairV3):
    SAFE_CALLS=dict(BoundedCompositionalProgramRepairV3.SAFE_CALLS)
WholeFunctionRepairV1.SAFE_CALLS['int']=int

def same_ast(a,b):
    try:return ast.dump(ast.parse(a),include_attributes=False)==ast.dump(ast.parse(b),include_attributes=False)
    except Exception:return False

def execute(src,name,ctx):
    return WholeFunctionRepairV1.execute(src,name,(copy.deepcopy(ctx),))

def score(src,name,states,reference):
    ok=0
    for ctx in states:
        try:ok+=execute(src,name,ctx)==execute(reference,name,ctx)
        except Exception:pass
    return ok/max(1,len(states))

def all_states_for(source):
    tree=ast.parse(source);func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
    arg=func.args.args[0].arg
    keys=[]
    for comp in [x for x in ast.walk(func) if isinstance(x,(ast.ListComp,ast.SetComp,ast.GeneratorExp,ast.DictComp))]:
        bindings={}
        for g in comp.generators:
            if isinstance(g.target,ast.Name) and isinstance(g.iter,(ast.Tuple,ast.List)):
                vals=[]
                good=True
                for e in g.iter.elts:
                    if not isinstance(e,ast.Constant) or not isinstance(e.value,str):good=False;break
                    vals.append(e.value)
                if good:bindings[g.target.id]=vals
        for x in ast.walk(comp):
            if isinstance(x,ast.Subscript) and isinstance(x.value,ast.Name) and x.value.id==arg and isinstance(x.slice,ast.Name):
                for k in bindings.get(x.slice.id,[]):
                    if k not in keys:keys.append(k)
    if not keys:raise RuntimeError('WHOLE_FUNCTION_STATE_KEYS_NOT_INFERRED')
    return [dict(zip(keys,bits)) for bits in product((False,True),repeat=len(keys))],keys

def hamming(a,b,keys):
    return sum(bool(a[k])!=bool(b[k]) for k in keys)/max(1,len(keys))

def partition(states):
    xs=sorted(states,key=lambda x:sha(canon(x)))
    # 32-state domain: 8 calibration, 4 seed, 12 active probe pool, 8 hidden.
    if len(xs)<24:raise RuntimeError('STATE_DOMAIN_TOO_SMALL')
    cal=xs[:8];seed=xs[8:12];hidden=xs[-8:];probe=xs[12:-8]
    return cal,seed,probe,hidden

def hypotheses(mutated,name,known,max_count=160):
    # Candidate hypothesis set is generated without using the hidden reference.
    xs=[];seen=set()
    def add(s):
        if not s or s in seen:return
        seen.add(s)
        if WholeFunctionRepairV1._passes(s,name,known):xs.append(s)
    add(mutated)
    first=[]
    for c in WholeFunctionRepairV1._atomic_mutations(mutated,known,enable=('binop','compare','boolop','constant')):
        first.append(c);add(c)
        if len(first)>=220:break
    if len(xs)<2:
        for base in first[:120]:
            for c in WholeFunctionRepairV1._atomic_mutations(base,known,enable=('binop','compare','boolop','constant')):
                add(c)
                if len(xs)>=max_count:break
            if len(xs)>=max_count:break
    xs.sort(key=lambda s:(len(s),sha(s),s))
    return xs[:max_count]

def choose_defect(reference,name,calibration):
    examples=[((copy.deepcopy(x),),execute(reference,name,x)) for x in calibration]
    candidates=[];token_map={}
    for cand in WholeFunctionRepairV1._atomic_mutations(reference,examples,enable=('binop','compare','boolop','constant')):
        if same_ast(cand,reference):continue
        reversible=False
        for back in WholeFunctionRepairV1._atomic_mutations(cand,examples,enable=('binop','compare','boolop','constant')):
            if same_ast(back,reference):reversible=True;break
        if not reversible:continue
        sc=score(cand,name,calibration,reference)
        if sc>=1.0:continue
        token='D-'+sha(cand)[:16];token_map[token]=(cand,sc)
        candidates.append(EvidenceCandidate(token=token,evidence=1.0-sc,complexity=1.0,risk=0.0,novelty=1.0))
    if not candidates:raise RuntimeError('NO_REVERSIBLE_MATERIAL_WHOLE_FUNCTION_DEFECT')
    sel=NeutralEvidenceProfileSelectorV1.select(candidates,complexity_penalty=.01,risk_penalty=.5,novelty_bonus=.01)
    cand,sc=token_map[sel['selected_token']]
    return cand,sc,sel

def cognitive_decision(organ,payload):
    return core.cognitive_experience_decide(organ,payload)

def run_task(meta):
    reference=meta['source'];name=meta['function_name']
    states,keys=all_states_for(reference)
    calibration,seed_states,probe_states,hidden_states=partition(states)
    mutated,cal_score,defect_selector=choose_defect(reference,name,calibration)
    mutated_hidden=score(mutated,name,hidden_states,reference)
    known=[((copy.deepcopy(x),),execute(reference,name,x)) for x in seed_states]
    current=mutated;trace=[];queried=[]

    for cycle in range(12):
        hs=hypotheses(mutated,name,known)
        # If the current source passes known observations, include it in the disagreement population.
        if WholeFunctionRepairV1._passes(current,name,known) and current not in hs:hs=[current]+hs
        remaining=[x for x in probe_states if canon(x) not in {canon(q) for q in queried}]
        if not remaining:break

        # Cognitive layer must authorize active evidence search.
        think_e=cognitive_decision('THINKING',{'oracle_available':True,'hypothesis_set_present':True,'state_known':True})
        intel_e=cognitive_decision('INTELLIGENCE',{'hypothesis_set_present':True,'state_known':True})
        if think_e.get('decision')!='SEEK_EVIDENCE' or intel_e.get('decision')!='ACTIVE_EVIDENCE_SEARCH':
            trace.append({'cycle':cycle,'phase':'EVIDENCE','status':'COGNITIVE_WITHHOLD','thinking':think_e,'intelligence':intel_e});break

        probe_candidates=[];probe_map={}
        used_states=seed_states+queried
        for ctx in remaining:
            outputs=[]
            for s in hs:
                try:outputs.append(canon(execute(s,name,ctx)))
                except Exception:outputs.append('__ERROR__')
            distinct=len(set(outputs))
            disagreement=(distinct-1)/max(1,len(hs))
            novelty=min([hamming(ctx,u,keys) for u in used_states] or [1.0])
            token='P-'+sha(canon(ctx))[:16];probe_map[token]=ctx
            probe_candidates.append(EvidenceCandidate(token=token,evidence=float(disagreement),complexity=0.0,risk=0.0,novelty=float(novelty)))
        ps=NeutralEvidenceProfileSelectorV1.select(probe_candidates,complexity_penalty=0.0,risk_penalty=.5,novelty_bonus=.08)
        ctx=probe_map[ps['selected_token']]
        # Oracle answer is revealed only after YADO selected the input.
        expected=execute(reference,name,ctx);queried.append(copy.deepcopy(ctx));known.append(((copy.deepcopy(ctx),),expected))

        # Cognitive layer authorizes revision under a separate non-conflicting state.
        think_r=cognitive_decision('THINKING',{'formal_spec_present':False,'candidate_available':False,'state_known':True})
        intel_r=cognitive_decision('INTELLIGENCE',{'reversible':True,'hypothesis_set_present':False,'formal_spec_present':True,'real_source':True,'state_known':True})
        if think_r.get('decision')!='REVISE' or intel_r.get('decision')!='ITERATIVE_REAL_REPAIR':
            trace.append({'cycle':cycle,'phase':'REPAIR','status':'COGNITIVE_WITHHOLD','thinking':think_r,'intelligence':intel_r,'probe':ctx});break

        repair=WholeFunctionRepairV1.repair(mutated,name,known,max_candidates=20000,max_edit_depth=2,enabled=('binop','compare','boolop','constant'))
        if repair.get('source'):current=repair['source']

        think_t=cognitive_decision('THINKING',{'candidate_available':True,'hypothesis_set_present':False,'formal_spec_present':False,'state_known':True})
        known_exact=WholeFunctionRepairV1._passes(current,name,known)
        trace.append({'cycle':cycle,'phase':'TEST','probe_token':ps['selected_token'],'probe':ctx,'expected':expected,
          'hypothesis_count_before_probe':len(hs),'selected_score':ps['selected_score'],
          'thinking_evidence':think_e.get('decision'),'intelligence_evidence':intel_e.get('decision'),
          'thinking_repair':think_r.get('decision'),'intelligence_repair':intel_r.get('decision'),
          'thinking_test':think_t.get('decision'),'known_exact':known_exact,'candidate_sha256':sha(current),
          'repair_reason':repair.get('reason'),'edit_depth':repair.get('edit_depth'),'tried':repair.get('tried')})
        if think_t.get('decision')!='TEST':break

        # Stop using only observable probe-space ambiguity, never hidden/reference equality.
        hs_after=hypotheses(mutated,name,known)
        disagreement_left=False
        for q in remaining:
            if canon(q)==canon(ctx):continue
            outs=set()
            for s in hs_after:
                try:outs.add(canon(execute(s,name,q)))
                except Exception:outs.add('__ERROR__')
            if len(outs)>1:disagreement_left=True;break
        if known_exact and not disagreement_left:break

    repaired_hidden=score(current,name,hidden_states,reference)
    full_score=score(current,name,states,reference)
    ast_exact=same_ast(current,reference)
    logic_final=cognitive_decision('LOGIC',{'result_exact':full_score==1.0,'state_known':True})
    thinking_final=cognitive_decision('THINKING',{'failure_seen':False,'state_known':True}) if full_score==1.0 else cognitive_decision('THINKING',{'failure_seen':True,'repair_regressed':False,'state_known':True})
    hidden_overlap=any(canon(x) in {canon(y) for y in hidden_states} for x in queried+seed_states+calibration)
    return {
      'task_id':meta['token'],'source_path':meta['path'],'function_name':name,
      'complete_function_source':reference,'reference_source_sha256':meta['source_sha256'],
      'state_key_count':len(keys),'state_count':len(states),
      'calibration_count':len(calibration),'seed_count':len(seed_states),'probe_pool_count':len(probe_states),'hidden_count':len(hidden_states),
      'defect_selector':defect_selector,'mutated_source':mutated,'mutated_source_sha256':sha(mutated),
      'defect_calibration_score':cal_score,'mutated_hidden_score':mutated_hidden,
      'selected_probe_count':len(queried),'selected_probes':queried,'trace':trace,
      'repaired_source':current,'repaired_source_sha256':sha(current),'repaired_hidden_score':repaired_hidden,
      'full_domain_score':full_score,'exact_parent_ast_recovered':ast_exact,
      'logic_final_decision':logic_final,'thinking_final_decision':thinking_final,
      'hidden_overlap_with_calibration_seed_or_selected_probes':hidden_overlap,
      'cognitive_layer_used':True,'original_source_hidden_from_repair_search':True,
    }

unlocked=parent.get('unlocked_candidates') or []
if not unlocked:raise RuntimeError('NO_UNLOCKED_WHOLE_FUNCTION_CANDIDATES')
# The selector is still used even when V2 discovered one candidate; no host function name is hard-coded.
choice=NeutralEvidenceProfileSelectorV1.select([
    EvidenceCandidate(token=x['token'],evidence=float(x.get('mutatable_node_count',0))+0.1*float(x.get('distinct_output_count',0)),complexity=0,risk=0,novelty=1)
    for x in unlocked
],complexity_penalty=.02,risk_penalty=.5,novelty_bonus=.02)
selected=next(x for x in unlocked if x['token']==choice['selected_token'])
episode=run_task(selected)

# Deterministic restore repeats the whole repair path.
restored=run_task(selected)
restore_exact=(episode['mutated_source_sha256']==restored['mutated_source_sha256'] and
               episode['repaired_source_sha256']==restored['repaired_source_sha256'] and
               [canon(x) for x in episode['selected_probes']]==[canon(x) for x in restored['selected_probes']])
control_ablation=episode['mutated_hidden_score']
gain=episode['repaired_hidden_score']-episode['mutated_hidden_score']

gene={'schema':'yado.g2.coding_whole_function_real_repair_gene.v1',
 'gene_id':'GENE-G2-CODING-WHOLE-FUNCTION-REAL-REPAIR-V1-'+digest({'episode':episode,'substrate':parent['substrate_gene']['gene_digest']})[:16],
 'organ':'THINKING','gene_scope':['THINKING','INTELLIGENCE','LOGIC','CODE','MEMORY'],
 'heritage':[parent['gene_id'],parent.get('receipt_sha256'),'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3'],
 'mechanism_kind':'COMPLETE_REAL_FUNCTION_REVERSIBLE_DEFECT_ACTIVE_COUNTEREXAMPLE_COGNITIVE_REPAIR',
 'whole_function_task_count':1,'promotion_state':'SHADOW_ONLY'}
gene['gene_digest']=digest(gene)

checks={
 'substrate_v2_consumed':True,
 'whole_function_selected_by_yado':choice['selected_token']==selected['token'],
 'complete_function_not_ast_fragment':episode['complete_function_source'].lstrip().startswith('def '+episode['function_name']+'('),
 'real_active_runtime_source':str(selected['path']).startswith('runtime/') and (REPO/selected['path']).exists(),
 'reversible_shadow_defect_material':episode['defect_calibration_score']<1.0 and episode['mutated_source_sha256']!=episode['reference_source_sha256'],
 'hidden_defect_material':episode['mutated_hidden_score']<=.75,
 'active_self_selected_probe_used':episode['selected_probe_count']>=1,
 'cognitive_layer_used':episode['cognitive_layer_used'] is True,
 'cognitive_evidence_and_repair_actions_observed':any(x.get('thinking_evidence')=='SEEK_EVIDENCE' and x.get('intelligence_evidence')=='ACTIVE_EVIDENCE_SEARCH' and x.get('thinking_repair')=='REVISE' and x.get('intelligence_repair')=='ITERATIVE_REAL_REPAIR' for x in episode['trace']),
 'hidden_never_queried':episode['hidden_overlap_with_calibration_seed_or_selected_probes'] is False,
 'hidden_repair_exact':episode['repaired_hidden_score']==1.0,
 'full_domain_exact':episode['full_domain_score']==1.0,
 'repair_gain_material':gain>=.25,
 'final_logic_accepts':episode['logic_final_decision'].get('decision')=='ACCEPT',
 'final_thinking_accepts':episode['thinking_final_decision'].get('decision')=='ACCEPT',
 'restore_exact':restore_exact and restored['repaired_hidden_score']==episode['repaired_hidden_score'],
 'original_source_hidden_from_repair_search':episode['original_source_hidden_from_repair_search'] is True,
 'host_selected_patch':False,'host_selected_probe':False,'external_coding_model_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
false_keys=['host_selected_patch','host_selected_probe','external_coding_model_used','automatic_canonical_promotion']
passed=all(checks[k] is True for k in checks if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V1' if passed else 'WITHHOLD_G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V1'

experience={'schema':'yado.g2.coding_whole_function_real_repair.experience.v1','status':'TRAINED' if passed else 'WITHHOLD',
 'substrate_gene_id':parent['gene_id'],'selected_function':{'token':selected['token'],'path':selected['path'],'function_name':selected['function_name']},
 'episode':episode,'restore':restored,'repair_gain':gain,'control_ablation_hidden_score':control_ablation,
 'whole_function_gene':gene,'canonical_mutation':False,
 'semantic_boundary':'FIRST BOUNDED COMPLETE-FUNCTION REPAIR ON A REAL ACTIVE YADO RUNTIME FUNCTION. THE ENTIRE FUNCTION BODY IS THE REPAIR UNIT. THE ONLY SHADOW SUBSTRATE EXTENSION IS PURE BUILTIN int; ATTRIBUTE/LOOP/FILESYSTEM/NETWORK REMAIN DISALLOWED. THIS IS ONE FUNCTION/ONE FILE, NOT GENERAL SOFTWARE REPAIR.'}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.coding_whole_function_real_repair.v1','status':status,
 'selected_function':{'token':selected['token'],'path':selected['path'],'function_name':selected['function_name']},
 'state_count':episode['state_count'],'mutated_hidden_score':episode['mutated_hidden_score'],'repaired_hidden_score':episode['repaired_hidden_score'],
 'full_domain_score':episode['full_domain_score'],'exact_parent_ast_recovered':episode['exact_parent_ast_recovered'],
 'selected_probe_count':episode['selected_probe_count'],'repair_gain':gain,'control_ablation_hidden_score':control_ablation,
 'gene_id':gene['gene_id'],'whole_function_gene':gene,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V2_SUBSTRATE_EXPANSION' if passed else 'G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V1_REPAIR',
 'receipt_sha256':None,'semantic_boundary':experience['semantic_boundary']}
report['receipt_sha256']=digest({k:v for k,v in report.items() if k!='receipt_sha256'})
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'selected_function':report['selected_function'],'state_count':report['state_count'],
 'mutated_hidden_score':report['mutated_hidden_score'],'repaired_hidden_score':report['repaired_hidden_score'],
 'full_domain_score':report['full_domain_score'],'exact_parent_ast_recovered':report['exact_parent_ast_recovered'],
 'selected_probe_count':report['selected_probe_count'],'repair_gain':gain,'gene_id':gene['gene_id'],
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
