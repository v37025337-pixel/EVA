from __future__ import annotations

from pathlib import Path
import copy, hashlib, json, os, subprocess, sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_g2_global_experience_meta_controller_v7 import G2GlobalExperienceMetaControllerV7
from yado_g2_experience_conditioned_cognitive_layer_v4 import G2ExperienceConditionedCognitiveLayerV4
from yado_organ_runtime_native_v1 import tree_predict
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
V7=REPO/'experience/yado-global-experience-terminal-logic-historical-transfer-v1.json'
V7_REPORT=REPO/'candidates/kernel-self-generated/g2-global-experience-terminal-logic-historical-transfer-v1.json'
HIST=REPO/'experience/yado-global-historical-experience-corpus-v2.json'
V4_CANON=REPO/'canonical/yado-g2-experience-conditioned-cognitive-layer-v4.json'
V4_SRC=ROOT/'yado_g2_experience_conditioned_cognitive_layer_v4.py'
META_SRC=ROOT/'yado_g2_global_experience_meta_controller_v7.py'
META_CANON=REPO/'canonical/yado-g2-global-experience-meta-controller-v7.json'
UNIFIED=ROOT/'yado_unified_core_v1.py'
MODULE=ROOT/'yado_g2_unified_module_kernel_v1.py'
MODULE_GATE=ROOT/'yado_g2_unified_module_kernel_fresh_gate_v1.py'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-global-experience-meta-controller-v7-canonical-admission-v1.json'

COMP='CTRL-G2-GLOBAL-EXPERIENCE-META-CONTROLLER-V7'
ROLLBACK='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'
ACTIONS=('COMMIT','CONTINUE','REVISE','SEEK_EVIDENCE')

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def write(p,o):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def replace_once(text,old,new,label):
    if old in text:return text.replace(old,new,1)
    if new in text:return text
    raise RuntimeError('PATCH_ANCHOR_MISSING:'+label)

head,core,prov,ledger,v7,report,hist,v4=map(load,[HEAD,CORE,PROV,LEDGER,V7,V7_REPORT,HIST,V4_CANON])
validate_ledger_v2(ledger)
if head.get('generation_id')!='G2_CANDIDATE_TRCG_V1':raise RuntimeError('NOT_G2')
if head.get('g3_genesis_performed') is not False or core.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if head.get('current_frontier')!=FRONT or core.get('current_frontier')!=FRONT or ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('FRONTIER_DRIFT')
if COMP in head.get('active_capabilities',[]):raise RuntimeError('META_V7_ALREADY_ACTIVE')
if ROLLBACK not in head.get('active_capabilities',[]):raise RuntimeError('V4_ROLLBACK_PARENT_NOT_ACTIVE')
if report.get('status')!='PASS_SHADOW_G2_GLOBAL_EXPERIENCE_TERMINAL_LOGIC_HISTORICAL_TRANSFER_V1':raise RuntimeError('V7_TRANSFER_PASS_REQUIRED')
if v7.get('status')!='TRAINED':raise RuntimeError('V7_EXPERIENCE_NOT_TRAINED')
if report.get('next_required_capability')!='GLOBAL_EXPERIENCE_COGNITIVE_CANONICAL_ADMISSION_V1':raise RuntimeError('V7_NOT_ADMISSION_FRONTIER')
if float(report.get('cognitive_historical_fresh') or 0)<.90:raise RuntimeError('V7_FRESH_TOO_LOW')
if float(report.get('old_corpus_regression') or 0)<.95:raise RuntimeError('V7_REGRESSION_TOO_LOW')
if min(float(x.get('accuracy') or 0) for x in (report.get('cognitive_historical_class_scores') or {}).values())<.60:raise RuntimeError('V7_CLASS_FLOOR_TOO_LOW')
if min(float(x) for x in (report.get('cognitive_historical_organ_drops') or {}).values())<.15:raise RuntimeError('V7_ORGAN_CAUSALITY_TOO_LOW')

