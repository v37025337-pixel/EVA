from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,random,sys,time

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1,program_acc as old_acc
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1,program_acc
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

LEDGER=ROOT.parent/'architecture'/'evolution-ledger.json'
SCOUT=ROOT.parent/'receipts'/'yado-free-for-dev-capability-scout-v1-latest.json'
OUT=ROOT/'g1_external_resource_assisted_access_control_repair_v1'
OUT.mkdir(exist_ok=True)

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()

ledger=json.loads(LEDGER.read_text()); scout=json.loads(SCOUT.read_text())
validate_ledger_v2(ledger)
if ledger['current_head']!='G1_CANDIDATE_S2':raise RuntimeError('G1_NOT_HEAD')
if scout['status']!='PASS_FREE_FOR_DEV_CAPABILITY_SCOUT_V1':raise RuntimeError('SCOUT_NOT_PASS')
hyp=[x for x in scout['mechanism_hypotheses'] if x['deficit']=='ACCESS_CONTROL_HIGHER_EXPRESSIVENESS_COUNTEREXAMPLE']
if not hyp or hyp[0]['candidate_algorithm_family']!='BOUNDED_DNF_PLUS_RELATION_POLICY_INDUCTION':
    raise RuntimeError('RESOURCE_HYPOTHESIS_MISSING')

def cases(seed,n,fields,values,law,team_pool=None):
    r=random.Random(seed);out=[]
    for _ in range(n):
        x={}
        for f in fields:
            if team_pool and f in team_pool:
                x[f]=r.choice(team_pool[f])
            else:x[f]=r.choice(values[f])
        x['unseen_noise_a']=r.randint(-20,20);x['unseen_noise_b']=r.choice(['Z0','Z1','Z2','Z3','Z4'])
        out.append({'input':x,'expected':law(x)})
    return out

tasks={}

# Exact historical counterexample.
fields=['identity_verified','resource_class','session_risk','mfa']
vals={'identity_verified':[True,False],'resource_class':['PUBLIC','INTERNAL','RESTRICTED'],'session_risk':['LOW','MEDIUM','HIGH'],'mfa':[True,False]}
def access(x):
    if x['identity_verified'] and x['mfa'] and x['resource_class']=='RESTRICTED' and x['session_risk']=='LOW':return 'ALLOW'
    if x['identity_verified'] and x['resource_class']=='INTERNAL' and x['session_risk']!='HIGH':return 'ALLOW'
    return 'DENY'
tasks['ACCESS_CONTROL_HISTORICAL']={
 'train':cases(61000,480,fields,vals,access),'val':cases(62000,240,fields,vals,access),'blind':cases(63000,600,fields,vals,access)
}

# Fresh relation tasks. Blind identifiers are disjoint so memorized equality values cannot transfer.
def rel_task(name,seed,base_fields,base_vals,law,rel_fields):
    train_pool={f:[f'T{i}' for i in range(10)] for f in rel_fields}
    val_pool={f:[f'T{i}' for i in range(5,15)] for f in rel_fields}
    blind_pool={f:[f'T{i}' for i in range(15,35)] for f in rel_fields}
    tasks[name]={
      'train':cases(seed,720,base_fields,base_vals,law,train_pool),
      'val':cases(seed+1,360,base_fields,base_vals,law,val_pool),
      'blind':cases(seed+2,900,base_fields,base_vals,law,blind_pool)
    }

fields=['actor_id','owner_id','actor_team','resource_team','role','classification','device_trusted']
vals={'actor_id':['x'],'owner_id':['x'],'actor_team':['x'],'resource_team':['x'],'role':['VIEWER','EDITOR','ADMIN'],'classification':['PUBLIC','INTERNAL','SECRET'],'device_trusted':[True,False]}
def doc(x):
    if x['actor_id']==x['owner_id']:return 'ALLOW'
    if x['actor_team']==x['resource_team'] and x['role']=='EDITOR' and x['classification']=='INTERNAL' and x['device_trusted']:return 'ALLOW'
    if x['role']=='ADMIN' and x['device_trusted']:return 'ALLOW'
    return 'DENY'
rel_task('DOCUMENT_RELATION_POLICY',71000,fields,vals,doc,['actor_id','owner_id','actor_team','resource_team'])

