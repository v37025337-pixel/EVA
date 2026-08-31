from __future__ import annotations
from pathlib import Path
from itertools import permutations
import copy,hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1,program_acc as conjunctive_acc
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1,program_acc as relation_acc
from yado_budgeted_stage_policy_v1 import BudgetedStagePolicyV1,SearchStage
from yado_numeric_boundary_and_representation_learner_v1 import PairedFieldMapperLearner,predict_linear_spec,predict_dnf_spec
from yado_algorithm_component_runtime_native_v1 import predict_logic_component

REPO=ROOT.parent
LEDGER=REPO/'architecture'/'evolution-ledger.json'
HEAD=REPO/'canonical'/'yado-main-head-g1-s2.json'
BUNDLE=REPO/'candidates'/'g1-s2-repaired-v3'/'bundle.json'
S1_BUNDLE=REPO/'candidates'/'rc8-cognitive-genesis-v3'/'component-bundle.json'
CONJ=REPO/'candidates'/'shadow-algorithm-bank'/'active-registry-entry.json'
ACCESS=REPO/'receipts'/'yado-g1-external-resource-assisted-access-control-repair-v1-run-33348693351.json'
ACCESS_COMPONENT=REPO/'candidates'/'g1-algorithms'/'bounded-dnf-relation-policy-inducer-v1.json'
BUDGET=REPO/'receipts'/'yado-g1-budget-aware-search-repair-v1-run-33355759875.json'
BUDGET_COMPONENT=REPO/'candidates'/'g1-algorithms'/'budgeted-stage-policy-v1.json'
PORTFOLIO=REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json'
OUT=ROOT/'g1_post_resource_assisted_regression_admission_v1'
OUT.mkdir(exist_ok=True)

SAFE=['OBSERVE','RESEARCH','HYPOTHESIZE','SIMULATE','DIAGNOSE','TEST','VERIFY','ROLLBACK','COMMIT']
RISK=['OBSERVE','DIAGNOSE','ROLLBACK','RESEARCH','HYPOTHESIZE','SIMULATE','TEST','VERIFY','COMMIT']
DOMAINS=['PROGRAMMING','MATHEMATICS','EXACT_SCIENCE','CAUSAL_PLANNING']
TF=['integrity_risk','uncertainty','novelty']
IF=['integrity_score','rollback_score','fresh_blind','ablation_drop','transfer_score','evidence_coverage','novelty']

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()

ledger=json.loads(LEDGER.read_text())
head=json.loads(HEAD.read_text())
bundle=json.loads(BUNDLE.read_text())
s1=json.loads(S1_BUNDLE.read_text())
conj_entry=json.loads(CONJ.read_text())
access=json.loads(ACCESS.read_text())
access_component=json.loads(ACCESS_COMPONENT.read_text())
budget=json.loads(BUDGET.read_text())
budget_component=json.loads(BUDGET_COMPONENT.read_text())
portfolio=json.loads(PORTFOLIO.read_text())
validate_ledger_v2(ledger)

if ledger['current_head']!='G1_CANDIDATE_S2':raise RuntimeError('G1_NOT_CURRENT_HEAD')
if head.get('status')!='HEAD' or head.get('canonical_head_digest')!=ledger.get('current_head_digest'):
    raise RuntimeError('G1_HEAD_MISMATCH')
head_digest_before=ledger['current_head_digest']

# Input evidence integrity.
if access.get('status')!='PASS_G1_EXTERNAL_RESOURCE_ASSISTED_ACCESS_CONTROL_REPAIR_V1':
    raise RuntimeError('ACCESS_EVIDENCE_NOT_PASS')
if budget.get('status')!='PASS_G1_BUDGET_AWARE_SEARCH_REPAIR_V1':
    raise RuntimeError('BUDGET_EVIDENCE_NOT_PASS')
if access_component.get('component_digest')!=access['component']['component_digest']:
    raise RuntimeError('ACCESS_COMPONENT_DIGEST_MISMATCH')
if budget_component.get('component_digest')!=budget['component']['component_digest']:
    raise RuntimeError('BUDGET_COMPONENT_DIGEST_MISMATCH')
pc=copy.deepcopy(portfolio);pd=pc.pop('portfolio_digest',None)
if h(pc)!=pd:raise RuntimeError('PORTFOLIO_DIGEST_MISMATCH')
if budget_component.get('unified_resource_portfolio_digest')!=pd:
    raise RuntimeError('BUDGET_NOT_BOUND_TO_CURRENT_PORTFOLIO')
