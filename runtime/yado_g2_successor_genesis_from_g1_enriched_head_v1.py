from __future__ import annotations
from pathlib import Path
from itertools import permutations
import copy,hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1,program_acc as conjunctive_acc
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1,program_acc as relation_acc
from yado_budgeted_stage_policy_v1 import BudgetedStagePolicyV1,SearchStage
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1,router_acc
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate

LEDGER=REPO/'architecture'/'evolution-ledger.json'
HEAD=REPO/'canonical'/'yado-main-head-g1-s2.json'
REGISTRY=REPO/'architecture'/'g1-developmental-capability-registry-v1.json'
PORTFOLIO=REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json'
TRAINING=REPO/'architecture'/'g1-training-state-v1.json'
POST=REPO/'receipts'/'yado-g1-post-resource-assisted-development-regression-admission-v1-run-33355904404.json'
OUT=REPO/'candidates'/'g2-successor-v1'
OUT.mkdir(parents=True,exist_ok=True)

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()

ledger=json.loads(LEDGER.read_text());head=json.loads(HEAD.read_text())
registry=json.loads(REGISTRY.read_text());portfolio=json.loads(PORTFOLIO.read_text())
training=json.loads(TRAINING.read_text());post=json.loads(POST.read_text())
validate_ledger_v2(ledger)

if ledger['current_head']!='G1_CANDIDATE_S2':raise RuntimeError('G1_NOT_HEAD')
if head.get('canonical_head_digest')!=ledger.get('current_head_digest'):raise RuntimeError('HEAD_DIGEST_MISMATCH')
if training.get('status')!='READY_FOR_G2_GENESIS':raise RuntimeError('G1_TRAINING_NOT_READY')
if training.get('stable_pass_streak',0)<5:raise RuntimeError('INSUFFICIENT_STABLE_G1_RUNS')
if post.get('status')!='PASS_G1_POST_RESOURCE_ASSISTED_DEVELOPMENT_REGRESSION_AND_ADMISSION_V1':raise RuntimeError('G1_POST_ADMISSION_MISSING')
g1_digest=ledger['current_head_digest']

# Generic structure constructor from typed capability inventory, not from a fixed G2 architecture name.
entries=registry['entries']
by_organ={}
for e in entries:by_organ.setdefault(e['organ'],[]).append(e['entry_id'])

planes=[
 {'plane_id':'P_MEMORY_LINEAGE','kind':'MEMORY_LINEAGE','members':['EVOLUTION_LEDGER','G1_TRAINING_STATE'],'stateful':True},
 {'plane_id':'P_RESOURCE_EVIDENCE','kind':'RESOURCE_EVIDENCE','members':[e['entry_id'] for e in entries if 'RESOURCE' in e['family']],'stateful':True},
 {'plane_id':'P_LOGIC','kind':'LOGIC_CAPABILITY','members':sorted(by_organ.get('LOGIC',[])),'stateful':False},
 {'plane_id':'P_THINKING','kind':'THINKING_PLANNING','members':sorted(by_organ.get('THINKING',[])),'stateful':False},
 {'plane_id':'P_INTELLIGENCE','kind':'INTELLIGENCE_META','members':sorted(by_organ.get('INTELLIGENCE',[]))+[
     'ALG-BOUNDED-CAPABILITY-ROUTER-V1','ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1'
 ],'stateful':False},
 {'plane_id':'P_WORKSPACE','kind':'RECURRENT_WORKSPACE_CORE','members':['G1_CANONICAL_COGNITIVE_CORE'],'stateful':True},
]
planes=[p for p in planes if p['members']]
edges=[
 {'src':'P_MEMORY_LINEAGE','dst':'P_INTELLIGENCE','channel':'COUNTEREXAMPLE_AND_PROVENANCE'},
 {'src':'P_RESOURCE_EVIDENCE','dst':'P_THINKING','channel':'COSTED_EVIDENCE_OPTIONS'},
 {'src':'P_THINKING','dst':'P_LOGIC','channel':'PLANNED_REASONING_TASK'},
 {'src':'P_LOGIC','dst':'P_INTELLIGENCE','channel':'STRUCTURED_INFERENCE_RESULT'},
 {'src':'P_INTELLIGENCE','dst':'P_WORKSPACE','channel':'SELECTED_ACTION_AND_SELF_MODEL_UPDATE'},
 {'src':'P_WORKSPACE','dst':'P_THINKING','channel':'RECURRENT_GOAL_CONTEXT'},
 {'src':'P_WORKSPACE','dst':'P_MEMORY_LINEAGE','channel':'EPISODE_COMMIT'},
 {'src':'P_MEMORY_LINEAGE','dst':'P_WORKSPACE','channel':'TEMPORAL_CONTEXT_RESTORE'},
]
existing={p['plane_id'] for p in planes};edges=[e for e in edges if e['src'] in existing and e['dst'] in existing]