fields=['requester','service_owner','requester_team','service_team','role','tests_pass','environment']
vals={'requester':['x'],'service_owner':['x'],'requester_team':['x'],'service_team':['x'],'role':['DEV','RELEASE_ADMIN','AUDITOR'],'tests_pass':[True,False],'environment':['DEV','STAGING','PROD']}
def deploy(x):
    if x['role']=='RELEASE_ADMIN' and x['tests_pass']:return 'APPROVE'
    if x['requester']==x['service_owner'] and x['tests_pass'] and x['environment']=='STAGING':return 'APPROVE'
    if x['requester_team']==x['service_team'] and x['role']=='DEV' and x['tests_pass'] and x['environment']=='DEV':return 'APPROVE'
    return 'DENY'
rel_task('DEPLOY_RELATION_POLICY',72000,fields,vals,deploy,['requester','service_owner','requester_team','service_team'])

fields=['principal_lab','dataset_lab','principal_id','dataset_owner','role','ethics_ok','purpose']
vals={'principal_lab':['x'],'dataset_lab':['x'],'principal_id':['x'],'dataset_owner':['x'],'role':['RESEARCHER','DATA_STEWARD','GUEST'],'ethics_ok':[True,False],'purpose':['RESEARCH','COMMERCIAL','TEACHING']}
def science(x):
    if x['role']=='DATA_STEWARD' and x['ethics_ok']:return 'ACCESS'
    if x['principal_id']==x['dataset_owner'] and x['ethics_ok']:return 'ACCESS'
    if x['principal_lab']==x['dataset_lab'] and x['role']=='RESEARCHER' and x['ethics_ok'] and x['purpose']=='RESEARCH':return 'ACCESS'
    return 'DENY'
rel_task('SCIENTIFIC_DATA_RELATION_POLICY',73000,fields,vals,science,['principal_lab','dataset_lab','principal_id','dataset_owner'])

fields=['controller_zone','device_zone','controller_id','device_owner','role','authenticated','severity']
vals={'controller_zone':['x'],'device_zone':['x'],'controller_id':['x'],'device_owner':['x'],'role':['OPERATOR','SAFETY_ADMIN','OBSERVER'],'authenticated':[True,False],'severity':['LOW','MEDIUM','HIGH']}
def control(x):
    if x['role']=='SAFETY_ADMIN' and x['authenticated']:return 'EXECUTE'
    if x['controller_id']==x['device_owner'] and x['authenticated'] and x['severity']!='LOW':return 'EXECUTE'
    if x['controller_zone']==x['device_zone'] and x['role']=='OPERATOR' and x['authenticated'] and x['severity']=='HIGH':return 'EXECUTE'
    return 'BLOCK'
rel_task('CONTROL_RELATION_POLICY',74000,fields,vals,control,['controller_zone','device_zone','controller_id','device_owner'])

def relation_ablated_acc(p,cases):
    ok=0
    for e in cases:
        out=p.default_output
        for c in p.clauses:
            if any(a.op.startswith('FIELD_') for a in c.atoms):continue
            if c.match(e['input']):out=c.output;break
        ok+=out==e['expected']
    return ok/len(cases)

results={}
for name,d in tasks.items():
    t0=time.perf_counter()
    new=BoundedDNFRelationPolicyInducerV1.synthesize(name,'LOGIC',d['train'],min_support=4,max_clauses=12)
    sec=time.perf_counter()-t0
    nr={
      'train':program_acc(new,d['train']),
      'validation':program_acc(new,d['val']),
      'fresh_blind':program_acc(new,d['blind']),
      'ablation':program_acc(new,d['blind'],ablated=True),
      'restore':program_acc(new,d['blind']),
      'relation_ablation':relation_ablated_acc(new,d['blind']),
      'synthesis_seconds':sec,
      'program':new.canonical(),
    }
    try:
        old=ConjunctiveRuleInducerV1.synthesize(name,'LOGIC',d['train'],min_support=3,max_rules=12)
        old_blind=old_acc(old,d['blind'])
    except Exception:old_blind=0.0
    nr['old_conjunctive_fresh_blind']=old_blind
    nr['gain_over_old']=nr['fresh_blind']-old_blind
    nr['pass']=nr['validation']>=.98 and nr['fresh_blind']>=.99 and nr['restore']==nr['fresh_blind'] and nr['fresh_blind']>nr['ablation']+.05
    results[name]=nr

hist=results['ACCESS_CONTROL_HISTORICAL']
relation_tasks=[v for k,v in results.items() if k!='ACCESS_CONTROL_HISTORICAL']
relation_causal=all(v['fresh_blind']>v['relation_ablation']+.02 for v in relation_tasks)
all_pass=all(v['pass'] for v in results.values()) and hist['fresh_blind']>=.995 and hist['gain_over_old']>.01 and relation_causal