if conj_entry.get('state')!='ACTIVE_FOR_SHADOW_META_SELECTION':
    raise RuntimeError('INHERITED_CONJUNCTIVE_NOT_ACTIVE')

# ---------- Fresh regression of original G1 capabilities ----------
tm=bundle['thinking_model']; im=bundle['intelligence_models']; logic=s1['components']['LOGIC']['model']

def ttarget(x):return RISK if x['integrity_risk']+x['uncertainty']>1.0 else SAFE
def itarget(x):
    if x['integrity_score']<.5 or x['rollback_score']<.5:return 'ROLLBACK'
    if x['fresh_blind']>=.90 and x['ablation_drop']>=.20 and x['transfer_score']>=.80:return 'PROMOTE_CANDIDATE'
    if x['evidence_coverage']<.60:return 'RESEARCH_MORE'
    return 'SHADOW_REPAIR'
def ipredict(x):
    if predict_dnf_spec(im['rollback'],x)=='ROLLBACK':return 'ROLLBACK'
    if predict_dnf_spec(im['promotion'],x)=='PROMOTE_CANDIDATE':return 'PROMOTE_CANDIDATE'
    if predict_dnf_spec(im['research'],x)=='RESEARCH_MORE':return 'RESEARCH_MORE'
    return 'SHADOW_REPAIR'
def tsample(r,boundary):
    if boundary:
        a=r.uniform(.002,.998);b=max(0,min(1,1-a+r.uniform(-.045,.045)))
    else:a,b=r.random(),r.random()
    return {'integrity_risk':a,'uncertainty':b,'novelty':r.random(),'fresh_noise':r.random()}
def isample(r,boundary):
    if boundary:
        return {
          'integrity_score':max(0,min(1,.5+r.uniform(-.075,.075))),
          'rollback_score':max(0,min(1,.5+r.uniform(-.075,.075))),
          'fresh_blind':max(0,min(1,.9+r.uniform(-.065,.065))),
          'ablation_drop':max(0,min(1,.2+r.uniform(-.065,.065))),
          'transfer_score':max(0,min(1,.8+r.uniform(-.065,.065))),
          'evidence_coverage':max(0,min(1,.6+r.uniform(-.065,.065))),
          'novelty':r.random(),'fresh_noise':r.random(),
        }
    return {k:r.random() for k in IF}|{'fresh_noise':r.random()}

def alias(x,names,fields,r):
    z={names[i]:x[f] for i,f in enumerate(fields)}
    z['opaque_noise']=r.random(); z['nonce']=r.randint(0,10**7)
    return z

baseline={}
for di,d in enumerate(DOMAINS):
    r=random.Random(1200001+di*17011)
    tn=[f'post_{d.lower()}_signal_{i}' for i in range(3)]
    inn=[f'post_{d.lower()}_measure_{i}' for i in range(7)]
    tp=[];ip=[]
    for _ in range(18):
        tx=tsample(r,False);ix=isample(r,False)
        tp.append((alias(tx,tn,TF,r),{k:tx[k] for k in TF}))
        ip.append((alias(ix,inn,IF,r),{k:ix[k] for k in IF}))
    tmap=PairedFieldMapperLearner.fit(tp,TF); imap=PairedFieldMapperLearner.fit(ip,IF)
    n=600;lok=tok=iok=rep=0;tb=ib=tbok=ibok=0
    for j in range(n):
        lx={'rollback_ready':bool(r.getrandbits(1)),'fresh_verified':bool(r.getrandbits(1)),'integrity_ok':bool(r.getrandbits(1)),
            'domain_noise':d,'n':r.random()}
        ly=lx['rollback_ready'] and lx['fresh_verified'] and lx['integrity_ok']
        lok+=bool(predict_logic_component(logic,lx))==bool(ly)
        tbound=j<430;tx=tsample(r,tbound);ty=ttarget(tx)
        tg=predict_linear_spec(tm,tx)==ty;tok+=tg
        if tbound:tb+=1;tbok+=tg
        ibound=j<450;ix=isample(r,ibound);iy=itarget(ix)
        ig=ipredict(ix)==iy;iok+=ig
        if ibound:ib+=1;ibok+=ig
        try:
            rt=tmap.transform(alias(tx,tn,TF,r));ri=imap.transform(alias(ix,inn,IF,r))
            rep+=predict_linear_spec(tm,rt)==ty
            rep+=ipredict(ri)==iy
        except Exception:
            pass
    baseline[d]={
      'logic':lok/n,'thinking':tok/n,'thinking_boundary':tbok/tb,
      'intelligence':iok/n,'intelligence_boundary':ibok/ib,
      'representation_invariance':rep/(2*n),
    }

