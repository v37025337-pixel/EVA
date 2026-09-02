from __future__ import annotations
from pathlib import Path
from itertools import combinations
from dataclasses import asdict
import copy,hashlib,json,os,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

import yado_architecture_neutral_meta_synthesizer_v2 as neutral
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
SOURCE_CAND=REPO/'candidates/kernel-self-generated/scale-conditional-pair-knn-successor-v1.json'
DB=REPO/'runtime/yado_g2_native_selector_commit_registry_v1.sqlite'
ART=REPO/'architecture/yado-kernel-native-selector-commit-substrate-genesis-v1.json'
CAND=REPO/'candidates/kernel-self-generated/native-selector-commit-substrate-v1.json'
OUT=ROOT/'yado_kernel_native_selector_commit_substrate_genesis_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
 x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,ledger,corpus,src=map(load,[HEAD,CORE,LEDGER,CORPUS,SOURCE_CAND])
validate_ledger_v2(ledger)
front='KERNEL_NATIVE_SELECTOR_COMMIT_SUBSTRATE_GENESIS_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if src.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('SOURCE_SELECTOR_NOT_SUPPORTED')
threshold=float(src['selected_threshold'])
low_label=str(src['branches']['low_scale']);high_label=str(src['branches']['high_scale'])

data=neutral.build_dataset(force=True)
expected={x['id']:x['sha256'] for x in corpus['source_digests']}
actual={sid:r['sha256'] for sid,r in data['rows'].items()}
if expected!=actual:raise RuntimeError('SOURCE_DIGEST_DRIFT')
ids=sorted(data['rows'])

# Derive examples from the kernel-selected reaction norm, not host-authored rules.
# Hold out exactly 10 cases per observed scale (1..5), so causal blind contains
# both routing outputs and cannot be passed by a single default branch.
train=[]
blind=[]
for size in (1,2,3,4,5):
    rows=[]
    for combo in combinations(ids,size):
        x,y,counts=neutral._vector(combo,data['rows'])
        expected_route=high_label if float(x['source_count'])+1e-12>=threshold else low_label
        key='|'.join(combo)
        rows.append((hashlib.sha256((key+'|COMMIT_SUBSTRATE_BLIND').encode()).hexdigest(),{'input':{'source_count':float(x['source_count'])},'expected':expected_route}))
    rows.sort(key=lambda z:z[0])
    hold=min(10,len(rows)-2)
    blind.extend(v for _,v in rows[:hold])
    train.extend(v for _,v in rows[hold:])

# Size-6 remains a separate full post-commit transfer test, not causal selection evidence.
fresh6=[]
for combo in combinations(ids,6):
    x,y,counts=neutral._vector(combo,data['rows'])
    fresh6.append({'input':{'source_count':float(x['source_count'])},'expected':high_label})
if len(train)!=1535 or len(blind)!=50 or len(fresh6)!=924:
    raise RuntimeError('CASE_COUNTS_INVALID:'+json.dumps({'train':len(train),'blind':len(blind),'fresh6':len(fresh6)}))

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Create a durable bounded selector routing capability from the kernel-selected scale reaction norm',
      required_capabilities={'SCALE_CONDITIONAL_SELECTOR_ROUTE_V1':1.0},
      success_criteria={'blind_score':1.0,'ablation_required':True,'restore_required':True,'source_threshold':threshold},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    if len(deficits)!=1:raise RuntimeError('EXPECTED_ONE_SELECTOR_DEFICIT:'+str(len(deficits)))
    deficit=deficits[0]
    program,selection=k.executive.synthesize_best_mechanism(
      deficit.deficit_id,'GENERATIVE_EXECUTIVE',train,min_support=2
    )
    development=k.executive.evaluate_mechanism(
      program.program_id,blind,min_score=1.0,min_ablation_drop=0.20
    )
    if not development.state_committed or development.verdict!='COMMIT':
        raise RuntimeError('NATIVE_EXECUTIVE_DID_NOT_COMMIT:'+json.dumps(asdict(development),sort_keys=True,default=str))
    low_probe=k.executive.execute_capability('SCALE_CONDITIONAL_SELECTOR_ROUTE_V1',{'source_count':1.0})
    boundary_probe=k.executive.execute_capability('SCALE_CONDITIONAL_SELECTOR_ROUTE_V1',{'source_count':threshold})
    high_probe=k.executive.execute_capability('SCALE_CONDITIONAL_SELECTOR_ROUTE_V1',{'source_count':2.0})
    if low_probe!=low_label or boundary_probe!=high_label or high_probe!=high_label:
        raise RuntimeError('POST_COMMIT_ROUTE_PROBE_FAILED:'+json.dumps({'low':low_probe,'boundary':boundary_probe,'high':high_probe}))
    fresh6_correct=sum(k.executive.execute_capability('SCALE_CONDITIONAL_SELECTOR_ROUTE_V1',row['input'])==row['expected'] for row in fresh6)
    fresh6_score=fresh6_correct/len(fresh6)
    if abs(fresh6_score-1.0)>1e-12:
        raise RuntimeError('POST_COMMIT_FRESH6_TRANSFER_FAILED:'+str(fresh6_score))
    k.conn.execute('PRAGMA wal_checkpoint(FULL)')
    k.conn.commit()
    selection_obj=asdict(selection)
    development_obj=asdict(development)
    program_id=program.program_id
    program_digest=development.program_digest