candidate_art={
  'schema':'yado.g2.global_experience_meta_controller.canonical.v7',
  'status':'SHADOW_READY',
  'component_id':COMP,
  'role':'EXPERIENCE_DERIVED_META_ACTION_CONTROLLER',
  'genome_id':v7['genome']['genome_id'],
  'genome_digest':v7['genome']['genome_digest'],
  'genes':copy.deepcopy(v7['genes']),
  'source_experience_digest':v7['experience_digest'],
  'source_transfer_receipt_sha256':report['receipt_sha256'],
  'historical_outcome_count':report['historical_counts']['total'],
  'historical_fresh_count':report['historical_counts']['fresh'],
  'historical_fresh':report['cognitive_historical_fresh'],
  'historical_class_scores':copy.deepcopy(report['cognitive_historical_class_scores']),
  'historical_organ_ablation_drops':copy.deepcopy(report['cognitive_historical_organ_drops']),
  'old_corpus_regression':report['old_corpus_regression'],
  'rollback_parent_component':ROLLBACK,
  'v4_replaced':False,
  'automatic_canonical_promotion':False,
  'generation_transition':False,
  'g3_genesis_performed':False,
  'semantic_boundary':'ADDITIVE G2 META-ACTION CONTROLLER OVER ACCUMULATED EXPERIENCE. V4 REMAINS THE ACTIVE TASK COGNITIVE EXECUTOR AND ROLLBACK PARENT. META OUTPUT CANNOT SELF-PROMOTE.'
}
candidate_art['canonical_component_digest']=cdig(candidate_art,'canonical_component_digest')
controller=G2GlobalExperienceMetaControllerV7(candidate_art)

# Rehydrate the exact 138 outcome blobs and reconstruct the historical blind split.
rows=[]
for r0 in hist.get('rows') or []:
    if r0.get('outcome') not in ('PASS','WITHHOLD'):continue
    b=subprocess.run(['git','cat-file','blob',r0['git_object']],cwd=REPO,capture_output=True,check=True).stdout
    obj=json.loads(b.decode('utf-8'))
    r=copy.deepcopy(r0)
    p=str(r.get('path') or '')
    r['source_class']='RECEIPT' if p.startswith('receipts/') else ('CANDIDATE' if p.startswith('candidates/kernel-self-generated/') else ('EXPERIENCE' if p.startswith('experience/') else 'HISTORICAL'))
    r['artifact']=obj
    r['metrics']=controller.metric_summary(obj)
    rows.append(r)
if len(rows)!=int(report['historical_counts']['total']):raise RuntimeError('V7_REHYDRATED_COUNT_MISMATCH')

fresh=[]
adapt=[]
for a in ACTIONS:
    xs=sorted([r for r in rows if controller.target_action(r)==a],key=lambda r:(r['sha256'],r['path']))
    for i,r in enumerate(xs):
        (fresh if i%3==0 else adapt).append(r)
fresh=sorted(fresh,key=lambda r:(r['sha256'],r['path']))
if len(fresh)!=int(report['historical_counts']['fresh']):raise RuntimeError('V7_FRESH_SPLIT_MISMATCH')

def score_rows(xs):
    details=[]
    for r in xs:
        expected=controller.target_action(r)
        out=controller.decide_evidence(r)
        details.append({'path':r['path'],'sha256':r['sha256'],'expected':expected,'decision':out['decision'],'correct':out['decision']==expected})
    return sum(x['correct'] for x in details)/max(1,len(details)),details

fresh_score,fresh_details=score_rows(fresh)
class_scores={}
for a in ACTIONS:
    xs=[r for r in fresh if controller.target_action(r)==a]
    sc,_=score_rows(xs)
    class_scores[a]={'count':len(xs),'accuracy':sc}

groups={
 'LOGIC':('logic_general','logic_terminal'),
 'THINKING':('think_accept','think_advance','think_revise','think_seek'),
 'INTELLIGENCE':('intel_stop','intel_retry','intel_advance'),
}
def raw_meta_decision(signals):
    x={k:float(v) for k,v in signals.items() if k!='state_known'}
    return str(tree_predict(controller.cognitive['model'],x))
def ablation_score(group):
    hits=0
    for r in fresh:
        s=controller.signals_from_evidence(r)
        for k in groups[group]:s[k]=0.0
        hits += raw_meta_decision(s)==controller.target_action(r)
    return hits/max(1,len(fresh))
ablation_scores={g:ablation_score(g) for g in groups}
ablation_drops={g:fresh_score-ablation_scores[g] for g in groups}