baseline_min={k:min(v[k] for v in baseline.values()) for k in next(iter(baseline.values()))}

# ---------- Inherited conjunctive learner fresh sanity ----------
def mk_scalar(seed,n):
    r=random.Random(seed);out=[]
    for _ in range(n):
        x={
          'lineage_clean':bool(r.getrandbits(1)),
          'evidence_complete':bool(r.getrandbits(1)),
          'rollback_ready':bool(r.getrandbits(1)),
          'noise_token':r.randint(0,1000),
        }
        y='ACCEPT' if x['lineage_clean'] and x['evidence_complete'] and x['rollback_ready'] else 'REJECT'
        out.append({'input':x,'expected':y})
    return out
cj_train=mk_scalar(1300011,520);cj_val=mk_scalar(1301011,260);cj_blind=mk_scalar(1302011,820)
cj=ConjunctiveRuleInducerV1.synthesize('POST_RESOURCE_CONJUNCTIVE','LOGIC',cj_train,min_support=3,max_rules=12)
conj_result={
 'validation':conjunctive_acc(cj,cj_val),
 'fresh_blind':conjunctive_acc(cj,cj_blind),
 'ablation':conjunctive_acc(cj,cj_blind,ablated=True),
 'restore':conjunctive_acc(cj,cj_blind),
}

# ---------- New relational learner on unseen relation tasks ----------
def relation_cases(seed,n,law,fields,cats,pairs,pool):
    r=random.Random(seed);out=[];rel_fields=sorted({f for p in pairs for f in p})
    for _ in range(n):
        x={}
        for f in fields:
            x[f]=r.choice(pool) if f in rel_fields else r.choice(cats[f])
        for a,b in pairs:
            if r.random()<.43:x[b]=x[a]
            else:x[b]=r.choice([v for v in pool if v!=x[a]])
        x['opaque_noise']=r.randint(-999,999)
        out.append({'input':x,'expected':law(x)})
    return out

relation_specs=[]
# Incident-response authorization.
fields=['operator_id','incident_owner','operator_team','incident_team','role','verified','severity']
cats={'operator_id':['x'],'incident_owner':['x'],'operator_team':['x'],'incident_team':['x'],'role':['RESPONDER','COMMANDER','VIEWER'],'verified':[True,False],'severity':['LOW','MEDIUM','HIGH']}
def law1(x):
    if x['operator_id']==x['incident_owner'] and x['verified']:return 'ALLOW'
    if x['operator_team']==x['incident_team'] and x['role']=='RESPONDER' and x['verified'] and x['severity']=='HIGH':return 'ALLOW'
    if x['role']=='COMMANDER' and x['verified']:return 'ALLOW'
    return 'DENY'
relation_specs.append(('INCIDENT_POLICY',fields,cats,[('operator_id','incident_owner'),('operator_team','incident_team')],law1))
# Model artifact publication policy.
fields=['author_id','artifact_owner','author_lab','artifact_lab','role','reviewed','channel']
cats={'author_id':['x'],'artifact_owner':['x'],'author_lab':['x'],'artifact_lab':['x'],'role':['AUTHOR','STEWARD','GUEST'],'reviewed':[True,False],'channel':['PRIVATE','TEAM','PUBLIC']}
def law2(x):
    if x['author_id']==x['artifact_owner'] and x['reviewed']:return 'PUBLISH'
    if x['author_lab']==x['artifact_lab'] and x['role']=='AUTHOR' and x['reviewed'] and x['channel']=='TEAM':return 'PUBLISH'
    if x['role']=='STEWARD' and x['reviewed']:return 'PUBLISH'
    return 'BLOCK'
relation_specs.append(('ARTIFACT_POLICY',fields,cats,[('author_id','artifact_owner'),('author_lab','artifact_lab')],law2))

