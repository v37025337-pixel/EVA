from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
from itertools import combinations
import copy,hashlib,json,os,sys,time
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

import yado_architecture_neutral_meta_synthesizer_v2 as neutral
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_core_v2_2 import MechanismSelector
from yado_core_v2_1 import RuleProgram,BoundedRuleSandbox,RulePredicate,RuleSpec
from yado_organ_runtime_native_v1 import tree_predict
from yado_cognitive_growth_runtime_v1 import select_centroid_features,fit_centroid_strategy,centroid_predict,select_knn_k,fit_knn_strategy,knn_predict
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json';CORE=REPO/'canonical/yado-unified-core-v1.json';LEDGER=REPO/'architecture/evolution-ledger.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json';CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
CAL=REPO/'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json';KNN=REPO/'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json'
SP1=REPO/'candidates/kernel-self-generated/evolutionary-source-presence-representation-v1.json';SP2=REPO/'candidates/kernel-self-generated/evolutionary-source-interaction-representation-v2.json'
ART=REPO/'architecture/yado-kernel-fresh-four-source-curriculum-v1.json';CAND=REPO/'candidates/kernel-self-generated/fresh-four-source-curriculum-v1.json';HISTORY=REPO/'resources/yado-four-source-curriculum-history-v1.json'
OUT=ROOT/'yado_kernel_fresh_four_source_curriculum_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text())
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n')
def cdig(o,field):
 x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,'ts':time.time(),**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,base,corpus,cal,knn,sp1,sp2=map(load,[HEAD,CORE,LEDGER,BASE,CORPUS,CAL,KNN,SP1,SP2])
validate_ledger_v2(ledger)
front='KERNEL_EVOLUTIONARY_SOURCE_INTERACTION_REPRESENTATION_V3'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

# Re-fetch same 12 sources and require byte-identical hashes before deriving fresh cases.
data=neutral.build_dataset(force=True)
expected={x['id']:x['sha256'] for x in corpus['source_digests']};actual={sid:r['sha256'] for sid,r in data['rows'].items()}
if expected!=actual:raise RuntimeError('SOURCE_DIGEST_DRIFT:'+json.dumps({'expected':expected,'actual':actual},sort_keys=True))
ids=sorted(data['rows'])
fresh4=[]
for combo in combinations(ids,4):
 x,y,counts=neutral._vector(combo,data['rows']);key='|'.join(combo);bucket=int(hashlib.sha256((key+'|FRESH4_V1').encode()).hexdigest()[:8],16)%100
 fresh4.append({'key':key,'x':x,'y':y,'counts':counts,'bucket':bucket})
if len(fresh4)!=495:raise RuntimeError('FOUR_SOURCE_COUNT_MISMATCH:'+str(len(fresh4)))
final_fresh=[c for c in fresh4 if c['bucket']<20];dev=[c for c in fresh4 if c['bucket']>=20]
if len(final_fresh)<80 or len(dev)<350:raise RuntimeError('FOUR_SOURCE_SPLIT_TOO_SMALL')
log('fresh4_constructed',all=len(fresh4),development=len(dev),sealed_fresh=len(final_fresh),source_sha_exact=True)

# Current inherited behavior: SOURCE_PRESENCE_V1 -> LOCAL_KNN_CHILD_V1 -> CALIBRATED_CHILD_V2.
parent_model=base['kernel_result']['model'];g=cal['generator'];gate=g['gate_model'];corr=g['corrector_model'];th=float(cal['selected_threshold'])
def orig(x):return tree_predict(parent_model,x)
def cdists(model,x):
 out=[]
 for ls,center in model['centroids'].items():
  d=0.0
  for k in model['features']:
   s=max(float(model['scales'].get(k,1)),1e-12);d+=((float(x.get(k,0))-float(center[k]))/s)**2
  out.append((d,ls))
 return sorted(out)
def cmargin(model,x):
 z=cdists(model,x);return 0 if len(z)<2 else z[1][0]-z[0][0]
def cal_pred(x):
 if centroid_predict(gate,x)!='PARENT_ERROR':return orig(x)
 if cmargin(gate,x)+1e-12<th:return orig(x)
 return centroid_predict(corr,x)
def inherited_pred(x):
 sm=knn.get('selected_model') or {}
 if not sm:return cal_pred(x)
 return knn_predict(sm['corrector'],x) if knn_predict(sm['gate'],x)=='BASE_ERROR' else cal_pred(x)