finally:
    k.close()

db_sha_before=hashlib.sha256(DB.read_bytes()).hexdigest()

# Restart proof: fresh RC8 instance restores COMMITTED mechanism from the same DB.
k2=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    restored=dict(k2.executive.active_program_by_capability)
    restored_programs={pid:{'status':p.status,'target_capability':p.target_capability,'target_organ':p.target_organ} for pid,p in k2.executive.programs.items()}
    low2=k2.executive.execute_capability('SCALE_CONDITIONAL_SELECTOR_ROUTE_V1',{'source_count':1.0})
    high2=k2.executive.execute_capability('SCALE_CONDITIONAL_SELECTOR_ROUTE_V1',{'source_count':2.0})
    if restored.get('SCALE_CONDITIONAL_SELECTOR_ROUTE_V1')!=program_id:
        raise RuntimeError('RESTART_DID_NOT_RESTORE_ACTIVE_PROGRAM')
    if low2!=low_label or high2!=high_label:
        raise RuntimeError('RESTART_EXECUTION_FAILED')
    k2.conn.execute('PRAGMA wal_checkpoint(FULL)');k2.conn.commit()
finally:k2.close()

db_sha_after=hashlib.sha256(DB.read_bytes()).hexdigest()
if db_sha_after!=db_sha_before:
    # SQLite can update metadata during reopen; use final digest as durable artifact digest.
    db_sha_before=db_sha_after

checks={
 'kernel_goal_created':True,
 'kernel_deficit_detected':True,
 'kernel_synthesized_mechanism':True,
 'native_evaluate_mechanism_committed':True,
 'blind_score_one':abs(float(development_obj['candidate_score'])-1.0)<1e-12,
 'fresh6_post_commit_transfer_one':abs(float(fresh6_score)-1.0)<1e-12,
 'causal_ablation_passed':float(development_obj['candidate_score'])-float(development_obj['ablation_score'])>=0.20,
 'restore_exact':abs(float(development_obj['candidate_score'])-float(development_obj['restore_score']))<1e-12,
 'restart_restored_active_program':restored.get('SCALE_CONDITIONAL_SELECTOR_ROUTE_V1')==program_id,
 'restart_execution_correct':low2==low_label and high2==high_label,
 'source_sha_exact_match':expected==actual,
 'host_rule_program_written':False,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_NATIVE_SELECTOR_COMMIT_SUBSTRATE_CANONICAL_BINDING_V1' if supported else 'KERNEL_NATIVE_SELECTOR_COMMIT_SUBSTRATE_GENESIS_V2'

candidate={
 'schema':'yado.g2.native_selector_commit_substrate.v1','state':state,
 'capability':'SCALE_CONDITIONAL_SELECTOR_ROUTE_V1',
 'target_organ':'GENERATIVE_EXECUTIVE',
 'source_reaction_norm_candidate_digest':src['candidate_digest'],
 'kernel_selected_threshold':threshold,
 'training_case_count':len(train),'blind_case_count':len(blind),'fresh6_post_commit_case_count':len(fresh6),'fresh6_post_commit_score':fresh6_score,
 'selection':selection_obj,'development':development_obj,
 'program_id':program_id,'program_digest':program_digest,
 'persistent_registry_path':'runtime/yado_g2_native_selector_commit_registry_v1.sqlite',
 'persistent_registry_sha256':db_sha_after,
 'restart_active_programs':restored,'restart_programs':restored_programs,
 'route_probes':{'low':low2,'boundary_before_restart':boundary_probe,'high':high2},
 'checks':checks,'canonical_active':False,'promotion_applied':False,'g3_genesis_performed':False,
}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)

artifact={'schema':'yado.g2.kernel_native_selector_commit_substrate_genesis.v1',
 'status':'PASS_NATIVE_SELECTOR_COMMIT_SUBSTRATE_GENESIS_V1' if supported else 'WITHHOLD_NATIVE_SELECTOR_COMMIT_SUBSTRATE_GENESIS_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],
 'program_id':program_id,'program_digest':program_digest,'registry_sha256':db_sha_after,
 'next_required_capability':next_cap,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
receipt={**artifact,'schema':'yado.g2.kernel_native_selector_commit_substrate_genesis.receipt.v1',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_NATIVE_SELECTOR_COMMIT_SUBSTRATE_GENESIS_V1",
 'event_type':'G2_NATIVE_EXECUTIVE_COMMIT_SUBSTRATE_GENESIS','status':'PASS_SHADOW' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"NATIVE_EXECUTIVE=DevelopmentalExecutiveV22; PROGRAM={program_id}; BLIND={development_obj['candidate_score']:.6f}; ABLATION={development_obj['ablation_score']:.6f}; RESTORE={development_obj['restore_score']:.6f}; RESTART={checks['restart_restored_active_program']}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-native-selector-commit-substrate-genesis-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
print(json.dumps({'state':state,'program_id':program_id,'development':development_obj,'restart_active':restored,'next':next_cap},indent=2,sort_keys=True,default=str))