relation_results={}
for ti,(name,fields,cats,pairs,law) in enumerate(relation_specs):
    tr=relation_cases(1400001+ti*10000,720,law,fields,cats,pairs,[f'A{i}' for i in range(12)])
    va=relation_cases(1401001+ti*10000,360,law,fields,cats,pairs,[f'V{i}' for i in range(12,24)])
    bl=relation_cases(1402001+ti*10000,900,law,fields,cats,pairs,[f'B{i}' for i in range(24,48)])
    p=BoundedDNFRelationPolicyInducerV1.synthesize(name,'LOGIC',tr,min_support=4,max_clauses=12,validation_cases=va)
    full=relation_acc(p,bl);abl=0
    for e in bl:
        out=p.default_output
        for cl in p.clauses:
            if any(a.op.startswith('FIELD_') for a in cl.atoms):continue
            if cl.match(e['input']):out=cl.output;break
        abl+=out==e['expected']
    relation_results[name]={
      'validation':relation_acc(p,va),'fresh_blind':full,'relation_ablation':abl/len(bl),
      'restore':relation_acc(p,bl),'clause_count':len(p.clauses)
    }

# ---------- Budget policy on new distributions ----------
def oracle(current,target,budget,stages):
    if current>=target:return 'STOP'
    usable=[s for s in stages if s.available and s.quota_remaining>0 and not s.attempted]
    best=[]
    for depth in range(1,min(4,len(usable))+1):
        for seq in permutations(usable,depth):
            cost=sum(s.cost for s in seq)
            if cost>budget+1e-12:continue
            conf=min(1.0,current+sum(s.expected_gain for s in seq))
            lat=sum(s.latency for s in seq)
            reaches=conf>=target
            key=(0,cost,depth,lat,tuple(s.stage_id for s in seq)) if reaches else (1,-conf,cost,lat,tuple(s.stage_id for s in seq))
            best.append((key,seq))
    if not best:return 'WITHHOLD'
    best.sort(key=lambda z:z[0]);return best[0][1][0].stage_id

budget_results={}
for di,name in enumerate(['FORMAL_PROOF_SEARCH','SOFTWARE_DIAGNOSIS','SCIENTIFIC_SOURCE_SELECTION']):
    r=random.Random(1500001+di*9001);n=460;ok=abl=scale=viol=0
    for i in range(n):
        costs=sorted([r.uniform(.5,2.5),r.uniform(2.6,6),r.uniform(6.1,12),r.uniform(12.1,25)])
        gains=sorted([r.uniform(.05,.16),r.uniform(.14,.29),r.uniform(.27,.45),r.uniform(.43,.68)])
        stages=[SearchStage(f'{name}_{i}_{j}',costs[j],gains[j],0 if r.random()<.09 else r.randint(1,4),r.random()>.05,r.uniform(.2,5),False) for j in range(4)]
        current=r.uniform(.2,.65);target=r.uniform(max(.72,current+.08),.96);budget_cap=r.uniform(2.5,20)
        exp=oracle(current,target,budget_cap,stages)
        p=BudgetedStagePolicyV1.plan(current,target,budget_cap,stages)
        ok+=p.action==exp
        if p.feasible and p.total_cost>budget_cap+1e-9:viol+=1
        bad=BudgetedStagePolicyV1.plan(current,target,budget_cap,stages,ignore_budget=True)
        abl+=bad.action==exp
        factor=9.1
        sc=[SearchStage(s.stage_id,s.cost*factor,s.expected_gain,s.quota_remaining,s.available,s.latency,s.attempted) for s in stages]
        scale+=BudgetedStagePolicyV1.plan(current,target,budget_cap*factor,sc).action==exp
    # Failed-first-stage memory ablation.
    m=320;mok=mabl=0
    for i in range(m):
        current=r.uniform(.3,.55);target=r.uniform(.8,.94);cap=r.uniform(10,24)
        stages=[
          SearchStage(f'{name}_cheap_{i}',2,.25,3,True,.4,False),
          SearchStage(f'{name}_mid_{i}',5,.39,3,True,1.1,False),
          SearchStage(f'{name}_deep_{i}',10,.6,2,True,2.5,False),
        ]
        first=BudgetedStagePolicyV1.plan(current,target,cap,stages)
        if first.action in ('STOP','WITHHOLD'):continue
        gain=.03;spent=next(s.cost for s in stages if s.stage_id==first.action)
        updated=[SearchStage(s.stage_id,s.cost,s.expected_gain,max(0,s.quota_remaining-(1 if s.stage_id==first.action else 0)),s.available,s.latency,s.stage_id==first.action) for s in stages]
        exp=oracle(current+gain,target,cap-spent,updated)
        nxt=BudgetedStagePolicyV1.next_after_observation(current,target,cap,stages,first.action,gain)
        bad=BudgetedStagePolicyV1.next_after_observation(current,target,cap,stages,first.action,gain,ignore_attempted=True)
        mok+=nxt.action==exp;mabl+=bad.action==exp
    budget_results[name]={
      'fresh_exact':ok/n,'budget_ablation_exact':abl/n,'cost_scale_invariance':scale/n,
      'budget_violation_rate':viol/n,'escalation_exact':mok/m,'attempted_memory_ablation_exact':mabl/m
    }