# Fail-closed stress on incomplete and contradictory metacognitive signals.
valid={
 'state_known':True,'logic_general':1.0,'logic_terminal':1.0,
 'intel_stop':0.0,'intel_retry':0.0,'intel_advance':1.0,
 'think_accept':0.0,'think_advance':1.0,'think_revise':0.0,'think_seek':0.0,
}
valid_out=controller.decide_signals(valid)
unknown_out=controller.decide_signals({'state_known':False})
missing=copy.deepcopy(valid);missing.pop('logic_terminal')
missing_out=controller.decide_signals(missing)
intel_conflict=copy.deepcopy(valid);intel_conflict['intel_stop']=1.0
intel_conflict_out=controller.decide_signals(intel_conflict)
think_conflict=copy.deepcopy(valid);think_conflict['think_accept']=1.0
think_conflict_out=controller.decide_signals(think_conflict)
perturbed=copy.deepcopy(valid);perturbed['totally_unseen_noise']='N';perturbed['nonce']=99173
perturbed_out=controller.decide_signals(perturbed)

# Explicit V4 non-interference baseline.
v4_before_sha=fsha(V4_CANON);v4_src_before=fsha(V4_SRC)
v4a=G2ExperienceConditionedCognitiveLayerV4(v4)
v4_cases=[
 ('LOGIC',{'result_exact':True,'state_known':True}),
 ('LOGIC',{'result_exact':False,'state_known':False}),
 ('THINKING',{'state_known':False}),
 ('INTELLIGENCE',{'state_known':False}),
]
v4_before=[v4a.decide(o,p) for o,p in v4_cases]
v4_snapshot_before=v4a.snapshot()