# ---- fresh subsystem evidence for architecture construction ----
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def route_label(x):
    if x['budget_limited'] or x['quota_limited']:return CAP_BUD
    if x['external_evidence_needed']:return CAP_RES
    if x['relation_needed'] or x['disjunction_needed']:return CAP_REL
    return CAP_CONJ
def route_cases(seed,n):
    r=random.Random(seed);out=[]
    for _ in range(n):
        x={'budget_limited':bool(r.getrandbits(1)),'quota_limited':r.random()<.17,
           'external_evidence_needed':r.random()<.28,'relation_needed':r.random()<.32,
           'disjunction_needed':r.random()<.18,'noise':r.randint(-1000,1000)}
        out.append({'input':x,'expected':route_label(x)})
    return out
rt=route_cases(3100011,1100);rv=route_cases(3101011,500);rb=route_cases(3102011,1000)
router=BoundedCapabilityRouterLearnerV1.synthesize(rt,rv,CAP_CONJ,min_support=6)
router_fresh=router_acc(router,rb);router_ablation=router_acc(router,rb,ablated=True)

def scalar_cases(seed,n):
    r=random.Random(seed);out=[]
    for _ in range(n):
        x={'causal_ok':bool(r.getrandbits(1)),'fresh_ok':bool(r.getrandbits(1)),'rollback_ok':bool(r.getrandbits(1)),'noise':r.randrange(100000)}
        out.append({'input':x,'expected':'USE' if x['causal_ok'] and x['fresh_ok'] and x['rollback_ok'] else 'WAIT'})
    return out
st=scalar_cases(3110011,620);sv=scalar_cases(3111011,300);sb=scalar_cases(3112011,900)
sp=ConjunctiveRuleInducerV1.synthesize('G2_SCALAR','LOGIC',st,min_support=3,max_rules=12)
scalar_fresh=conjunctive_acc(sp,sb);scalar_ablation=conjunctive_acc(sp,sb,ablated=True)

def rel_cases(seed,n,pool):
    r=random.Random(seed);out=[]
    for _ in range(n):
        a=r.choice(pool);o=r.choice(pool);ta=r.choice(pool);tr=r.choice(pool)
        if r.random()<.4:a=o
        if r.random()<.4:tr=ta
        x={'agent':a,'owner':o,'agent_group':ta,'object_group':tr,'role':r.choice(['MEMBER','LEAD','GUEST']),
           'verified':bool(r.getrandbits(1)),'criticality':r.choice(['LOW','HIGH']),'noise':r.randint(-99,99)}
        if x['agent']==x['owner'] and x['verified']:y='ALLOW'
        elif x['agent_group']==x['object_group'] and x['role']=='MEMBER' and x['verified'] and x['criticality']=='HIGH':y='ALLOW'
        elif x['role']=='LEAD' and x['verified']:y='ALLOW'
        else:y='DENY'
        out.append({'input':x,'expected':y})
    return out
rtr=rel_cases(3120011,800,[f'T{i}' for i in range(14)])
rva=rel_cases(3121011,380,[f'V{i}' for i in range(14,28)])
rbl=rel_cases(3122011,1000,[f'B{i}' for i in range(28,56)])
rp=BoundedDNFRelationPolicyInducerV1.synthesize('G2_REL','LOGIC',rtr,min_support=4,max_clauses=12,validation_cases=rva)
relation_fresh=relation_acc(rp,rbl)
rel_abl=0
for e in rbl:
    out=rp.default_output
    for cl in rp.clauses:
        if any(a.op.startswith('FIELD_') for a in cl.atoms):continue
        if cl.match(e['input']):out=cl.output;break
    rel_abl+=out==e['expected']
relation_ablation=rel_abl/len(rbl)

def budget_oracle(cur,target,cap,stages):
    if cur>=target:return 'STOP'
    usable=[s for s in stages if s.available and s.quota_remaining>0 and not s.attempted];cand=[]
    for d in range(1,min(4,len(usable))+1):
        for seq in permutations(usable,d):
            cost=sum(s.cost for s in seq)
            if cost>cap+1e-12:continue
            conf=min(1,cur+sum(s.expected_gain for s in seq));lat=sum(s.latency for s in seq)
            reach=conf>=target
            key=(0,cost,d,lat,tuple(s.stage_id for s in seq)) if reach else (1,-conf,cost,lat,tuple(s.stage_id for s in seq))
            cand.append((key,seq))
    if not cand:return 'WITHHOLD'
    cand.sort(key=lambda z:z[0]);return cand[0][1][0].stage_id