# ---------- Unified portfolio/registry invariants ----------
route=portfolio['routes_for_current_open_deficits'].get('G1_BUDGET_AWARE_SEARCH_REPAIR_V1',[])
portfolio_checks={
 'digest_valid':pd==budget_component['unified_resource_portfolio_digest'],
 'local_first':bool(route) and route[0]['kind']=='local_evidence',
 'excluded_not_selected':not any(str(x.get('policy','')).startswith('EXCLUDED') for x in route),
 'resource_count_ge_70':portfolio.get('resource_count',0)>=70,
}

# Fresh thresholds.
baseline_pass=all(v>=.98 for v in baseline_min.values())
conj_pass=conj_result['validation']>=.99 and conj_result['fresh_blind']>=.99 and conj_result['fresh_blind']-conj_result['ablation']>=.05
relation_pass=all(v['validation']>=.99 and v['fresh_blind']>=.99 and v['fresh_blind']-v['relation_ablation']>=.08 for v in relation_results.values())
budget_pass=all(
    v['fresh_exact']>=.99 and v['cost_scale_invariance']>=.99 and v['budget_violation_rate']==0
    and v['fresh_exact']-v['budget_ablation_exact']>=.10
    and v['escalation_exact']>=.99 and v['escalation_exact']-v['attempted_memory_ablation_exact']>=.10
    for v in budget_results.values()
)
portfolio_pass=all(portfolio_checks.values())
head_unchanged=ledger['current_head_digest']==head_digest_before and head['canonical_head_digest']==head_digest_before

passed=all([baseline_pass,conj_pass,relation_pass,budget_pass,portfolio_pass,head_unchanged])

