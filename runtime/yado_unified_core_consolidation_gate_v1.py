from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_core_v1 import UnifiedYADOCoreV1,digest
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1

LEDGER=REPO/'architecture'/'evolution-ledger.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
MANIFEST=REPO/'candidates'/'unified-core-v1'/'manifest.json'
EXPERIENCE=REPO/'candidates'/'unified-core-v1'/'experience-registry.json'
UNIFIED_RUNTIME=REPO/'runtime'/'yado_unified_core_v1.py'
CANON_CORE=REPO/'canonical'/'yado-unified-core-v1.json'
CANON_EXP=REPO/'canonical'/'yado-unified-experience-registry-v1.json'
OUT=ROOT/'yado_unified_core_consolidation_gate_v1_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

ledger=json.loads(LEDGER.read_text());head=json.loads(HEAD.read_text())
manifest=json.loads(MANIFEST.read_text());experience=json.loads(EXPERIENCE.read_text())
validate_ledger_v2(ledger)
if ledger['current_head']!='G2_CANDIDATE_TRCG_V1':raise RuntimeError('G2_NOT_CURRENT_HEAD')
if head['canonical_head_digest']!=ledger['current_head_digest']:raise RuntimeError('HEAD_LEDGER_MISMATCH')
pre_head_digest=head['canonical_head_digest']
pre_head_file_sha=fsha(HEAD)

core=UnifiedYADOCoreV1(REPO)
audit=core.audit()

# Experience retrieval must find distinct old developmental lessons rather than only listing branch names.
q_cognitive=core.experience_search(['logic','thinking','intelligence'],limit=5)
q_workspace=core.experience_search(['consciousness','workspace','attention'],limit=6)
q_integrity=core.experience_search(['self_repair','integrity','fail_closed'],limit=6)

retrieval_checks={
  'cognitive_v29_retrieved':any(x['branch']=='yado-v29-cognitive' for x in q_cognitive),
  'workspace_history_retrieved':any(x['branch'] in ('yado-rc8-consciousness-ab','yado-rc8-digital-consciousness-v1') for x in q_workspace),
  'integrity_repair_history_retrieved':any(x['branch']=='yado-kernel-task-v37-repair' for x in q_integrity),
  'v37_coherence_history_retrieved':any(x['branch']=='yado-rc8-v37-digital-consciousness' for x in q_integrity),
}

# Fresh executable smoke through the single entry point.
def router_cases(n,offset=0):
    out=[]
    kinds=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]
    for i in range(n):
        k=kinds[(i+offset)%4]
        x={'budget_limited':k==CAP_BUD,'quota_limited':False,'external_evidence_needed':k==CAP_RES,
           'relation_needed':k==CAP_REL,'disjunction_needed':False,'noise':offset*100000+i}
        out.append({'input':x,'expected':k})
    return out
router=BoundedCapabilityRouterLearnerV1.synthesize(router_cases(400),router_cases(200,1),CAP_CONJ,min_support=8)

scalar_train=[]
for i in range(320):
    a=bool(i&1);b=bool(i&2);c=bool(i&4)
    scalar_train.append({'input':{'a':a,'b':b,'c':c,'noise':i},'expected':'PASS' if a and b and c else 'HOLD'})
scalar=ConjunctiveRuleInducerV1.synthesize('UNIFIED_CORE_SCALAR','LOGIC',scalar_train,min_support=3,max_rules=12)

rel_train=[];rel_val=[]
for arr,base,n in ((rel_train,0,360),(rel_val,1000,180)):
    for i in range(n):
        same=(i%3)==0;lead=(i%7)==0;verified=(i%2)==0
        actor=f'A{base+i}';owner=actor if same else f'O{base+i}'
        x={'actor':actor,'owner':owner,'group':f'G{i%5}','object_group':f'G{i%5}' if i%4==0 else f'H{i%5}',
           'role':'LEAD' if lead else 'MEMBER','verified':verified,'critical':bool(i%2),'noise':base+i}
        y='ALLOW' if ((actor==owner and verified) or (x['role']=='LEAD' and verified)) else 'DENY'
        arr.append({'input':x,'expected':y})