component={
 'schema':'yado.algorithm_component.bounded_dnf_relation_policy_inducer.v1',
 'component_id':'ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1',
 'family':'BOUNDED_DNF_PLUS_RELATION_POLICY_INDUCTION',
 'organ':'LOGIC','generation':'G1_CANDIDATE_S2',
 'origin_resource_scout_digest':scout['receipt_sha256'],
 'source_module':'runtime/yado_bounded_dnf_relation_policy_inducer_v1.py',
 'historical_counterexample_fresh_blind':hist['fresh_blind'],
 'historical_gain_over_old':hist['gain_over_old'],
 'transfer_task_min_fresh_blind':min(v['fresh_blind'] for v in relation_tasks),
 'relation_ablation_max':max(v['relation_ablation'] for v in relation_tasks),
 'activation_scope':'G1_SHADOW_ALGORITHM_BANK',
 'canonical_active':False,
}
component['component_digest']=h(component)
cand=ROOT.parent/'candidates'/'g1-algorithms';cand.mkdir(parents=True,exist_ok=True)
(cand/'bounded-dnf-relation-policy-inducer-v1.json').write_text(json.dumps(component,indent=2,sort_keys=True)+'\n')

report={
 'schema':'yado.g1.external_resource_assisted_access_control_repair.v1',
 'status':'PASS_G1_EXTERNAL_RESOURCE_ASSISTED_ACCESS_CONTROL_REPAIR_V1' if all_pass else 'WITHHOLD_G1_EXTERNAL_RESOURCE_ASSISTED_ACCESS_CONTROL_REPAIR_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'generation':ledger['current_head'],'resource_scout_digest':scout['receipt_sha256'],
 'resource_derived_hypothesis':hyp[0],
 'results':results,
 'summary':{
   'task_count':len(results),'tasks_passed':sum(v['pass'] for v in results.values()),
   'min_fresh_blind':min(v['fresh_blind'] for v in results.values()),
   'historical_access_old':hist['old_conjunctive_fresh_blind'],
   'historical_access_new':hist['fresh_blind'],
   'relation_causal':relation_causal,
 },
 'component':component,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G1_BUDGET_AWARE_SEARCH_REPAIR_V1' if all_pass else 'CONTINUE_G1_ACCESS_CONTROL_COUNTEREXAMPLE_REPAIR',
 'semantic_boundary':'EXTERNAL CATALOG INSPIRED A GENERAL BOUNDED POLICY REPRESENTATION; THE EVALUATION USES HOST-DEFINED SYNTHETIC TASKS AND DOES NOT PROVE REAL-WORLD AUTHORIZATION SECURITY',
}
report['receipt_sha256']=h(report)
(ROOT/'yado_g1_external_resource_assisted_access_control_repair_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')

e={
 'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G1_ACCESS_CONTROL_RESOURCE_ASSISTED_REPAIR",
 'event_type':'EXTERNAL_RESOURCE_ASSISTED_ALGORITHM_GENESIS','status':'PASS_SHADOW' if all_pass else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'ACCESS_CONTROL_HIGHER_EXPRESSIVENESS_COUNTEREXAMPLE',
 'effect':'BOUNDED_DNF_RELATION_POLICY_INDUCER_RESOLVED_HISTORICAL_ACCESS_COUNTEREXAMPLE_AND_TRANSFERRED' if all_pass else 'ACCESS_CONTROL_REPAIR_WITHHELD',
 'source_path':'receipts/yado-g1-external-resource-assisted-access-control-repair-v1-latest.json','source_digest':report['receipt_sha256'],
 'run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False,
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if all_pass:
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x not in ('ACCESS_CONTROL_HIGHER_EXPRESSIVENESS_COUNTEREXAMPLE','G1_EXTERNAL_RESOURCE_ASSISTED_ACCESS_CONTROL_REPAIR_V1')]
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['G1_BUDGET_AWARE_SEARCH_REPAIR_V1']))
    ledger['shadow_resolved_deficits']=sorted(set(ledger.get('shadow_resolved_deficits',[])+['ACCESS_CONTROL_HIGHER_EXPRESSIVENESS_COUNTEREXAMPLE','G1_EXTERNAL_RESOURCE_ASSISTED_ACCESS_CONTROL_REPAIR_V1']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({
 'status':report['status'],'summary':report['summary'],
 'component_digest':component['component_digest'],
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not all_pass:raise SystemExit('ACCESS_CONTROL_REPAIR_WITHHELD')