rr=random.Random(3130011);n=700;bud_ok=bud_ab=viol=0
for i in range(n):
    costs=sorted([rr.uniform(.5,2.4),rr.uniform(2.5,6),rr.uniform(6.1,12),rr.uniform(12.1,25)])
    gains=sorted([rr.uniform(.05,.18),rr.uniform(.14,.3),rr.uniform(.25,.47),rr.uniform(.44,.7)])
    ss=[SearchStage(f'G2_{i}_{j}',costs[j],gains[j],0 if rr.random()<.08 else rr.randint(1,4),rr.random()>.04,rr.uniform(.2,5),False) for j in range(4)]
    cur=rr.uniform(.2,.65);target=rr.uniform(max(.72,cur+.08),.96);cap=rr.uniform(2.5,21)
    exp=budget_oracle(cur,target,cap,ss);p=BudgetedStagePolicyV1.plan(cur,target,cap,ss)
    bud_ok+=p.action==exp
    if p.feasible and p.total_cost>cap+1e-9:viol+=1
    bud_ab+=BudgetedStagePolicyV1.plan(cur,target,cap,ss,ignore_budget=True).action==exp
budget_fresh=bud_ok/n;budget_ablation=bud_ab/n

resource_route=portfolio['routes_for_current_open_deficits']
resource_ok=portfolio.get('resource_count',0)>=70 and all((not a) or a[0]['kind']=='local_evidence' for a in resource_route.values()) and not any(
    str(x.get('policy','')).startswith('EXCLUDED') for a in resource_route.values() for x in a
)

component_evidence={
 'scalar':scalar_fresh,'relation':relation_fresh,'budget':budget_fresh,
 'router':router_fresh,'resource':1.0 if resource_ok else 0.0,
 'neutral_selector':min(x['selector_metrics']['fresh_exact'] for x in training['rounds'][-5:]),
}

# Architecture variants are derived by ablation from the generated graph.
required={'scalar','relation','budget','router','resource','neutral_selector'}
variants=[]
ablations=[None,'relation','budget','router','resource','memory']
for ab in ablations:
    token='arch_'+h({'planes':planes,'edges':edges,'ablation':ab})[:16]
    present=set(required)
    if ab in present:present.remove(ab)
    # memory is a structural dependency: its loss damages meta continuity but not a named capability score.
    success=sum(component_evidence[k] for k in present)/len(required)
    if ab=='memory':success=max(0,success-.12)
    risk=(len(required-present)/len(required))+(0.18 if ab=='memory' else 0)
    complexity=(sum(len(p['members']) for p in planes)-(1 if ab else 0))/20
    novelty=.9 if ab is None else .55
    variants.append({'token':token,'ablation':ab,'evidence':success,'risk':risk,'complexity':complexity,'novelty':novelty,'present':sorted(present)})
sel=NeutralEvidenceProfileSelectorV1.select([
    EvidenceCandidate(v['token'],v['evidence'],v['complexity'],v['risk'],v['novelty']) for v in variants
])
selected=next(v for v in variants if v['token']==sel['selected_token'])

checks={
 'g1_training_ready':training['status']=='READY_FOR_G2_GENESIS' and training['stable_pass_streak']>=5,
 'router_fresh':router_fresh>=.99 and router_fresh-router_ablation>=.20,
 'scalar_fresh':scalar_fresh>=.99 and scalar_fresh-scalar_ablation>=.05,
 'relation_fresh':relation_fresh>=.99 and relation_fresh-relation_ablation>=.08,
 'budget_fresh':budget_fresh>=.99 and budget_fresh-budget_ablation>=.10 and viol==0,
 'resource_routing':resource_ok,
 'selected_full_architecture':selected['ablation'] is None,
 'g1_head_immutable':ledger['current_head_digest']==g1_digest,
}
passed=all(checks.values())

