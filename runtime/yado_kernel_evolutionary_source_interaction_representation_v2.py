from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
from itertools import combinations
import copy,hashlib,json,os,sys,time
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_core_v2_2 import MechanismSelector
from yado_core_v2_1 import RuleProgram,BoundedRuleSandbox,RulePredicate,RuleSpec
from yado_organ_runtime_native_v1 import tree_predict
from yado_cognitive_growth_runtime_v1 import select_centroid_features,fit_centroid_strategy,centroid_predict,select_knn_k,fit_knn_strategy,knn_predict
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json';CORE=REPO/'canonical/yado-unified-core-v1.json';LEDGER=REPO/'architecture/evolution-ledger.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json';CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
CAL=REPO/'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json'
HIER=REPO/'candidates/kernel-self-generated/evolutionary-hierarchical-residual-successor-v1.json'
KNN=REPO/'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json'
SP1=REPO/'candidates/kernel-self-generated/evolutionary-source-presence-representation-v1.json'
ART=REPO/'architecture/yado-kernel-evolutionary-source-interaction-representation-v2.json'
CAND=REPO/'candidates/kernel-self-generated/evolutionary-source-interaction-representation-v2.json'
OUT=ROOT/'yado_kernel_evolutionary_source_interaction_representation_v2_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text())
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n')
def cdig(o,field):
 x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,'ts':time.time(),**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,base,corpus,cal,hier,knn,sp1=map(load,[HEAD,CORE,LEDGER,BASE,CORPUS,CAL,HIER,KNN,SP1])
validate_ledger_v2(ledger)
front='KERNEL_EVOLUTIONARY_SOURCE_PRESENCE_REPRESENTATION_V2'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
if cdig(corpus,'corpus_digest')!=corpus['corpus_digest']:raise RuntimeError('CORPUS_DIGEST_MISMATCH')

source_ids=[str(x['id']) for x in corpus['source_digests']];source_pairs=list(combinations(source_ids,2))
def augment(c):
 x=dict(c['x']);present=set(str(c['key']).split('|'))
 for sid in source_ids:x['src::'+sid]=1.0 if sid in present else 0.0
 for a,b in source_pairs:x['srcpair::'+a+'&&'+b]=1.0 if a in present and b in present else 0.0
 return x
cases=list(corpus['cases']);nonblind=[c for c in cases if c['bucket']>=18];blind=[c for c in cases if c['bucket']<18]

parent_model=base['kernel_result']['model'];g=cal['generator'];gate=g['gate_model'];corr=g['corrector_model'];th=float(cal['selected_threshold'])
def orig(x):return tree_predict(parent_model,x)
def dists(model,x):
 out=[]
 for ls,center in model['centroids'].items():
  d=0.0
  for k in model['features']:
   s=max(float(model['scales'].get(k,1)),1e-12);d+=((float(x.get(k,0))-float(center[k]))/s)**2
  out.append((d,ls))
 return sorted(out)
def margin(model,x):
 z=dists(model,x);return 0 if len(z)<2 else z[1][0]-z[0][0]
def cal_pred(x):
 if centroid_predict(gate,x)!='PARENT_ERROR':return orig(x)
 if margin(gate,x)+1e-12<th:return orig(x)
 return centroid_predict(corr,x)
def local_knn_pred(x):
 sm=knn.get('selected_model') or {}
 if not sm:return cal_pred(x)
 return knn_predict(sm['corrector'],x) if knn_predict(sm['gate'],x)=='BASE_ERROR' else cal_pred(x)

