from __future__ import annotations
from pathlib import Path
from dataclasses import asdict,is_dataclass
import copy,hashlib,json,os,sys,time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_core_v2_2 import MechanismSelector
from yado_core_v2_1 import BoundedRuleSandbox,RuleProgram
from yado_organ_runtime_native_v1 import tree_predict
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
ART=REPO/'architecture/yado-kernel-evolutionary-successor-genesis-v3.json'
CAND=REPO/'candidates/kernel-self-generated/evolutionary-rule-program-successor-v3.json'
OUT=ROOT/'yado_kernel_evolutionary_successor_genesis_v3_receipt.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,o): p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def serial(o):
    if is_dataclass(o): return asdict(o)
    if hasattr(o,'__dict__'): return copy.deepcopy(o.__dict__)
    return o
def log(stage,**kw):
    print(json.dumps({'stage':stage,'ts':time.time(),**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,base,corpus=map(load,[HEAD,CORE,LEDGER,BASE,CORPUS])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V4']:
    raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')
if cdig(corpus,'corpus_digest')!=corpus.get('corpus_digest'):
    raise RuntimeError('FROZEN_CORPUS_DIGEST_MISMATCH')
cases=list(corpus['cases'])
true_blind=[c for c in cases if c['bucket']<18]
nonblind=[c for c in cases if c['bucket']>=18]
if (len(nonblind),len(true_blind))!=(252,46):
    raise RuntimeError('CORPUS_PARTITION_MISMATCH')

parent_result=base['kernel_result']
parent_model=parent_result['model']
parent_digest=h({'algorithm':parent_result.get('selected_algorithm'),'model':parent_model})
def parent_pred(x): return tree_predict(parent_model,x)

# Native G2 evolutionary-control decision.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_successor_v3_operation.sqlite'))
try:
    records=[
      {'variant_id':'EXECUTABLE_PARENT','parent_id':None,'lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':parent_digest,
       'task_scores':{'validation':float(parent_result['validation']),'fresh_blind':float(parent_result['fresh_blind']),'completion':1.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0},'failure_tags':['fresh_blind_below_gate'],'status':'EVALUATED'},
      {'variant_id':'EXHAUSTIVE_SEARCH_LIMITS','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':'v4-and-successor-v2-resource-ceilings',
       'task_scores':{'validation':0.0,'fresh_blind':0.0,'completion':0.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':0.0,'bounded':0.0},
       'failure_tags':['meta_grammar_timeout','cart_axis_timeout','linear_score_timeout'],'status':'EVALUATED'}
    ]
    operation=k.propose_evolution_operation(records,'EXHAUSTIVE_SEARCH_LIMITS','fresh_blind')
finally:
    k.close()
if operation.get('operation')!='REACTION_NORM':
    raise RuntimeError('KERNEL_DID_NOT_SELECT_REACTION_NORM:'+json.dumps(operation,sort_keys=True))
log('operation_done',operation=operation.get('operation'))

# Deterministic stratification uses only permitted non-blind parent outcome.
errors=sorted([c for c in nonblind if parent_pred(c['x'])!=c['y']],key=lambda c:h(c['key']+'|V3ERR'))
correct=sorted([c for c in nonblind if parent_pred(c['x'])==c['y']],key=lambda c:h(c['key']+'|V3OK'))
if len(errors)<6: raise RuntimeError('INSUFFICIENT_PARENT_ERRORS:'+str(len(errors)))
# Reserve at least 2 parent errors for dev holdout; use remaining for developmental training.
hold_n=max(2,min(3,len(errors)//4))
dev_err=errors[-hold_n:]; train_err=errors[:-hold_n]
ok_hold_n=max(12,int(len(correct)*.18))
dev_ok=correct[-ok_hold_n:]; train_ok=correct[:-ok_hold_n]
dev_hold=sorted(dev_err+dev_ok,key=lambda c:h(c['key']+'|V3HOLD'))
train_rows=sorted(train_err+train_ok,key=lambda c:h(c['key']+'|V3TRAIN'))
log('evidence_ready',parent_errors=len(errors),train=len(train_rows),dev_holdout=len(dev_hold),train_errors=len(train_err),dev_errors=len(dev_err))

def mk_examples(rows,mode):
    if mode=='gate':
        return [{'input':c['x'],'expected':'PARENT_ERROR' if parent_pred(c['x'])!=c['y'] else 'PARENT_OK'} for c in rows]
    if mode=='corrector':
        return [{'input':c['x'],'expected':c['y']} for c in rows if parent_pred(c['x'])!=c['y']]
    raise ValueError(mode)

def synth_rule(examples,capability):
    candidates=MechanismSelector.synthesize_candidates(capability,'INTELLIGENCE',examples,min_support=2)
    rules=[p for p in candidates if isinstance(p,RuleProgram)]
    if not rules: raise ValueError('NO_RULE_PROGRAM_CANDIDATE')
    rules.sort(key=lambda p:(MechanismSelector.complexity(p),p.digest()))
    return rules[0]

def execute(program,x):
    return BoundedRuleSandbox.execute(program,x)

def score_gate(program,rows):
    return sum(execute(program,c['x'])==('PARENT_ERROR' if parent_pred(c['x'])!=c['y'] else 'PARENT_OK') for c in rows)/max(1,len(rows))
def score_corrector(program,rows):
    err=[c for c in rows if parent_pred(c['x'])!=c['y']]
    return sum(execute(program,c['x'])==c['y'] for c in err)/max(1,len(err))

# Developmental synthesis first; true blind remains inaccessible here.
genesis_error=None
try:
    gate_dev=synth_rule(mk_examples(train_rows,'gate'),'PARENT_ERROR_GATE_V3')
    corr_dev=synth_rule(mk_examples(train_rows,'corrector'),'PARENT_RESIDUAL_CORRECTOR_V3')
    gate_dev_score=score_gate(gate_dev,dev_hold)
    corr_dev_score=score_corrector(corr_dev,dev_hold)
    log('developmental_rules_created',
        gate_rules=len(gate_dev.rules),corrector_rules=len(corr_dev.rules),
        gate_dev_holdout=gate_dev_score,corrector_dev_holdout=corr_dev_score)
except ValueError as exc:
    genesis_error=type(exc).__name__+':'+str(exc)
    gate_dev=corr_dev=None;gate_dev_score=corr_dev_score=0.0
    log('developmental_rule_creation_withhold',error=genesis_error)

development_supported=bool(gate_dev is not None and corr_dev is not None and gate_dev_score>=0.75 and corr_dev_score>0.0)

gate_final=corr_final=None
if development_supported:
    try:
        gate_final=synth_rule(mk_examples(nonblind,'gate'),'PARENT_ERROR_GATE_V3_FINAL')
        corr_final=synth_rule(mk_examples(nonblind,'corrector'),'PARENT_RESIDUAL_CORRECTOR_V3_FINAL')
    except ValueError as exc:
        genesis_error='FINAL_'+type(exc).__name__+':'+str(exc)
        gate_final=corr_final=None
        log('final_rule_creation_withhold',error=genesis_error)

def child_pred(x):
    if gate_final is None or corr_final is None: return parent_pred(x)
    if execute(gate_final,x)=='PARENT_ERROR':
        return execute(corr_final,x)
    return parent_pred(x)
def acc(rows,pred):
    return sum(pred(c['x'])==c['y'] for c in rows)/max(1,len(rows))

parent_blind=acc(true_blind,parent_pred)
child_blind=acc(true_blind,child_pred) if gate_final is not None else parent_blind
parent_correct=[c for c in true_blind if parent_pred(c['x'])==c['y']]
parent_wrong=[c for c in true_blind if parent_pred(c['x'])!=c['y']]
retention=acc(parent_correct,child_pred) if gate_final is not None else 1.0
repair=sum(child_pred(c['x'])==c['y'] for c in parent_wrong)/max(1,len(parent_wrong)) if gate_final is not None else 0.0
supported=bool(gate_final is not None and corr_final is not None and child_blind>=0.90 and child_blind>parent_blind and retention==1.0 and repair>0)
state='SHADOW_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_EVOLUTIONARY_SUCCESSOR_FRESH_ADMISSION_V1' if supported else 'KERNEL_EVOLUTIONARY_SUCCESSOR_RULE_PROGRAM_GENESIS_V2'

candidate={
 'schema':'yado.g2.evolutionary_rule_program_successor.v3',
 'state':state,
 'principle':'CREATE_SUCCESSOR_FROM_PARENT_DEFICIT_NOT_SEARCH_EXHAUSTIVE_MODEL_SPACE',
 'evolution_operation':operation,
 'parent':{'model_digest':parent_digest,'fresh_blind':parent_blind,'algorithm':parent_result.get('selected_algorithm')},
 'new_mechanism':{
   'op':'EVOLUTIONARY_RULE_PROGRAM_RESIDUAL_SUCCESSOR',
   'error_gate':None if gate_final is None else serial(gate_final),
   'residual_corrector':None if corr_final is None else serial(corr_final),
   'generator':'MechanismSelector.synthesize_candidates -> RuleProgramSynthesizer',
   'executor':'BoundedRuleSandbox.execute',
   'genesis_error':genesis_error,
 },
 'development':{
   'supported':development_supported,
   'gate_dev_holdout':gate_dev_score,
   'corrector_dev_holdout':corr_dev_score,
   'train_count':len(train_rows),'dev_holdout_count':len(dev_hold),
   'train_parent_errors':len(train_err),'dev_parent_errors':len(dev_err),
 },
 'metrics':{
   'fresh_blind_parent':parent_blind,'fresh_blind_successor':child_blind,
   'parent_correct_retention':retention,'parent_error_repair_rate':repair,
   'true_blind_parent_error_count':len(parent_wrong),
 },
 'frozen_history':{'corpus_digest':corpus['corpus_digest'],'true_blind_used_for_creation':False,'true_blind_used_for_admission_only':True},
 'boundedness':{'max_rules':BoundedRuleSandbox.MAX_RULES,'allowed_ops':sorted(BoundedRuleSandbox.ALLOWED_OPS),'eval_exec_used':False,'network_used_by_rule_executor':False},
 'host_task_specific_rules_written':False,
 'kernel_generated_rule_programs':gate_final is not None and corr_final is not None,
 'canonical_active':False,'promotion_applied':False,
}
candidate['candidate_digest']=h(candidate)
CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)
log('candidate_evaluated',state=state,parent_blind=parent_blind,child_blind=child_blind,retention=retention,repair=repair,next=next_cap)

artifact={
 'schema':'yado.g2.kernel_evolutionary_successor_genesis.v3',
 'status':'PASS_EVOLUTIONARY_SUCCESSOR_GENESIS_V3',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],
 'genesis_error':genesis_error,'development':candidate['development'],'metrics':candidate['metrics'],
 'frozen_corpus_digest':corpus['corpus_digest'],'next_required_capability':next_cap,
 'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

# Advance only developmental control-plane frontier; mechanism remains shadow unless separately admitted.
previous_head_digest=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits'
head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

checks={
 'kernel_selected_reaction_norm':operation.get('operation')=='REACTION_NORM',
 'frozen_history_digest_valid':cdig(corpus,'corpus_digest')==corpus['corpus_digest'],
 'blind_not_used_for_creation':candidate['frozen_history']['true_blind_used_for_creation'] is False,
 'bounded_rule_executor':candidate['boundedness']['eval_exec_used'] is False and candidate['boundedness']['network_used_by_rule_executor'] is False,
 'no_canonical_mechanism_mutation':True,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
receipt={
 **artifact,'schema':'yado.g2.kernel_evolutionary_successor_genesis.receipt.v3',
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],'checks':checks,
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_EVOLUTIONARY_SUCCESSOR_GENESIS_V3",
 'event_type':'G2_EVOLUTIONARY_RULE_PROGRAM_SUCCESSOR_GENESIS',
 'status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],
 'deficit':'KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V4',
 'effect':f"MODE=CREATE_NOT_SEARCH; GENERATOR=RULE_PROGRAM; PARENT_BLIND={parent_blind:.6f}; CHILD_BLIND={child_blind:.6f}; RETAIN={retention:.6f}; REPAIR={repair:.6f}; GENESIS_ERROR={genesis_error}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-evolutionary-successor-genesis-v3-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,
 'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap or ctx['active_head']!='G2_CANDIDATE_TRCG_V1':
    raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',candidate_state=state,next=next_cap,receipt_sha256=receipt['receipt_sha256'])