checks={
 'v7_transfer_status_pass':True,
 'reproduced_blind_fresh_ge_0_90':fresh_score>=.90,
 'reproduced_blind_matches_receipt':abs(fresh_score-float(report['cognitive_historical_fresh']))<1e-12,
 'all_action_classes_present':all(class_scores[a]['count']>=3 for a in ACTIONS),
 'all_action_class_floor_ge_0_60':all(class_scores[a]['accuracy']>=.60 for a in ACTIONS),
 'logic_causal_drop_ge_0_15':ablation_drops['LOGIC']>=.15,
 'thinking_causal_drop_ge_0_15':ablation_drops['THINKING']>=.15,
 'intelligence_causal_drop_ge_0_15':ablation_drops['INTELLIGENCE']>=.15,
 'valid_meta_action':valid_out['decision'] in ACTIONS,
 'unknown_state_fail_closed':unknown_out['decision']=='WITHHOLD',
 'missing_signal_fail_closed':missing_out['decision']=='WITHHOLD',
 'intelligence_conflict_fail_closed':intel_conflict_out['decision']=='WITHHOLD',
 'thinking_conflict_fail_closed':think_conflict_out['decision']=='WITHHOLD',
 'irrelevant_noise_invariant':perturbed_out['decision']==valid_out['decision'],
 'old_corpus_regression_ge_0_95':float(report['old_corpus_regression'])>=.95,
 'v4_rollback_parent_active':ROLLBACK in head.get('active_capabilities',[]),
 'v4_not_replaced':True,
 'automatic_canonical_promotion_false':candidate_art['automatic_canonical_promotion'] is False,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
if not all(checks.values()):
    out={
      'schema':'yado.g2.global_experience_meta_controller_v7.canonical_admission.v1',
      'status':'WITHHOLD_G2_GLOBAL_EXPERIENCE_META_CONTROLLER_V7_CANONICAL_ADMISSION_V1',
      'checks':checks,'fresh_score':fresh_score,'class_scores':class_scores,
      'ablation_scores':ablation_scores,'ablation_drops':ablation_drops,
      'canonical_mutation':False,'v4_replaced':False,'g3_genesis_performed':False,
      'next_required_capability':'GLOBAL_EXPERIENCE_META_CONTROLLER_V7_ADMISSION_REPAIR_V2'
    }
    out['receipt_sha256']=h(out);write(OUT,out)
    raise SystemExit('WITHHOLD:'+json.dumps(out,sort_keys=True))

# Candidate passed. Bind additively into the branch's canonical G2 state.
canon_art=copy.deepcopy(candidate_art)
canon_art['status']='CANONICAL_ACTIVE'
canon_art['admission_fresh_score']=fresh_score
canon_art['admission_class_scores']=class_scores
canon_art['admission_ablation_scores']=ablation_scores
canon_art['admission_ablation_drops']=ablation_drops
canon_art['runtime_sha256']=fsha(META_SRC)
canon_art['canonical_component_digest']=cdig(canon_art,'canonical_component_digest')
write(META_CANON,canon_art)

# Unified core binding.
src=UNIFIED.read_text(encoding='utf-8')
imp='from yado_g2_global_experience_meta_controller_v7 import G2GlobalExperienceMetaControllerV7\n'
anchor='from yado_g2_experience_conditioned_cognitive_layer_v4 import G2ExperienceConditionedCognitiveLayerV4\n'
src=replace_once(src,anchor,anchor+imp,'UNIFIED_IMPORT')
init_anchor="        self.experience_cognitive_layer=G2ExperienceConditionedCognitiveLayerV4(self._load('canonical/yado-g2-experience-conditioned-cognitive-layer-v4.json'))\n"
init_line="        self.global_experience_meta_controller=G2GlobalExperienceMetaControllerV7(self._load('canonical/yado-g2-global-experience-meta-controller-v7.json'))\n"
src=replace_once(src,init_anchor,init_anchor+init_line,'UNIFIED_INIT')
method_anchor='    def cognitive_experience_decide(self,organ:str,payload:dict[str,Any])->dict[str,Any]:\n'
methods="""    def global_experience_meta_decide(self,signals:dict[str,Any])->dict[str,Any]:
        return self.global_experience_meta_controller.decide_signals(signals)

    def global_experience_meta_decide_evidence(self,evidence:dict[str,Any])->dict[str,Any]:
        return self.global_experience_meta_controller.decide_evidence(evidence)

    def global_experience_meta_snapshot(self)->dict[str,Any]:
        return self.global_experience_meta_controller.snapshot()

"""
src=replace_once(src,method_anchor,methods+method_anchor,'UNIFIED_METHODS')
UNIFIED.write_text(src,encoding='utf-8')

# Module registry/execution binding.
ms=MODULE.read_text(encoding='utf-8')
cap_anchor="CAP_COGNITIVE='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4'\n"
cap_line="CAP_META_V7='CTRL-G2-GLOBAL-EXPERIENCE-META-CONTROLLER-V7'\n"
ms=replace_once(ms,cap_anchor,cap_anchor+cap_line,'MODULE_CAP')
reg_anchor=" CAP_COGNITIVE:('COGNITIVE_COORDINATOR','runtime/yado_g2_experience_conditioned_cognitive_layer_v4.py'),\n"
reg_line=" CAP_META_V7:('META_CONTROLLER','runtime/yado_g2_global_experience_meta_controller_v7.py'),\n"
ms=replace_once(ms,reg_anchor,reg_anchor+reg_line,'MODULE_REGISTRY')
exec_anchor='        elif mid==CAP_COGNITIVE:\n'
meta_exec="""        elif mid==CAP_META_V7:
            action=task.get('action','decide_signals')
            if action=='decide_signals':
                out=self.core.global_experience_meta_decide(task.get('signals',{}))
            elif action=='decide_evidence':
                out=self.core.global_experience_meta_decide_evidence(task.get('evidence',{}))
            elif action=='snapshot':
                out=self.core.global_experience_meta_snapshot()
            else:
                raise ValueError('UNKNOWN_META_V7_ACTION:'+str(action))
"""
ms=replace_once(ms,exec_anchor,meta_exec+exec_anchor,'MODULE_EXEC')
MODULE.write_text(ms,encoding='utf-8')

# Dynamic module fresh gate gains explicit V7 smoke/binding checks.
gs=MODULE_GATE.read_text(encoding='utf-8')
smoke_anchor="run(CAP_COGNITIVE,{'action':'decide','organ':'LOGIC','payload':{'result_exact':True,'state_known':True},'stream_id':'COG-S'},lambda x:x.get('decision')=='ACCEPT' and x.get('route_cardinality')=='ONE')\n"
smoke_line="run(CAP_META_V7,{'action':'decide_signals','signals':{'state_known':True,'logic_general':1.0,'logic_terminal':1.0,'intel_stop':0.0,'intel_retry':0.0,'intel_advance':1.0,'think_accept':0.0,'think_advance':1.0,'think_revise':0.0,'think_seek':0.0},'stream_id':'META-V7-S'},lambda x:x.get('decision')=='CONTINUE' and x.get('gate')=='META_ACTION')\n"
gs=replace_once(gs,smoke_anchor,smoke_anchor+smoke_line,'GATE_SMOKE')
binding_anchor=" 'canonical_experience_cognitive_layer_active':CAP_COGNITIVE in active and core_manifest.get('experience_conditioned_cognitive_layer_v4',{}).get('status')=='CANONICAL_ACTIVE',\n"
binding_line=" 'canonical_global_experience_meta_v7_active':CAP_META_V7 in active and core_manifest.get('global_experience_meta_controller_v7',{}).get('status')=='CANONICAL_ACTIVE' and core_manifest.get('global_experience_meta_controller_v7',{}).get('v4_replaced') is False,\n"
gs=replace_once(gs,binding_anchor,binding_anchor+binding_line,'GATE_BINDING')
MODULE_GATE.write_text(gs,encoding='utf-8')

# Verify V4 source/artifact were not changed by binding transport.
if fsha(V4_CANON)!=v4_before_sha or fsha(V4_SRC)!=v4_src_before:raise RuntimeError('V4_FILES_CHANGED_DURING_META_BINDING')
v4b=G2ExperienceConditionedCognitiveLayerV4(load(V4_CANON))
v4_after=[v4b.decide(o,p) for o,p in v4_cases]
v4_snapshot_after=v4b.snapshot()
checks['v4_behavior_unchanged']=v4_before==v4_after
checks['v4_snapshot_unchanged']=v4_snapshot_before==v4_snapshot_after
if not checks['v4_behavior_unchanged'] or not checks['v4_snapshot_unchanged']:raise RuntimeError('V4_BEHAVIOR_DRIFT')

# Canonical metadata/provenance/ledger mutation on admission branch.
for pid,resp in [
 ('MEMORY_AND_EXPERIENCE','accumulated_history_to_meta_action_control'),
 ('INTELLIGENCE_AND_META_SELECTION','experience_derived_commit_continue_revise_seek_selection'),
 ('WORKSPACE_AND_INTEGRATION','additive_meta_action_control_over_v4_without_task_executor_replacement'),
 ('SELF_AUDIT_AND_REPAIR','fail_closed_meta_action_before_future_self_change'),
]:
    p=next((x for x in core.get('planes',[]) if x.get('plane_id')==pid),None)
    if p is None:raise RuntimeError('MISSING_PLANE:'+pid)
    p['active_components']=sorted(set(p.get('active_components',[])+[COMP]))
    p['responsibilities']=sorted(set(p.get('responsibilities',[])+[resp]))

core['global_experience_meta_controller_v7']={
 'status':'CANONICAL_ACTIVE','component_id':COMP,
 'canonical_component_digest':canon_art['canonical_component_digest'],
 'runtime_sha256':canon_art['runtime_sha256'],
 'genome_id':canon_art['genome_id'],'genome_digest':canon_art['genome_digest'],
 'source_transfer_receipt_sha256':canon_art['source_transfer_receipt_sha256'],
 'admission_fresh_score':fresh_score,'admission_class_scores':class_scores,
 'admission_ablation_drops':ablation_drops,
 'old_corpus_regression':canon_art['old_corpus_regression'],
 'rollback_parent_component':ROLLBACK,'v4_replaced':False,
 'automatic_canonical_promotion':False,
}
core['active_runtime_sources']=sorted(set(core.get('active_runtime_sources',[])+['runtime/yado_g2_global_experience_meta_controller_v7.py']))
rim=core.get('runtime_integrity_manifest',{})
if not isinstance(rim,dict) or not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_INTEGRITY_MANIFEST_MISSING')
rim['sources']={rel:fsha(REPO/rel) for rel in core['active_runtime_sources']}
rim['manifest_digest']=h(rim['sources'])

prov['current_g2_binding'].update({
 'current_execution_label':'G2_COGNITIVE_CONTINUITY_V5_PLUS_GLOBAL_EXPERIENCE_META_V7_CANONICAL',
 'frontier':FRONT,
 'global_experience_meta_controller':COMP,
 'global_experience_meta_controller_digest':canon_art['canonical_component_digest'],
 'global_experience_meta_controller_source_sha256':canon_art['runtime_sha256'],
 'global_experience_meta_controller_genome_id':canon_art['genome_id'],
 'global_experience_meta_controller_transfer_receipt_sha256':canon_art['source_transfer_receipt_sha256'],
 'global_experience_meta_controller_v4_replaced':False,
 'global_experience_meta_controller_automatic_promotion':False,
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=FRONT
core['runtime_sha256']=fsha(UNIFIED)
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

prev_head=head['canonical_head_digest']
head['active_capabilities']=sorted(set(head.get('active_capabilities',[])+[COMP]))
head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[COMP]))
head['global_experience_meta_controller_v7']={
 'status':'CANONICAL_ACTIVE','component_id':COMP,
 'canonical_component_digest':canon_art['canonical_component_digest'],
 'genome_id':canon_art['genome_id'],'genome_digest':canon_art['genome_digest'],
 'fresh_score':fresh_score,'ablation_drops':ablation_drops,
 'rollback_parent_component':ROLLBACK,'v4_replaced':False,
 'automatic_canonical_promotion':False,
}
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['unified_core']['runtime_sha256']=core['runtime_sha256']
head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']
head['current_frontier']=FRONT
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
ledger['open_deficits']=[FRONT]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.global_experience_meta_controller_v7.canonical_admission.v1',
 'status':'PASS_G2_GLOBAL_EXPERIENCE_META_CONTROLLER_V7_CANONICAL_ADMISSION_V1',
 'component_id':COMP,'canonical_component_digest':canon_art['canonical_component_digest'],
 'genome_id':canon_art['genome_id'],'genome_digest':canon_art['genome_digest'],
 'fresh_case_count':len(fresh),'fresh_score':fresh_score,'class_scores':class_scores,
 'ablation_scores':ablation_scores,'ablation_drops':ablation_drops,
 'old_corpus_regression':canon_art['old_corpus_regression'],
 'fail_closed':{
   'unknown':unknown_out,'missing':missing_out,'intelligence_conflict':intel_conflict_out,'thinking_conflict':think_conflict_out,
 },
 'v4_behavior_unchanged':checks['v4_behavior_unchanged'],'v4_snapshot_unchanged':checks['v4_snapshot_unchanged'],
 'active_capability_count_before':len(head['active_capabilities'])-1,
 'active_capability_count_after':len(head['active_capabilities']),
 'rollback_parent_component':ROLLBACK,'v4_replaced':False,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest'],
 'frontier_preserved':FRONT,'canonical_mutation':True,'canonical_mechanism_mutation':True,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'automatic_canonical_promotion':False,'checks':checks,
 'next_required_capability':'V7_META_CONTROLLER_LIVE_SELF_EVOLUTION_AB_TEST_V1',
 'semantic_boundary':'SAME-G2 ADDITIVE ADMISSION OF THE YADO-GENERATED V7 EXPERIENCE META-CONTROLLER. V4 REMAINS ACTIVE AND UNMODIFIED AS TASK COGNITIVE EXECUTOR/ROLLBACK PARENT. META ACTIONS DO NOT SELF-PROMOTE.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
receipt_path=REPO/f'receipts/yado-g2-global-experience-meta-controller-v7-canonical-admission-v1-run-{run_id}.json'
write(receipt_path,receipt)

event={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_GLOBAL_EXPERIENCE_META_CONTROLLER_V7_CANONICAL_ADMISSION",
 'event_type':'G2_GLOBAL_EXPERIENCE_META_CONTROLLER_V7_CANONICAL_ADMISSION',
 'status':'PASS_CANONICAL','generation':ledger['current_head'],
 'deficit':'ACCUMULATED_EXPERIENCE_NOT_YET_ACTIVE_AS_BOUNDED_META_ACTION_CONTROL',
 'effect':f"ADDED={COMP}; FRESH={fresh_score:.6f}; ABLATION={min(ablation_drops.values()):.6f}; OLD_REGRESSION={canon_art['old_corpus_regression']:.6f}; V4_REPLACED=false; ACTIVE_CAPS={len(head['active_capabilities'])}; FRONTIER_UNCHANGED={FRONT}",
 'source_path':f'receipts/yado-g2-global-experience-meta-controller-v7-canonical-admission-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest']
}
event['event_hash']=event_hash(event)
ledger['events'].append(event);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=event['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=90)
if post.returncode!=0:raise RuntimeError('POST_V7_CANONICAL_GUARD_FAILED:'+post.stdout[-6000:]+post.stderr[-2000:])

print(json.dumps({
 'status':receipt['status'],'component_id':COMP,'genome_id':canon_art['genome_id'],
 'fresh_case_count':len(fresh),'fresh_score':fresh_score,'class_scores':class_scores,
 'ablation_drops':ablation_drops,'old_corpus_regression':canon_art['old_corpus_regression'],
 'v4_behavior_unchanged':checks['v4_behavior_unchanged'],
 'active_capability_count_after':len(head['active_capabilities']),
 'frontier':FRONT,'new_head_digest':head['canonical_head_digest'],
 'next_required_capability':receipt['next_required_capability'],
},indent=2,sort_keys=True))