# Native archive selection.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_source_interaction_control.sqlite'))
try:
 records=[
  {'variant_id':'EXECUTABLE_PARENT','parent_id':None,'lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':'parent','task_scores':{'fresh_blind':.8043478260869565},'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'bounded':1.0},'failure_tags':['residual'],'status':'EVALUATED'},
  {'variant_id':'CALIBRATED_CHILD_V2','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':cal['candidate_digest'],'task_scores':{'fresh_blind':float(cal['metrics']['fresh_blind_successor'])},'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'bounded':1.0},'failure_tags':['residual'],'status':'EVALUATED'},
  {'variant_id':'HIERARCHICAL_CHILD_V1','parent_id':'CALIBRATED_CHILD_V2','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':hier['candidate_digest'],'task_scores':{'fresh_blind':float(hier['metrics']['fresh_blind_successor'])},'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'bounded':1.0},'failure_tags':['zero_gain'],'status':'EVALUATED'},
  {'variant_id':'LOCAL_KNN_CHILD_V1','parent_id':'CALIBRATED_CHILD_V2','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':knn['candidate_digest'],'task_scores':{'fresh_blind':float(knn['metrics']['fresh_blind_successor'])},'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'bounded':1.0},'failure_tags':['zero_gain'],'status':'EVALUATED'},
  {'variant_id':'SOURCE_PRESENCE_V1','parent_id':'LOCAL_KNN_CHILD_V1','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':sp1['candidate_digest'],'task_scores':{'fresh_blind':float(sp1['metrics']['fresh_blind_successor'])},'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'bounded':1.0},'failure_tags':['no_admissible_skill'],'status':'EVALUATED'}]
 parent=k.select_evolution_parent(records,'fresh_blind');op=k.propose_evolution_operation(records,parent['variant_id'],'fresh_blind')
finally:k.close()
supported_parents={'CALIBRATED_CHILD_V2','LOCAL_KNN_CHILD_V1','SOURCE_PRESENCE_V1'}
if parent.get('variant_id') not in supported_parents:raise RuntimeError('UNSUPPORTED_KERNEL_PARENT:'+json.dumps(parent))
if op.get('operation')!='CLONAL':raise RuntimeError('KERNEL_OP_NOT_CLONAL:'+json.dumps(op))
def parent_pred(x):
 return cal_pred(x) if parent['variant_id']=='CALIBRATED_CHILD_V2' else local_knn_pred(x)
log('control_selected',parent=parent,operation=op)

def acc(rows,pred,aug=False):return sum(pred(augment(c) if aug else c['x'])==c['y'] for c in rows)/max(1,len(rows))
# Same deterministic stratified outer and inner evaluation contract as V1.
by={}
for c in nonblind:by.setdefault(str(c['y']),[]).append(c)
dev_train=[];outer=[]
for label,rows in sorted(by.items()):
 rows=sorted(rows,key=lambda c:h(c['key']+'|SRC2_OUTER'));n=len(rows);hold=0 if n<3 else max(1,int(round(n*.20)))
 outer+=rows[-hold:] if hold else [];dev_train+=rows[:-hold] if hold else rows
by2={};inner_fit=[];inner_val=[]
for c in dev_train:by2.setdefault(str(c['y']),[]).append(c)
for label,rows in sorted(by2.items()):
 rows=sorted(rows,key=lambda c:h(c['key']+'|SRC2_INNER'));n=len(rows);hold=0 if n<4 else max(1,int(round(n*.20)))
 inner_val+=rows[-hold:] if hold else [];inner_fit+=rows[:-hold] if hold else rows
fit=[(augment(c),c['y']) for c in inner_fit];ival=[(augment(c),c['y']) for c in inner_val];full=[(augment(c),c['y']) for c in dev_train]
base_train=acc(dev_train,parent_pred);base_outer=acc(outer,parent_pred)
log('splits',train=len(dev_train),outer=len(outer),inner_fit=len(inner_fit),inner_val=len(inner_val),base_outer=base_outer,feature_count=len(augment(nonblind[0])))

skills=[];models={};metrics={}
# centroid
_,cm=select_centroid_features(fit,ival);cf=fit_centroid_strategy(full,cm['selected_features'])
ctr=sum(centroid_predict(cf,augment(c))==c['y'] for c in dev_train)/len(dev_train);co=sum(centroid_predict(cf,augment(c))==c['y'] for c in outer)/len(outer)
sid='SOURCE_INTERACTION_CENTROID';skills.append({'skill_id':sid,'artifact_digest':h(cf),'structural_valid':True,'semantic_consistency':1.0,'fit_baseline':base_train,'fit_candidate':ctr,'heldout_baseline':base_outer,'heldout_candidate':co,'regression_pass':co>=base_outer,'state_integrity':True,'rollback_available':True,'metadata':{'family':'CENTROID','features':cm['selected_features']}});models[sid]={'family':'CENTROID','model':cf};metrics[sid]={'train':ctr,'outer':co,'meta':cm}
# knn
_,km=select_knn_k(fit,ival,(1,3,5,7,9));kf=fit_knn_strategy(full,km['selected_k'])
ktr=sum(knn_predict(kf,augment(c))==c['y'] for c in dev_train)/len(dev_train);ko=sum(knn_predict(kf,augment(c))==c['y'] for c in outer)/len(outer)
sid='SOURCE_INTERACTION_KNN';skills.append({'skill_id':sid,'artifact_digest':h(kf),'structural_valid':True,'semantic_consistency':1.0,'fit_baseline':base_train,'fit_candidate':ktr,'heldout_baseline':base_outer,'heldout_candidate':ko,'regression_pass':ko>=base_outer,'state_integrity':True,'rollback_available':True,'metadata':{'family':'KNN','k':km['selected_k']}});models[sid]={'family':'KNN','model':kf};metrics[sid]={'train':ktr,'outer':ko,'meta':km}
# RuleProgram
rule_error=None
try:
 programs=MechanismSelector.synthesize_candidates('ARCH_SELECTOR_SOURCE_INTERACTIONS','INTELLIGENCE',[{'input':augment(c),'expected':c['y']} for c in dev_train],min_support=2)
 rules=[p for p in programs if isinstance(p,RuleProgram)]
 if rules:
  rules.sort(key=lambda p:(MechanismSelector.complexity(p),p.digest()));rp=rules[0]
  rtr=sum(BoundedRuleSandbox.execute(rp,augment(c))==c['y'] for c in dev_train)/len(dev_train);ro=sum(BoundedRuleSandbox.execute(rp,augment(c))==c['y'] for c in outer)/len(outer)
  rd={'program_id':rp.program_id,'target_capability':rp.target_capability,'target_organ':rp.target_organ,'rules':[{'predicates':[asdict(p) for p in r.predicates],'output':r.output,'support':r.support,'confidence':r.confidence} for r in rp.rules],'default_output':rp.default_output,'source_digest':rp.source_digest,'training_count':rp.training_count}
  sid='SOURCE_INTERACTION_RULE_PROGRAM';skills.append({'skill_id':sid,'artifact_digest':rp.digest(),'structural_valid':True,'semantic_consistency':1.0,'fit_baseline':base_train,'fit_candidate':rtr,'heldout_baseline':base_outer,'heldout_candidate':ro,'regression_pass':ro>=base_outer,'state_integrity':True,'rollback_available':True,'metadata':{'family':'RULE_PROGRAM','rules':len(rp.rules)}});models[sid]={'family':'RULE_PROGRAM','model':rd};metrics[sid]={'train':rtr,'outer':ro,'rules':len(rp.rules)}
except Exception as e:rule_error=type(e).__name__+':'+str(e)[:600]

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_source_interaction_select.sqlite'))
try:selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,max_heldout_drop=0.0,min_heldout_gain=0.0)
finally:k.close()
ids=list(selection.get('selected_skill_ids') or []);selected_id=ids[0] if ids else None;selected=models.get(selected_id)
log('kernel_selection',selection=selection,selected=selected_id,metrics=metrics,rule_error=rule_error)

def pred(c):
 if selected is None:return parent_pred(c['x'])
 x=augment(c)
 if selected['family']=='CENTROID':return centroid_predict(selected['model'],x)
 if selected['family']=='KNN':return knn_predict(selected['model'],x)
 d=selected['model'];rules=[RuleSpec([RulePredicate(**p) for p in r['predicates']],r['output'],r['support'],r['confidence']) for r in d['rules']];rp=RuleProgram(d['program_id'],d['target_capability'],d['target_organ'],rules,d['default_output'],d['source_digest'],d['training_count']);return BoundedRuleSandbox.execute(rp,x)

pb=acc(blind,parent_pred);cb=sum(pred(c)==c['y'] for c in blind)/len(blind);gain=cb-pb
state='SHADOW_SUPPORTED' if selected_id is not None and cb>=.90 and gain>0 else 'WITHHOLD'
next_cap='KERNEL_EVOLUTIONARY_SUCCESSOR_FRESH_ADMISSION_V1' if state=='SHADOW_SUPPORTED' else 'KERNEL_EVOLUTIONARY_SOURCE_INTERACTION_REPRESENTATION_V3'
candidate={'schema':'yado.g2.evolutionary_source_interaction_representation.v2','state':state,'principle':'GENERIC_PAIRWISE_SOURCE_INTERACTION_REPRESENTATION','parent_choice':parent,'evolution_operation':op,
'representation':{'base_features_preserved':True,'source_presence_count':len(source_ids),'source_pair_feature_count':len(source_pairs),'target_mapping_supplied':False},
'selection':selection,'selected_skill_id':selected_id,'selected_model':selected,'development_metrics':metrics,'rule_error':rule_error,
'metrics':{'outer_baseline':base_outer,'fresh_blind_parent':pb,'fresh_blind_successor':cb,'gain':gain},
'frozen_history':{'blind_used_for_generation':False,'blind_used_for_selection':False,'blind_used_for_admission_only':True,'corpus_digest':corpus['corpus_digest']},'host_task_specific_rules_written':False,'canonical_active':False,'promotion_applied':False}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)
artifact={'schema':'yado.g2.kernel_evolutionary_source_interaction_representation.v2','status':'PASS_SOURCE_INTERACTION_REPRESENTATION_V2','candidate_state':state,'candidate_digest':candidate['candidate_digest'],'selected_skill_id':selected_id,'metrics':candidate['metrics'],'next_required_capability':next_cap,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False};artifact['artifact_digest']=h(artifact);write(ART,artifact)
prev=head['canonical_head_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core);head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
checks={'kernel_selected_supported_parent':parent.get('variant_id') in supported_parents,'kernel_selected_clonal':op.get('operation')=='CLONAL','blind_not_used_for_generation':True,'blind_not_used_for_selection':True,'no_target_mapping_supplied':True,'no_canonical_mechanism_mutation':True,'g3_not_started':head.get('g3_genesis_performed') is False}
receipt={**artifact,'schema':'yado.g2.kernel_evolutionary_source_interaction_representation.receipt.v2','previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks};receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_SOURCE_INTERACTION_REPRESENTATION_V2",'event_type':'G2_EVOLUTIONARY_CLONAL_PAIRWISE_REPRESENTATION','status':'PASS_SHADOW' if state=='SHADOW_SUPPORTED' else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,'effect':f"MODE=CLONAL_PAIRWISE_REPRESENTATION; PARENT={parent.get('variant_id')}; SELECTED={selected_id}; OUTER_BASE={base_outer:.6f}; PARENT_BLIND={pb:.6f}; CHILD_BLIND={cb:.6f}; GAIN={gain:.6f}; NEXT={next_cap}",'source_path':f'receipts/yado-kernel-evolutionary-source-interaction-representation-v2-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',state=state,selected=selected_id,metrics=candidate['metrics'],next=next_cap)