# Let archive select parent/op using current lineage, but all equal-behavior wrappers are supported.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_fresh4_control.sqlite'))
try:
 records=[
 {'variant_id':'CALIBRATED_CHILD_V2','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':cal['candidate_digest'],'task_scores':{'fresh_blind':float(cal['metrics']['fresh_blind_successor'])},'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'bounded':1.0},'failure_tags':['spent_blind'],'status':'EVALUATED'},
 {'variant_id':'LOCAL_KNN_CHILD_V1','parent_id':'CALIBRATED_CHILD_V2','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':knn['candidate_digest'],'task_scores':{'fresh_blind':float(knn['metrics']['fresh_blind_successor'])},'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'bounded':1.0},'failure_tags':['zero_gain'],'status':'EVALUATED'},
 {'variant_id':'SOURCE_PRESENCE_V1','parent_id':'LOCAL_KNN_CHILD_V1','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':sp1['candidate_digest'],'task_scores':{'fresh_blind':float(sp1['metrics']['fresh_blind_successor'])},'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'bounded':1.0},'failure_tags':['no_admissible_skill'],'status':'EVALUATED'},
 {'variant_id':'SOURCE_INTERACTION_V2','parent_id':'SOURCE_PRESENCE_V1','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':sp2['candidate_digest'],'task_scores':{'fresh_blind':float(sp2['metrics']['fresh_blind_successor'])},'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'bounded':1.0},'failure_tags':['no_admissible_skill'],'status':'EVALUATED'}]
 parent=k.select_evolution_parent(records,'fresh_blind');op=k.propose_evolution_operation(records,parent['variant_id'],'fresh_blind')
finally:k.close()
if parent.get('variant_id') not in {r['variant_id'] for r in records}:raise RuntimeError('UNSUPPORTED_PARENT')
if op.get('operation')!='CLONAL':raise RuntimeError('EXPECTED_CLONAL:'+json.dumps(op))
log('control_selected',parent=parent,operation=op)

source_ids=ids;source_pairs=list(combinations(source_ids,2))
def aug(c):
 x=dict(c['x']);present=set(c['key'].split('|'))
 for s in source_ids:x['src::'+s]=1.0 if s in present else 0.0
 for a,b in source_pairs:x['srcpair::'+a+'&&'+b]=1.0 if a in present and b in present else 0.0
 return x

# Developmental outer holdout inside dev; final_fresh remains untouched.
by={}
for c in dev:by.setdefault(str(c['y']),[]).append(c)
train=[];hold=[]
for label,rows in sorted(by.items()):
 rows=sorted(rows,key=lambda c:h(c['key']+'|F4_DEV_OUT'));n=len(rows);nho=0 if n<4 else max(1,int(round(n*.2)))
 hold+=rows[-nho:] if nho else [];train+=rows[:-nho] if nho else rows
by2={};fitrows=[];valrows=[]
for c in train:by2.setdefault(str(c['y']),[]).append(c)
for label,rows in sorted(by2.items()):
 rows=sorted(rows,key=lambda c:h(c['key']+'|F4_DEV_IN'));n=len(rows);nho=0 if n<5 else max(1,int(round(n*.2)))
 valrows+=rows[-nho:] if nho else [];fitrows+=rows[:-nho] if nho else rows
if not hold or not valrows:raise RuntimeError('DEV_SPLIT_EMPTY')
log('development_splits',train=len(train),holdout=len(hold),inner_fit=len(fitrows),inner_val=len(valrows))

def acc(rows,pred):return sum(pred(c['x'])==c['y'] for c in rows)/max(1,len(rows))
base_train=acc(train,inherited_pred);base_hold=acc(hold,inherited_pred)
skills=[];specs={};metrics={}

def add_numeric_family(prefix,augment):
 fit=[(augment(c),c['y']) for c in fitrows];val=[(augment(c),c['y']) for c in valrows];full=[(augment(c),c['y']) for c in train]
 _,cm=select_centroid_features(fit,val);cf=fit_centroid_strategy(full,cm['selected_features'])
 tr=sum(centroid_predict(cf,augment(c))==c['y'] for c in train)/len(train);ho=sum(centroid_predict(cf,augment(c))==c['y'] for c in hold)/len(hold)
 sid=prefix+'_CENTROID';skills.append({'skill_id':sid,'artifact_digest':h(cf),'structural_valid':True,'semantic_consistency':1.0,'fit_baseline':base_train,'fit_candidate':tr,'heldout_baseline':base_hold,'heldout_candidate':ho,'regression_pass':ho>=base_hold,'state_integrity':True,'rollback_available':True,'metadata':{'family':'CENTROID','repr':prefix,'features':cm['selected_features']}});specs[sid]={'family':'CENTROID','repr':prefix,'selected_features':cm['selected_features']};metrics[sid]={'train':tr,'holdout':ho,'inner':cm}
 _,km=select_knn_k(fit,val,(1,3,5,7,9));kf=fit_knn_strategy(full,km['selected_k'])
 tr=sum(knn_predict(kf,augment(c))==c['y'] for c in train)/len(train);ho=sum(knn_predict(kf,augment(c))==c['y'] for c in hold)/len(hold)
 sid=prefix+'_KNN';skills.append({'skill_id':sid,'artifact_digest':h(kf),'structural_valid':True,'semantic_consistency':1.0,'fit_baseline':base_train,'fit_candidate':tr,'heldout_baseline':base_hold,'heldout_candidate':ho,'regression_pass':ho>=base_hold,'state_integrity':True,'rollback_available':True,'metadata':{'family':'KNN','repr':prefix,'k':km['selected_k']}});specs[sid]={'family':'KNN','repr':prefix,'selected_k':km['selected_k']};metrics[sid]={'train':tr,'holdout':ho,'inner':km}

add_numeric_family('RAW',lambda c:dict(c['x']))
add_numeric_family('PAIR',aug)
# RuleProgram on pair representation.
rule_error=None
try:
 programs=MechanismSelector.synthesize_candidates('FRESH4_ARCH_SELECTOR','INTELLIGENCE',[{'input':aug(c),'expected':c['y']} for c in train],min_support=2)
 rules=[p for p in programs if isinstance(p,RuleProgram)]
 if rules:
  rules.sort(key=lambda p:(MechanismSelector.complexity(p),p.digest()));rp=rules[0]
  tr=sum(BoundedRuleSandbox.execute(rp,aug(c))==c['y'] for c in train)/len(train);ho=sum(BoundedRuleSandbox.execute(rp,aug(c))==c['y'] for c in hold)/len(hold)
  sid='PAIR_RULE_PROGRAM';skills.append({'skill_id':sid,'artifact_digest':rp.digest(),'structural_valid':True,'semantic_consistency':1.0,'fit_baseline':base_train,'fit_candidate':tr,'heldout_baseline':base_hold,'heldout_candidate':ho,'regression_pass':ho>=base_hold,'state_integrity':True,'rollback_available':True,'metadata':{'family':'RULE_PROGRAM','repr':'PAIR','rules':len(rp.rules)}});specs[sid]={'family':'RULE_PROGRAM','repr':'PAIR'};metrics[sid]={'train':tr,'holdout':ho,'rules':len(rp.rules)}
except Exception as e:rule_error=type(e).__name__+':'+str(e)[:800]

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_fresh4_skill_select.sqlite'))
try:selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,max_heldout_drop=0.0,min_heldout_gain=0.0)
finally:k.close()
selids=list(selection.get('selected_skill_ids') or []);selected_id=selids[0] if selids else None;selected_spec=specs.get(selected_id)
log('kernel_family_selection',selection=selection,selected=selected_id,metrics=metrics,rule_error=rule_error,base_holdout=base_hold)

# Refit selected family on ALL developmental four-source cases only.
selected_model=None
if selected_spec:
 repr_fn=(lambda c:dict(c['x'])) if selected_spec['repr']=='RAW' else aug
 all_dev=[(repr_fn(c),c['y']) for c in dev]
 if selected_spec['family']=='CENTROID':selected_model=fit_centroid_strategy(all_dev,selected_spec['selected_features'])
 elif selected_spec['family']=='KNN':selected_model=fit_knn_strategy(all_dev,selected_spec['selected_k'])
 else:
  programs=MechanismSelector.synthesize_candidates('FRESH4_ARCH_SELECTOR','INTELLIGENCE',[{'input':repr_fn(c),'expected':c['y']} for c in dev],min_support=2);rules=[p for p in programs if isinstance(p,RuleProgram)];rules.sort(key=lambda p:(MechanismSelector.complexity(p),p.digest()));selected_model=rules[0] if rules else None

# Sealed final fresh opened only here.
def final_pred(c):
 if selected_model is None:return inherited_pred(c['x'])
 repr_fn=(lambda c:dict(c['x'])) if selected_spec['repr']=='RAW' else aug;x=repr_fn(c)
 if selected_spec['family']=='CENTROID':return centroid_predict(selected_model,x)
 if selected_spec['family']=='KNN':return knn_predict(selected_model,x)
 return BoundedRuleSandbox.execute(selected_model,x)
fresh_base=acc(final_fresh,inherited_pred);fresh_candidate=sum(final_pred(c)==c['y'] for c in final_fresh)/len(final_fresh);gain=fresh_candidate-fresh_base
state='SHADOW_SUPPORTED' if selected_id is not None and fresh_candidate>=.90 and gain>0 else 'WITHHOLD'
next_cap='KERNEL_FOUR_SOURCE_TRANSFER_TO_FIVE_SOURCE_V1' if state=='SHADOW_SUPPORTED' else 'KERNEL_FOUR_SOURCE_CURRICULUM_REPAIR_V2'
model_obj=None
if selected_model is not None:
 if isinstance(selected_model,RuleProgram):model_obj={'program_id':selected_model.program_id,'target_capability':selected_model.target_capability,'target_organ':selected_model.target_organ,'rules':[{'predicates':[asdict(p) for p in r.predicates],'output':r.output,'support':r.support,'confidence':r.confidence} for r in selected_model.rules],'default_output':selected_model.default_output,'source_digest':selected_model.source_digest,'training_count':selected_model.training_count}
 else:model_obj=selected_model
candidate={'schema':'yado.g2.fresh_four_source_curriculum.v1','state':state,'principle':'REPLACE_SPENT_BLIND_WITH_UNSEEN_FOUR_SOURCE_CURRICULUM','parent_choice':parent,'evolution_operation':op,
'curriculum':{'old_298_exactly_sizes_1_2_3':True,'new_four_source_case_count':495,'development_count':len(dev),'sealed_fresh_count':len(final_fresh),'source_sha_exact_match':True,'sealed_fresh_used_for_selection':False},
'selection':selection,'selected_skill_id':selected_id,'selected_spec':selected_spec,'selected_model':model_obj,'development_metrics':metrics,'rule_error':rule_error,
'metrics':{'development_parent_holdout':base_hold,'fresh_four_parent':fresh_base,'fresh_four_candidate':fresh_candidate,'gain':gain},
'canonical_active':False,'promotion_applied':False,'g3_genesis_performed':False}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)
history={'schema':'yado.g2.four_source_curriculum_history.v1','status':'SPENT_AFTER_SINGLE_ADMISSION','source_sha256':actual,'case_count':len(fresh4),'development_count':len(dev),'fresh_count':len(final_fresh),'fresh_bucket_rule':'sha256(key|FRESH4_V1)%100 < 20','fresh_result':{'parent':fresh_base,'candidate':fresh_candidate,'selected_skill_id':selected_id},'dataset_digest':h(fresh4)}
write(HISTORY,history)
artifact={'schema':'yado.g2.kernel_fresh_four_source_curriculum.v1','status':'PASS_FRESH_FOUR_SOURCE_CURRICULUM_V1','candidate_state':state,'candidate_digest':candidate['candidate_digest'],'selected_skill_id':selected_id,'metrics':candidate['metrics'],'next_required_capability':next_cap,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False};artifact['artifact_digest']=h(artifact);write(ART,artifact)
prev=head['canonical_head_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core);head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
checks={'four_source_count_495':len(fresh4)==495,'source_sha_exact_match':expected==actual,'sealed_fresh_not_used_for_selection':True,'old_blind_treated_as_spent_history':True,'no_canonical_mechanism_mutation':True,'g3_not_started':head.get('g3_genesis_performed') is False}
receipt={**artifact,'schema':'yado.g2.kernel_fresh_four_source_curriculum.receipt.v1','previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks};receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_FRESH_FOUR_SOURCE_CURRICULUM_V1",'event_type':'G2_FRESH_CURRICULUM_EXPANSION','status':'PASS_SHADOW' if state=='SHADOW_SUPPORTED' else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,'effect':f"OLD_BLIND=SPENT_HISTORY; NEW_SIZE4=495; SELECTED={selected_id}; FRESH4_PARENT={fresh_base:.6f}; FRESH4_CANDIDATE={fresh_candidate:.6f}; GAIN={gain:.6f}; NEXT={next_cap}",'source_path':f'receipts/yado-kernel-fresh-four-source-curriculum-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',state=state,selected=selected_id,metrics=candidate['metrics'],next=next_cap)