architecture={
 'schema':'yado.g2.typed_recurrent_capability_graph.v1',
 'architecture_family':'TYPED_RECURRENT_CAPABILITY_GRAPH',
 'architecture_id':'G2_ARCH_'+h({'planes':planes,'edges':edges,'selected':selected})[:16],
 'parent_generation_id':'G1_CANDIDATE_S2','parent_head_digest':g1_digest,
 'planes':planes,'edges':edges,
 'inherited_registry_digest':registry['registry_digest'],
 'inherited_capabilities':[e['entry_id'] for e in entries],
 'new_capabilities':['ALG-BOUNDED-CAPABILITY-ROUTER-V1','ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1','COUNTEREXAMPLE_LINEAGE_MEMORY_V1'],
 'architecture_selection':{'variants':variants,'neutral_selector_result':sel,'selected_variant':selected},
 'recurrent':True,'typed_channels':True,'resource_cost_aware':True,'counterexample_memory_bound':True,
 'canonical_active':False,'promotion_applied':False,
 'semantic_boundary':'EXECUTABLE-STRUCTURE CANDIDATE BUILT FROM VERIFIED G1 CAPABILITIES; NOT A CLAIM OF AGI OR SUBJECTIVE CONSCIOUSNESS',
}
architecture['architecture_digest']=h(architecture)
(OUT/'architecture.json').write_text(json.dumps(architecture,indent=2,sort_keys=True)+'\n')

candidate={
 'schema':'yado.g2.successor_candidate.v1',
 'candidate_generation_id':'G2_CANDIDATE_TRCG_V1',
 'parent_generation_id':'G1_CANDIDATE_S2','parent_head_digest':g1_digest,
 'architecture_digest':architecture['architecture_digest'],
 'training_state_digest':training['state_digest'],
 'capability_evidence':component_evidence,
 'causal_evidence':{
   'router_drop':router_fresh-router_ablation,'scalar_drop':scalar_fresh-scalar_ablation,
   'relation_drop':relation_fresh-relation_ablation,'budget_drop':budget_fresh-budget_ablation,
 },
 'checks':checks,'status':'READY_FOR_G2_PROMOTION_GATE' if passed else 'WITHHOLD',
 'canonical_mutation':False,'promotion_applied':False,
}
candidate['candidate_digest']=h(candidate)
(OUT/'candidate.json').write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.successor_genesis_from_g1_enriched_head.receipt.v1',
 'status':'PASS_G2_SUCCESSOR_GENESIS_FROM_G1_ENRICHED_HEAD_V1' if passed else 'WITHHOLD_G2_SUCCESSOR_GENESIS_FROM_G1_ENRICHED_HEAD_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'parent_generation_id':'G1_CANDIDATE_S2','candidate_generation_id':'G2_CANDIDATE_TRCG_V1',
 'architecture_family':architecture['architecture_family'],'architecture_id':architecture['architecture_id'],
 'architecture_digest':architecture['architecture_digest'],'candidate_digest':candidate['candidate_digest'],
 'component_evidence':component_evidence,
 'causal':candidate['causal_evidence'],'checks':checks,
 'variant_selection':architecture['architecture_selection'],
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_FULL_FRESH_REGRESSION_AND_PROMOTION_GATE_V1' if passed else 'CONTINUE_G1_TO_G2_ARCHITECTURE_REPAIR',
 'semantic_boundary':'G2 CANDIDATE GENESIS AND ARCHITECTURE SELECTION ONLY. G1 REMAINS CANONICAL UNTIL A SEPARATE FRESH PROMOTION GATE PASSES.'
}
receipt['receipt_sha256']=h(receipt)
(ROOT/'yado_g2_successor_genesis_from_g1_enriched_head_v1_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={
 'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_SUCCESSOR_GENESIS",
 'event_type':'GENERATION_SUCCESSOR_GENESIS','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':'G2_CANDIDATE_TRCG_V1','parent_generation':'G1_CANDIDATE_S2',
 'deficit':'G2_SUCCESSOR_GENESIS_FROM_G1_ENRICHED_HEAD_V1',
 'effect':'G2_TYPED_RECURRENT_CAPABILITY_GRAPH_CANDIDATE_CREATED; PROMOTION_GATE_REQUIRED' if passed else 'G2_CANDIDATE_GENESIS_WITHHELD',
 'source_path':f'receipts/yado-g2-successor-genesis-from-g1-enriched-head-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False,
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x!='G2_SUCCESSOR_GENESIS_FROM_G1_ENRICHED_HEAD_V1']
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['G2_FULL_FRESH_REGRESSION_AND_PROMOTION_GATE_V1']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'architecture_id':architecture['architecture_id'],'checks':checks,
 'component_evidence':component_evidence,'selected_variant':selected,'next_required_capability':receipt['next_required_capability'],
 'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('G2_GENESIS_WITHHELD')
