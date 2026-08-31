from __future__ import annotations
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
RUNTIME=REPO/'runtime'/'yado_unified_core_v1.py'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
CAND_SRC=REPO/'candidates'/'g2-self-evolution'/'semantic_expression_synthesizer_v1.py'
CAND_META=REPO/'candidates'/'g2-self-evolution'/'semantic_expression_synthesizer_v1.json'
TARGET=REPO/'runtime'/'yado_semantic_expression_synthesizer_v1.py'
OUT=ROOT/'yado_mathematical_reasoning_canonical_integration_v1_receipt.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))

def latest_admission():
    xs=list((REPO/'receipts').glob('yado-mathematical-reasoning-fresh-admission-v1-run-*.json'))
    if not xs: raise RuntimeError('FRESH_ADMISSION_RECEIPT_MISSING')
    def runno(p):
        try:return int(p.stem.rsplit('-',1)[-1])
        except:return -1
    return max(xs,key=runno)

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);meta=load(CAND_META)
admit_path=latest_admission();admit=load(admit_path)
validate_ledger_v2(ledger)

if ledger.get('open_deficits')!=['REAL_MATHEMATICAL_REASONING_CANONICAL_INTEGRATION_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if admit.get('status')!='PASS_MATHEMATICAL_REASONING_FRESH_ADMISSION_V1':
    raise RuntimeError('FRESH_ADMISSION_NOT_PASS')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':
    raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(CAND_SRC)!=meta.get('candidate_source_sha256'):
    raise RuntimeError('CANDIDATE_SOURCE_DRIFT')
if admit.get('candidate_source_sha256')!=meta.get('candidate_source_sha256'):
    raise RuntimeError('ADMISSION_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

candidate_code=CAND_SRC.read_text(encoding='utf-8')
source_safety={
    'no_exec': 'exec(' not in candidate_code,
    'no_eval': 'eval(' not in candidate_code,
    'no_network': all(x not in candidate_code for x in ['requests.','aiohttp','urllib','socket']),
    'no_subprocess': 'subprocess' not in candidate_code,
    'bounded_ops': 'max_ops=3' in candidate_code and 'max_states_per_level=30000' in candidate_code,
}

src=RUNTIME.read_text(encoding='utf-8')
patched=src
import_anchor='from yado_legacy_experience_retriever_v2 import LegacyExperienceRetrieverV1'
import_line=import_anchor+'\nfrom yado_semantic_expression_synthesizer_v1 import SemanticExpressionSynthesizerV1'
if 'from yado_semantic_expression_synthesizer_v1 import SemanticExpressionSynthesizerV1' not in patched:
    patched=patched.replace(import_anchor,import_line)

init_anchor='        self.legacy_experience_retriever=LegacyExperienceRetrieverV1(self.repo,self.experience)'
init_line=init_anchor+'\n        self.semantic_expression_synthesizer=SemanticExpressionSynthesizerV1'
if 'self.semantic_expression_synthesizer=' not in patched:
    patched=patched.replace(init_anchor,init_line)

method_anchor='    def represent_raw_task(self,raw_text:str)->dict[str,Any]:'
methods=(
"    def synthesize_mathematical_expression(self,train_rows:list[dict[str,Any]],max_ops:int=3,max_states_per_level:int=30000)->dict[str,Any]:\n"
"        return self.semantic_expression_synthesizer.synthesize(train_rows,max_ops=max_ops,max_states_per_level=max_states_per_level)\n\n"
"    def predict_mathematical_expression(self,result:dict[str,Any],x:float,y:float)->Any:\n"
"        return self.semantic_expression_synthesizer.predict(result,x,y)\n\n"
+method_anchor)
if '    def synthesize_mathematical_expression(' not in patched:
    patched=patched.replace(method_anchor,methods)

bounded_patch=(
    patched.count('from yado_semantic_expression_synthesizer_v1 import SemanticExpressionSynthesizerV1')==1 and
    patched.count('self.semantic_expression_synthesizer=SemanticExpressionSynthesizerV1')==1 and
    patched.count('def synthesize_mathematical_expression(')==1 and
    patched.count('def predict_mathematical_expression(')==1
)

# Stage the admitted component and test through the patched unified-core interface.
TARGET.write_text(candidate_code,encoding='utf-8')
tmp=ROOT/'_mathematical_reasoning_candidate_unified_core.py'
tmp.write_text(patched,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_mathematical_reasoning_candidate_unified_core',tmp)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO)
    audit=obj.audit()
    train=[
      {'x':-4,'y':3,'expected':1},
      {'x':-2,'y':-5,'expected':49},
      {'x':0,'y':7,'expected':49},
      {'x':1,'y':-3,'expected':4},
      {'x':3,'y':2,'expected':25},
      {'x':6,'y':-1,'expected':25},
    ]
    result=obj.synthesize_mathematical_expression(train,max_ops=3,max_states_per_level=30000)
    blind=[(-7,2,25),(-3,-8,121),(2,9,121),(4,-5,1),(10,-2,64)]
    interface_ok=(result.get('expression') is not None and
                  all(obj.predict_mathematical_expression(result,x,y)==exp for x,y,exp in blind))
finally:
    try: tmp.unlink()
    except FileNotFoundError: pass

checks={
    'fresh_admission_pass': admit.get('status')=='PASS_MATHEMATICAL_REASONING_FRESH_ADMISSION_V1',
    'fresh_score_one': admit.get('fresh_score')==1.0,
    'causal_depth_dependence': admit.get('checks',{}).get('causal_depth_dependence') is True,
    'bounded_withhold_preserved': admit.get('checks',{}).get('bounded_withhold_beyond_depth') is True,
    'source_safety': all(source_safety.values()),
    'bounded_unified_core_patch': bounded_patch,
    'candidate_current_audit_pass': audit.get('pass') is True,
    'unified_core_interface_blind_pass': interface_ok,
    'canonical_head_coherent': ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())

post_head=None;post_core=None
if passed:
    RUNTIME.write_text(patched,encoding='utf-8')
    runtime_sha=fsha(RUNTIME)
    component_sha=fsha(TARGET)

    new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
    logic=next(x for x in new_core['planes'] if x.get('plane_id')=='LOGIC')
    logic['active_components']=sorted(set(logic.get('active_components',[])+[meta['component_id']]))
    logic['responsibilities']=sorted(set(logic.get('responsibilities',[])+['bounded_semantic_expression_synthesis']))
    new_core['active_runtime_sources']=sorted(set(new_core.get('active_runtime_sources',[])+[
        'runtime/yado_semantic_expression_synthesizer_v1.py'
    ]))
    new_core['mathematical_reasoning']={
        'component_id':meta['component_id'],
        'candidate_digest':meta['candidate_digest'],
        'source_sha256':component_sha,
        'fresh_admission_receipt_sha256':admit['receipt_sha256'],
        'fresh_score':admit.get('fresh_score'),
        'mode':'ACTIVE_BOUNDED_SEMANTIC_EXPRESSION_SYNTHESIS',
        'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
    }
    new_core['runtime_sha256']=runtime_sha
    new_core['current_frontier']='UNIFIED_CORE_POST_MATHEMATICAL_REASONING_SELF_AUDIT_V1'
    new_core['core_digest']=h(new_core)
    CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')

    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['new_capabilities']=sorted(set(new_head.get('new_capabilities',[])+[meta['component_id']]))
    new_head['unified_core']['runtime_sha256']=runtime_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['semantic_expression_synthesizer_source_sha256']=component_sha
    new_head['current_frontier']='UNIFIED_CORE_POST_MATHEMATICAL_REASONING_SELF_AUDIT_V1'
    new_head['canonical_head_digest']=h(new_head)
    HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    status='PASS_MATHEMATICAL_REASONING_CANONICAL_INTEGRATION_V1'
    next_cap='UNIFIED_CORE_POST_MATHEMATICAL_REASONING_SELF_AUDIT_V1'
else:
    try: TARGET.unlink()
    except FileNotFoundError: pass
    status='WITHHOLD_MATHEMATICAL_REASONING_CANONICAL_INTEGRATION_V1'
    next_cap='REAL_MATHEMATICAL_REASONING_SEARCH_EVOLUTION_V2'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
    'schema':'yado.g2.mathematical_reasoning_canonical_integration.v1',
    'status':status,
    'candidate_digest':meta['candidate_digest'],
    'candidate_source_sha256':meta['candidate_source_sha256'],
    'fresh_admission_receipt':admit['receipt_sha256'],
    'checks':checks,'source_safety':source_safety,
    'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,
    'g3_genesis_performed':False,
    'post_head_digest':post_head,'post_core_digest':post_core,
    'next_required_capability':next_cap,
    'semantic_boundary':'SAME-GENERATION CANONICALIZATION OF A BOUNDED SEMANTIC-EXPRESSION SYNTHESIZER. NOT GENERAL THEOREM PROVING, AGI, OR SUBJECTIVE CONSCIOUSNESS.'
}
receipt['receipt_sha256']=h(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={
    'index':len(ledger['events']),
    'event_id':f"E{len(ledger['events'])+1:04d}_G2_MATHEMATICAL_REASONING_CANONICAL_INTEGRATION",
    'event_type':'GENERATION_INTERNAL_SELF_EVOLVED_CODE_ADMISSION',
    'status':'PASS' if passed else 'WITHHOLD',
    'generation':ledger['current_head'],
    'deficit':'REAL_MATHEMATICAL_REASONING_CANONICAL_INTEGRATION_V1',
    'effect':'SEMANTIC_EXPRESSION_SYNTHESIZER_BOUND_TO_UNIFIED_CORE' if passed else 'MATHEMATICAL_REASONING_CANONICAL_INTEGRATION_WITHHELD',
    'source_path':f'receipts/yado-mathematical-reasoning-canonical-integration-v1-run-{run_id}.json',
    'source_digest':receipt['receipt_sha256'],'run_id':run_id,
    'parent_event_hash':ledger['tail_event_hash'],
    'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False
}
if passed:
    e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e)
ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed: ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
    'status':status,'checks':checks,'post_head_digest':post_head,
    'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:
    raise SystemExit('MATHEMATICAL_REASONING_CANONICAL_INTEGRATION_WITHHELD')
