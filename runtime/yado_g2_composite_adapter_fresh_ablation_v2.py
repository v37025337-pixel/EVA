from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_unified_execution_fabric_v1 import G2UnifiedExecutionFabricV1
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1
from yado_g2_composite_transfer_repair_adapter_v1 import G2CompositeTransferRepairAdapterV1

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def desc(cap,amb=False,n=0):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False,'context_ambiguous':amb,'nonce':n,'fresh_v2':True}
    if not amb:
        if cap==CAP_BUD:d['budget_limited']=True
        elif cap==CAP_RES:d['external_evidence_needed']=True
        elif cap==CAP_REL:d['relation_needed']=True
    return d

arch=load(REPO/'canonical/yado-g2-architecture-v1.json')
portfolio=load(REPO/'resources/yado-unified-external-resource-portfolio-v1.json')
routes=[]
for i in range(64):
    for cap in [CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]:
        routes.append({'input':desc(cap,False,9000+i%7),'expected':cap})
router=BoundedCapabilityRouterLearnerV1.synthesize(routes,routes,CAP_CONJ,min_support=5)

rows=[]
for a in [False,True]:
  for b in [False,True]:
    for c in [False,True]:
      for _ in range(10):
        rows.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
scalar=ConjunctiveRuleInducerV1.synthesize('COMPOSITE_ABLATION_V2_SCALAR','LOGIC',rows,min_support=2,max_rules=12)

class Rel:
    def execute(self,x):return 'ALLOW' if x.get('allow') else 'DENY'
relation=Rel()

def make_fabric():
    base=G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)
    return G2UnifiedExecutionFabricV1(base)

keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))

def make_task(cap,i,sid,amb=False):
    r=random.Random(260903500+i)
    if cap==CAP_CONJ:
        payload={'condition_a':True,'condition_b':True,'condition_c':True,'jitter':r.randint(0,9)}
        return {'kind':'scalar','descriptor':desc(cap,amb,i),'stream_id':sid,'payload':payload}
    if cap==CAP_REL:
        return {'kind':'relation','descriptor':desc(cap,amb,i),'stream_id':sid,'payload':{'allow':True,'jitter':r.randint(0,9)}}
    if cap==CAP_BUD:
        return {'kind':'budget','descriptor':desc(cap,amb,i),'stream_id':sid,'current_confidence':.15+(i%3)*.05,'target_confidence':.75,'remaining_budget':5.0,
                'stages':[{'stage_id':f'A{i}','cost':1.0,'expected_gain':.2,'quota_remaining':1,'available':True,'latency':1.0},
                          {'stage_id':f'B{i}','cost':3.0,'expected_gain':.6,'quota_remaining':1,'available':True,'latency':2.0}]}
    key=keys[i%len(keys)]
    return {'kind':'resource','descriptor':desc(cap,amb,i),'stream_id':sid,'route_key':key,'payload':{'jitter':r.randint(0,9)}}

def norm(mode,out):
    return {
      'selected':out.get('selected_capability',out.get('context_selected_capability')),
      'result':out.get('result'),
    }

def run_pair(i,cap,ablated=False):
    fa=make_fabric();fb=make_fabric()
    ca=G2CompositeTransferRepairAdapterV1(fa)
    db=ContextualStreamCapabilityAdapterV1(fb,'BOUNDED_STREAM_CONTEXT_MAP')
    sid=f'PAIR_{i}_{cap}'
    prime=make_task(cap,30000+i,sid,False)
    pa=ca.run(copy.deepcopy(prime),ablated_context=ablated)
    pb=db.run(copy.deepcopy(prime),ablated_context=ablated)
    follow=make_task(cap,40000+i,sid,True)
    aa=ca.run(copy.deepcopy(follow),ablated_context=ablated)
    ab=db.run(copy.deepcopy(follow),ablated_context=ablated)
    return {
      'prime_equal':norm('C',pa)==norm('D',pb),
      'follow_equal':norm('C',aa)==norm('D',ab),
      'composite_prime':norm('C',pa),'direct_prime':norm('D',pb),
      'composite_follow':norm('C',aa),'direct_follow':norm('D',ab),
    }

caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]
pairs=[]
abl_pairs=[]
for i in range(480):
    cap=caps[i%4]
    pairs.append(run_pair(i,cap,False))
for i in range(160):
    cap=caps[i%4]
    abl_pairs.append(run_pair(1000+i,cap,True))

prime_eq=sum(x['prime_equal'] for x in pairs)/len(pairs)
follow_eq=sum(x['follow_equal'] for x in pairs)/len(pairs)
abl_prime_eq=sum(x['prime_equal'] for x in abl_pairs)/len(abl_pairs)
abl_follow_eq=sum(x['follow_equal'] for x in abl_pairs)/len(abl_pairs)

# Independent aggregate memory-causality comparison.
def aggregate(mode):
    fabric=make_fabric()
    wrapper=G2CompositeTransferRepairAdapterV1(fabric) if mode=='COMPOSITE' else ContextualStreamCapabilityAdapterV1(fabric,'BOUNDED_STREAM_CONTEXT_MAP')
    good_exp=good_amb=good_abl=0
    total=320
    for i in range(total):
        cap=caps[i%4];sid=f'AGG_{mode}_{i}'
        prime=make_task(cap,50000+i,sid,False)
        p=wrapper.run(copy.deepcopy(prime))
        selected=p.get('selected_capability',p.get('context_selected_capability'))
        good_exp+=selected==cap
        follow=make_task(cap,60000+i,sid,True)
        q=wrapper.run(copy.deepcopy(follow))
        selected2=q.get('selected_capability',q.get('context_selected_capability'))
        good_amb+=selected2==cap
        try:
            a=wrapper.run(copy.deepcopy(follow),ablated_context=True)
            selected3=a.get('selected_capability',a.get('context_selected_capability'))
            good_abl+=selected3==cap
        except Exception:
            pass
    return {'explicit':good_exp/total,'ambiguous':good_amb/total,'ablated':good_abl/total,'causal_drop':good_amb/total-good_abl/total}

composite=aggregate('COMPOSITE')
direct=aggregate('DIRECT')
checks={
 'paired_prime_exact_1':prime_eq==1.0,
 'paired_ambiguous_exact_1':follow_eq==1.0,
 'paired_ablated_prime_exact_1':abl_prime_eq==1.0,
 'paired_ablated_follow_exact_1':abl_follow_eq==1.0,
 'direct_explicit_no_regression':direct['explicit']>=composite['explicit'],
 'direct_ambiguous_no_regression':direct['ambiguous']>=composite['ambiguous'],
 'direct_ablation_no_hidden_gain':direct['ablated']==composite['ablated'],
 'direct_causal_drop_no_regression':direct['causal_drop']>=composite['causal_drop']-1e-12,
}
status='PASS_COMPOSITE_ADAPTER_REDUNDANT_PAIRED_FRESH_V2' if all(checks.values()) else 'WITHHOLD_KEEP_COMPOSITE_ADAPTER_V2'
report={
 'schema':'yado.g2.composite_adapter_fresh_ablation.v2',
 'status':status,'checks':checks,
 'paired':{'count':len(pairs),'prime_exact':prime_eq,'ambiguous_exact':follow_eq},
 'paired_ablated':{'count':len(abl_pairs),'prime_exact':abl_prime_eq,'ambiguous_exact':abl_follow_eq},
 'aggregate':{'composite':composite,'direct_context_fabric':direct},
 'v1_context':{'status':'WITHHOLD_KEEP_COMPOSITE_ADAPTER','reason':'ABSOLUTE_AMBIGUOUS_THRESHOLD_MISMATCHED_REDUNDANCY_QUESTION'},
 'canonical_mutation':False,'removal_authorized':all(checks.values()),
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'PAIRED FRESH BEHAVIORAL EQUIVALENCE TEST. REMOVAL IS AUTHORIZED ONLY IF DIRECT CONTEXT+UNIFIED FABRIC MATCHES COMPOSITE EXACTLY ON PAIRED OUTPUTS AND DOES NOT REDUCE MEMORY CAUSALITY.'
}
report['receipt_sha256']=digest(report)
out=REPO/'candidates/kernel-self-generated/g2-composite-adapter-fresh-ablation-v2.json'
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
if not all(checks.values()):raise SystemExit(2)