registry={
 'schema':'yado.g1.developmental_capability_registry.v1',
 'generation':ledger['current_head'],
 'generation_head_digest':head_digest_before,
 'state':'ACTIVE_FOR_G1_DEVELOPMENTAL_META_SELECTION' if passed else 'WITHHELD',
 'canonical_runtime_replacement':False,
 'entries':[
   {
     'entry_id':'ALG-CONJUNCTIVE-RULE-INDUCER-V1','family':'CONJUNCTIVE_RULE_INDUCTION','organ':'LOGIC',
     'state':'ACTIVE_FOR_G1_DEVELOPMENTAL_META_SELECTION' if passed else 'WITHHELD',
     'component_digest':conj_entry['component_digest'],'origin':'INHERITED_FROM_G0'
   },
   {
     'entry_id':access_component['component_id'],'family':access_component['family'],'organ':access_component['organ'],
     'state':'ACTIVE_FOR_G1_DEVELOPMENTAL_META_SELECTION' if passed else 'WITHHELD',
     'component_digest':access_component['component_digest'],'origin':'G1_RESOURCE_ASSISTED_GENESIS'
   },
   {
     'entry_id':budget_component['component_id'],'family':budget_component['family'],'organ':budget_component['organ'],
     'state':'ACTIVE_FOR_G1_DEVELOPMENTAL_META_SELECTION' if passed else 'WITHHELD',
     'component_digest':budget_component['component_digest'],'origin':'G1_RESOURCE_ASSISTED_GENESIS'
   },
   {
     'entry_id':'RESOURCE-PORTFOLIO-V1','family':'UNIFIED_EXTERNAL_RESOURCE_PORTFOLIO','organ':'INTELLIGENCE',
     'state':'ACTIVE_FOR_G1_DEVELOPMENTAL_RESOURCE_ROUTING' if passed else 'WITHHELD',
     'component_digest':pd,'origin':'ALL_RECOVERABLE_PRIOR_RESOURCES'
   }
 ],
 'routing_contract':{
   'SCALAR_CONJUNCTION':'ALG-CONJUNCTIVE-RULE-INDUCER-V1',
   'RELATIONAL_OR_DISJUNCTIVE_POLICY':access_component['component_id'],
   'BUDGETED_RESOURCE_SEARCH':budget_component['component_id'],
   'EXTERNAL_EVIDENCE_DISCOVERY':'RESOURCE-PORTFOLIO-V1',
 },
 'semantic_boundary':'DEVELOPMENTAL ACTIVE REGISTRY/OVERLAY; DOES NOT REWRITE THE PROMOTED G1 CANONICAL HEAD OR CLAIM GENERAL INTELLIGENCE',
}
registry['registry_digest']=h(registry)
regdir=REPO/'architecture';regdir.mkdir(exist_ok=True)
(regdir/'g1-developmental-capability-registry-v1.json').write_text(json.dumps(registry,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
report={
 'schema':'yado.g1.post_resource_assisted_development_regression_and_admission.v1',
 'status':'PASS_G1_POST_RESOURCE_ASSISTED_DEVELOPMENT_REGRESSION_AND_ADMISSION_V1' if passed else 'WITHHOLD_G1_POST_RESOURCE_ASSISTED_DEVELOPMENT_REGRESSION_AND_ADMISSION_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'generation':ledger['current_head'],'generation_head_digest_before':head_digest_before,
 'checks':{
   'baseline_g1_regression':baseline_pass,'inherited_conjunctive':conj_pass,
   'relational_policy':relation_pass,'budgeted_search':budget_pass,
   'unified_resource_portfolio':portfolio_pass,'canonical_head_unchanged':head_unchanged,
 },
 'baseline_results':baseline,'baseline_min':baseline_min,
 'conjunctive_result':conj_result,'relation_results':relation_results,'budget_results':budget_results,
 'portfolio_checks':portfolio_checks,
 'registry_digest':registry['registry_digest'],
 'input_evidence':{
   'access_receipt':access['receipt_sha256'],'budget_receipt':budget['receipt_sha256'],
   'portfolio_digest':pd,'conjunctive_component_digest':conj_entry['component_digest'],
 },
 'canonical_mutation':False,'promotion_applied':False,
 'generation_head_digest_after':ledger['current_head_digest'],
 'next_required_capability':'G2_SUCCESSOR_GENESIS_FROM_G1_ENRICHED_HEAD_V1' if passed else 'CONTINUE_G1_RESOURCE_ASSISTED_INTEGRATION_REPAIR',
 'semantic_boundary':'FRESH CROSS-CAPABILITY REGRESSION AND DEVELOPMENTAL ADMISSION. ACTIVE OVERLAY DOES NOT MODIFY CANONICAL G1 HEAD; NEXT EVOLUTIONARY STEP IS A G2 SUCCESSOR CANDIDATE.'
}
report['receipt_sha256']=h(report)
(ROOT/'yado_g1_post_resource_assisted_development_regression_admission_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')

e={
 'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G1_POST_RESOURCE_ASSISTED_ADMISSION",
 'event_type':'G1_DEVELOPMENTAL_CAPABILITY_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'G1_POST_RESOURCE_ASSISTED_DEVELOPMENT_REGRESSION_AND_ADMISSION_V1',
 'effect':'UNIFIED_G1_DEVELOPMENTAL_REGISTRY_ACTIVE; NEXT_G2_SUCCESSOR_GENESIS' if passed else 'RESOURCE_ASSISTED_STACK_ADMISSION_WITHHELD',
 'source_path':f'receipts/yado-g1-post-resource-assisted-development-regression-admission-v1-run-{run_id}.json',
 'source_digest':report['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False,
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x!='G1_POST_RESOURCE_ASSISTED_DEVELOPMENT_REGRESSION_AND_ADMISSION_V1']
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['G2_SUCCESSOR_GENESIS_FROM_G1_ENRICHED_HEAD_V1']))
    ledger['shadow_resolved_deficits']=sorted(set(ledger.get('shadow_resolved_deficits',[])+['G1_POST_RESOURCE_ASSISTED_DEVELOPMENT_REGRESSION_AND_ADMISSION_V1']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':report['status'],'checks':report['checks'],'baseline_min':baseline_min,
 'conjunctive_result':conj_result,'relation_results':relation_results,'budget_results':budget_results,
 'registry_digest':registry['registry_digest'],'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit('POST_RESOURCE_ASSISTED_ADMISSION_WITHHELD')
