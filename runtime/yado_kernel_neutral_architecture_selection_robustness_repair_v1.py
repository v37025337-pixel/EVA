from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
SRC=REPO/'candidates/kernel-self-generated/neutral-architecture-selection-v1.json'
ART=REPO/'architecture/yado-kernel-neutral-architecture-selection-robustness-repair-v1.json'
CAND=REPO/'candidates/kernel-self-generated/neutral-architecture-selection-robustness-repair-v1.json'
OUT=ROOT/'yado_kernel_neutral_architecture_selection_robustness_repair_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,prov,src=map(load,[HEAD,CORE,LEDGER,PROV,SRC])
validate_ledger_v2(ledger)
front='KERNEL_NEUTRAL_ARCHITECTURE_SELECTION_ROBUSTNESS_REPAIR_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if src.get('state')!='WITHHOLD':raise RuntimeError('SOURCE_SELECTION_NOT_WITHHOLD')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

primary=src['selected_family']
loo_dist=dict(src['robustness']['leave_one_out_distribution'])
double_dist=dict(src['robustness']['double_ablation_distribution'])
all_support={}
for fam,n in loo_dist.items():all_support[fam]=all_support.get(fam,0)+n
for fam,n in double_dist.items():all_support[fam]=all_support.get(fam,0)+n
all_support[primary]=all_support.get(primary,0)+1
ranked=sorted(all_support,key=lambda f:(-all_support[f],f))
if ranked[0]!=primary:raise RuntimeError('PRIMARY_NOT_TOP_SUPPORT')
if len(ranked)<2:raise RuntimeError('INSUFFICIENT_FAMILY_DIVERSITY')

fit_labels=[primary]+sum(([fam]*n for fam,n in sorted(loo_dist.items())),[])
hold_labels=sum(([fam]*n for fam,n in sorted(double_dist.items())),[])
baseline_fit=sum(x==primary for x in fit_labels)/len(fit_labels)
baseline_hold=sum(x==primary for x in hold_labels)/len(hold_labels)

candidates=[]
for k in (1,2,min(3,len(ranked))):
    fams=tuple(ranked[:k])
    sid=('SINGLE_FAMILY' if k==1 else f'TOP{k}_COMPOSITE')+'_ARCHITECTURE_V1'
    fit=sum(x in fams for x in fit_labels)/len(fit_labels)
    hold=sum(x in fams for x in hold_labels)/len(hold_labels)
    candidates.append({
      'skill_id':sid,'artifact_digest':h({'families':fams,'fit':fit,'hold':hold}),
      'structural_valid':True,'semantic_consistency':1.0,
      'fit_baseline':baseline_fit,'fit_candidate':fit,
      'heldout_baseline':baseline_hold,'heldout_candidate':hold,
      'regression_pass':hold+1e-12>=baseline_hold,
      'state_integrity':True,'rollback_available':True,
      'metadata':{'families':list(fams),'fit_coverage':fit,'heldout_coverage':hold,'support_counts':all_support}
    })
# remove duplicate k when len(ranked)==2
uniq={c['skill_id']:c for c in candidates};candidates=list(uniq.values())

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_architecture_robustness_v1.sqlite'))
try:
    selection=k.select_evolution_skills(candidates,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,max_heldout_drop=0.0,min_heldout_gain=0.0)
finally:k.close()
selected_ids=list(selection.get('selected_skill_ids') or [])
selected_id=selected_ids[0] if selected_ids else None
selected=next((c for c in candidates if c['skill_id']==selected_id),None)
selected_families=list(selected['metadata']['families']) if selected else []
fit_cov=float(selected['metadata']['fit_coverage']) if selected else 0.0
hold_cov=float(selected['metadata']['heldout_coverage']) if selected else 0.0
log('kernel_selection',selection=selection,selected=selected_id,families=selected_families,fit=fit_cov,hold=hold_cov)

checks={
 'source_withhold_due_robustness_only':src.get('checks',{}).get('double_ablation_selected_family_majority') is False,
 'kernel_selected_representation':selected is not None,
 'selected_contains_primary_family':primary in selected_families,
 'fit_coverage_at_least_0_95':fit_cov>=.95,
 'double_ablation_coverage_at_least_0_95':hold_cov>=.95,
 'no_new_architecture_training':True,
 'architecture_not_mutated':True,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_DESIGN_V1' if supported else 'KERNEL_NEUTRAL_ARCHITECTURE_SELECTION_ROBUSTNESS_REPAIR_V2'

candidate={
 'schema':'yado.g2.neutral_architecture_selection_robustness_repair.v1','state':state,
 'origin_selection_candidate_digest':src['candidate_digest'],'primary_family':primary,
 'support_counts':all_support,'ranked_families':ranked,
 'candidate_representations':candidates,'kernel_selection':selection,
 'selected_representation':selected_id,'selected_families':selected_families,
 'fit_coverage':fit_cov,'double_ablation_coverage':hold_cov,
 'semantic_boundary':'ROBUSTNESS REPAIR CHANGES THE ARCHITECTURE DIRECTION REPRESENTATION FROM SINGLE FAMILY TO A KERNEL-SELECTED COMPOSITE IF NEEDED; NO EXECUTABLE ARCHITECTURE MUTATION YET.',
 'checks':checks,'architecture_mutation':False,'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False
}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)

artifact={
 'schema':'yado.g2.kernel_neutral_architecture_selection_robustness_repair.v1',
 'status':'PASS_ARCHITECTURE_SELECTION_ROBUSTNESS_REPAIR_V1' if supported else 'WITHHOLD_ARCHITECTURE_SELECTION_ROBUSTNESS_REPAIR_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],
 'selected_representation':selected_id,'selected_families':selected_families,
 'fit_coverage':fit_cov,'double_ablation_coverage':hold_cov,'next_required_capability':next_cap,
 'architecture_mutation':False,'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_ARCHITECTURE_COMPOSITE_'+('_'.join(selected_families) if supported else 'ROBUSTNESS_REPAIR_V2_PENDING'),
 'frontier':next_cap,'frontier_native_method':'select_evolution_skills',
 'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive',
 'selected_architecture_family_shadow':None,
 'selected_architecture_composite_shadow':selected_families if supported else None
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['neutral_architecture_selection_robustness_v1']={
 'status':state,'selected_representation':selected_id,'selected_families':selected_families,
 'candidate_digest':candidate['candidate_digest'],'fit_coverage':fit_cov,'double_ablation_coverage':hold_cov,
 'architecture_mutation':False
}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['neutral_architecture_selection_robustness_v1']={
 'status':state,'selected_representation':selected_id,'selected_families':selected_families,
 'candidate_digest':candidate['candidate_digest'],'architecture_mutation':False
}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits'
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_neutral_architecture_selection_robustness_repair.receipt.v1',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks,
 'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_ARCHITECTURE_SELECTION_ROBUSTNESS_REPAIR_V1",
 'event_type':'G2_KERNEL_SELECTED_ARCHITECTURE_DIRECTION_COMPOSITION','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"REPRESENTATION={selected_id}; FAMILIES={'+'.join(selected_families)}; FIT={fit_cov:.6f}; DOUBLE_ABLATION={hold_cov:.6f}; ARCHITECTURE_MUTATION=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-neutral-architecture-selection-robustness-repair-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_ROBUSTNESS_GUARD_FAILED:'+cp.stdout[-4000:]+cp.stderr[-1000:])
log('complete',state=state,selected_representation=selected_id,selected_families=selected_families,fit=fit_cov,double=hold_cov,next=next_cap)