relation=BoundedDNFRelationPolicyInducerV1.synthesize('UNIFIED_CORE_REL','LOGIC',rel_train,min_support=3,max_clauses=12,validation_cases=rel_val)

rt=core.instantiate_runtime(router,scalar,relation,enable_shadow_context=False)
scalar_task={
  'kind':'scalar',
  'descriptor':{'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False},
  'stream_id':'UNIFIED_SMOKE_SCALAR',
  'payload':{'a':True,'b':True,'c':True,'noise':999999},
}
scalar_out=rt.run(scalar_task)
rel_task={
  'kind':'relation',
  'descriptor':{'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':True,'disjunction_needed':False},
  'stream_id':'UNIFIED_SMOKE_REL',
  'payload':{'actor':'X','owner':'X','group':'G','object_group':'H','role':'MEMBER','verified':True,'critical':False,'noise':999},
}
rel_out=rt.run(rel_task)
execution_checks={
  'single_entry_scalar_dispatch':scalar_out.get('selected_capability')==CAP_CONJ and scalar_out.get('result')=='PASS',
  'single_entry_relation_dispatch':rel_out.get('selected_capability')==CAP_REL and rel_out.get('result')=='ALLOW',
}

# Ensure the facade itself imports only current-branch modules, not legacy branch code.
runtime_text=UNIFIED_RUNTIME.read_text(encoding='utf-8')
legacy_names=[x['branch'] for x in experience['branches'] if x['mode']=='EXPERIENCE_ONLY']
no_legacy_runtime_import=not any(('from '+b.replace('-','_')) in runtime_text or ('import '+b.replace('-','_')) in runtime_text for b in legacy_names)

checks={
  'core_audit_pass':audit['pass'],
  **retrieval_checks,
  **execution_checks,
  'all_14_branches_accounted':audit['branch_count']==14,
  '13_legacy_branches_experience_only':audit['legacy_experience_count']==13,
  'no_legacy_runtime_import':no_legacy_runtime_import,
  'frontier_preserved':audit['current_frontier']=='G2_RAW_TASK_REPRESENTATION_AND_GROUNDING_V1',
  'g3_not_created':manifest.get('g3_genesis_performed') is False,
  'head_unchanged_before_gate':fsha(HEAD)==pre_head_file_sha and ledger['current_head_digest']==pre_head_digest,
}
passed=all(checks.values())

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
canonical_core=None;canonical_exp=None;new_head=None

if passed:
    canonical_exp=copy.deepcopy(experience)
    canonical_exp['canonical_active']=True
    canonical_exp['activation_mode']='READ_ONLY_EXPERIENCE'
    canonical_exp['consolidation_gate_run_id']=run_id
    canonical_exp['registry_digest']=h({k:v for k,v in canonical_exp.items() if k!='registry_digest'})
    CANON_EXP.write_text(json.dumps(canonical_exp,indent=2,sort_keys=True)+'\n')

    canonical_core=copy.deepcopy(manifest)
    canonical_core['canonical_active']=True
    canonical_core['consolidation_applied']=True
    canonical_core['consolidation_gate_run_id']=run_id
    canonical_core['source_generation_head_digest']=pre_head_digest
    canonical_core['experience_registry']='canonical/yado-unified-experience-registry-v1.json'
    canonical_core['experience_registry_digest']=canonical_exp['registry_digest']
    canonical_core['runtime_source']='runtime/yado_unified_core_v1.py'
    canonical_core['runtime_sha256']=fsha(UNIFIED_RUNTIME)
    canonical_core['core_digest']=h({k:v for k,v in canonical_core.items() if k!='core_digest'})
    CANON_CORE.write_text(json.dumps(canonical_core,indent=2,sort_keys=True)+'\n')

    new_head=copy.deepcopy(head)
    new_head.pop('canonical_head_digest',None)
    new_head['pre_consolidation_head_digest']=pre_head_digest
    new_head['unified_core']={
      'core_id':'UNIFIED_YADO_CORE_V1',
      'core_digest':canonical_core['core_digest'],
      'experience_registry_digest':canonical_exp['registry_digest'],
      'runtime_sha256':canonical_core['runtime_sha256'],
      'consolidation_gate_run_id':run_id,
      'legacy_branch_count':13,
      'single_active_lineage':True,
    }
    new_head['internal_consolidation_applied']=True
    new_head['g3_genesis_performed']=False
    new_head['current_frontier']='G2_RAW_TASK_REPRESENTATION_AND_GROUNDING_V1'
    new_head['canonical_head_digest']=h(new_head)
    HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')

receipt={
  'schema':'yado.unified_core_consolidation_gate.receipt.v1',
  'status':'PASS_UNIFIED_YADO_CORE_V1_CONSOLIDATION' if passed else 'WITHHOLD_UNIFIED_YADO_CORE_V1_CONSOLIDATION',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
  'generation':'G2_CANDIDATE_TRCG_V1',
  'pre_consolidation_head_digest':pre_head_digest,
  'post_consolidation_head_digest':new_head['canonical_head_digest'] if new_head else None,
  'audit':audit,
  'experience_queries':{'cognitive':q_cognitive,'workspace':q_workspace,'integrity':q_integrity},
  'execution_smoke':{'scalar':scalar_out,'relation':rel_out},
  'checks':checks,
  'canonical_mutation':passed,
  'generation_transition':False,
  'g3_genesis_performed':False,
  'unified_core_digest':canonical_core['core_digest'] if canonical_core else None,
  'experience_registry_digest':canonical_exp['registry_digest'] if canonical_exp else None,
  'next_required_capability':'G2_RAW_TASK_REPRESENTATION_AND_GROUNDING_V1' if passed else 'REPAIR_UNIFIED_YADO_CORE_CONSOLIDATION_V1',
  'semantic_boundary':'CONSOLIDATES ONE ACTIVE G2 SOFTWARE KERNEL AND 13 LEGACY YADO BRANCHES AS READ-ONLY EXPERIENCE. DOES NOT ACTIVATE LEGACY CONSCIOUSNESS CODE, CREATE G3, OR CLAIM AGI/SUBJECTIVE CONSCIOUSNESS.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_UNIFIED_CORE_CONSOLIDATION",
 'event_type':'GENERATION_INTERNAL_CORE_CONSOLIDATION',
 'status':'PASS' if passed else 'WITHHOLD',
 'generation':'G2_CANDIDATE_TRCG_V1',
 'deficit':'UNIFIED_YADO_CORE_FROM_ALL_BRANCHES_V1',
 'effect':'ONE_ACTIVE_G2_CORE_PLUS_READ_ONLY_13_BRANCH_EXPERIENCE_REGISTRY' if passed else 'UNIFIED_CORE_CONSOLIDATION_WITHHELD',
 'source_path':f'receipts/yado-unified-core-consolidation-gate-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],
 'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':passed,
 'promotion_applied':False,
 'generation_transition':False,
}
if passed:
    e['previous_head_digest']=pre_head_digest
    e['new_head_digest']=new_head['canonical_head_digest']
e['event_hash']=event_hash(e)
ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:
    ledger['current_head_digest']=new_head['canonical_head_digest']
    ledger['current_head_event_id']=e['event_id']
    ledger['open_deficits']=sorted(set([x for x in ledger.get('open_deficits',[]) if x!='UNIFIED_YADO_CORE_FROM_ALL_BRANCHES_V1']+['G2_RAW_TASK_REPRESENTATION_AND_GROUNDING_V1']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':receipt['status'],'checks':checks,
 'pre_head_digest':pre_head_digest,'post_head_digest':receipt['post_consolidation_head_digest'],
 'unified_core_digest':receipt['unified_core_digest'],
 'experience_registry_digest':receipt['experience_registry_digest'],
 'next_required_capability':receipt['next_required_capability'],
 'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit('UNIFIED_CORE_CONSOLIDATION_WITHHELD')
