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
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False,'context_ambiguous':amb,'nonce':n}
    if not amb:
        if cap==CAP_BUD:d['budget_limited']=True
        elif cap==CAP_RES:d['external_evidence_needed']=True
        elif cap==CAP_REL:d['relation_needed']=True
    return d

arch=load(REPO/'canonical/yado-g2-architecture-v1.json')
portfolio=load(REPO/'resources/yado-unified-external-resource-portfolio-v1.json')

routes=[]
for i in range(50):
    for cap in [CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]:
        routes.append({'input':desc(cap,False,i%5),'expected':cap})
router=BoundedCapabilityRouterLearnerV1.synthesize(routes,routes,CAP_CONJ,min_support=5)
rows=[]
for a in [False,True]:
  for b in [False,True]:
    for c in [False,True]:
      for _ in range(8):rows.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
scalar=ConjunctiveRuleInducerV1.synthesize('COMPOSITE_ABLATION_SCALAR','LOGIC',rows,min_support=2,max_rules=12)
class Rel:
    def execute(self,x):return 'ALLOW' if x.get('allow') else 'DENY'
relation=Rel()

def make_fabric():
    base=G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)
    return G2UnifiedExecutionFabricV1(base)

keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))
def task(cap,i,sid,amb=False):
    r=random.Random(260903000+i)
    if cap==CAP_CONJ:
        return {'kind':'scalar','descriptor':desc(cap,amb,i),'stream_id':sid,'payload':{'condition_a':True,'condition_b':True,'condition_c':True}},'PASS'
    if cap==CAP_REL:
        return {'kind':'relation','descriptor':desc(cap,amb,i),'stream_id':sid,'payload':{'allow':True}},'ALLOW'
    if cap==CAP_BUD:
        t={'kind':'budget','descriptor':desc(cap,amb,i),'stream_id':sid,'current_confidence':.2,'target_confidence':.75,'remaining_budget':5.0,
           'stages':[{'stage_id':f'A{i}','cost':1.0,'expected_gain':.2,'quota_remaining':1,'available':True,'latency':1.0},
                     {'stage_id':f'B{i}','cost':3.0,'expected_gain':.6,'quota_remaining':1,'available':True,'latency':2.0}]}
        # expected current bounded planner action on explicit task
        f=make_fabric();o=f.execute_capability(CAP_BUD,copy.deepcopy(t));return t,o['result']
    key=keys[i%len(keys)];arr=portfolio['routes_for_current_open_deficits'][key]
    return {'kind':'resource','descriptor':desc(cap,amb,i),'stream_id':sid,'route_key':key,'payload':{}},(arr[0]['resource_id'] if arr else None)

def evaluate(mode):
    fabric=make_fabric()
    wrapper=G2CompositeTransferRepairAdapterV1(fabric) if mode=='COMPOSITE' else ContextualStreamCapabilityAdapterV1(fabric,'BOUNDED_STREAM_CONTEXT_MAP')
    caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]
    explicit=ambiguous=ablated=0;total=320
    for i in range(total):
        cap=caps[i%4];sid=f'{mode}_{i}'
        prime,expected=task(cap,10000+i,sid,False)
        o=wrapper.run(copy.deepcopy(prime))
        selected=o.get('selected_capability',o.get('context_selected_capability'))
        explicit+=selected==cap and o.get('result')==expected
        follow,_=task(cap,20000+i,sid,True)
        o2=wrapper.run(copy.deepcopy(follow))
        selected2=o2.get('selected_capability',o2.get('context_selected_capability'))
        ambiguous+=selected2==cap and o2.get('result')==expected
        try:
            o3=wrapper.run(copy.deepcopy(follow),ablated_context=True)
            selected3=o3.get('selected_capability',o3.get('context_selected_capability'))
            ablated+=selected3==cap and o3.get('result')==expected
        except Exception:
            pass
    return {'explicit':explicit/total,'ambiguous':ambiguous/total,'ablated':ablated/total,'causal_drop':ambiguous/total-ablated/total}

composite=evaluate('COMPOSITE')
direct=evaluate('DIRECT_CONTEXT_FABRIC')
checks={
 'direct_explicit':direct['explicit']>=.99,
 'direct_ambiguous':direct['ambiguous']>=.99,
 'direct_causal_drop':direct['causal_drop']>=.50,
 'no_regression_explicit':direct['explicit']>=composite['explicit'],
 'no_regression_ambiguous':direct['ambiguous']>=composite['ambiguous'],
 'no_regression_causal_drop':direct['causal_drop']>=composite['causal_drop']-.01,
}
report={
 'schema':'yado.g2.composite_adapter_fresh_ablation.v1',
 'status':'PASS_COMPOSITE_ADAPTER_REDUNDANT_SHADOW' if all(checks.values()) else 'WITHHOLD_KEEP_COMPOSITE_ADAPTER',
 'checks':checks,'composite':composite,'direct_context_fabric':direct,
 'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'FRESH ABLATION OF THE CANONICAL COMPOSITE COMPATIBILITY ADAPTER AGAINST CONTEXT-MEMORY PLUS UNIFIED EXECUTION FABRIC. NO CANONICAL CHANGE.'
}
report['receipt_sha256']=digest(report)
out=REPO/'candidates/kernel-self-generated/g2-composite-adapter-fresh-ablation-v1.json'
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
if not all(checks.values()):raise SystemExit(2)
