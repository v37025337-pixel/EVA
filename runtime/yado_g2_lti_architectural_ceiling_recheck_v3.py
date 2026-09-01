from __future__ import annotations
from pathlib import Path
from itertools import product
from fractions import Fraction
import hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_bounded_compositional_logic_v1 import BoundedCompositionalLogicV1
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1,program_acc
from yado_bounded_adaptive_contingent_planner_v1 import BoundedAdaptiveContingentPlannerV1,ContingentStage
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate

HEAD=REPO/'canonical'/'yado-main-head-g2.json';ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json';CORE=REPO/'canonical'/'yado-unified-core-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json';STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
OUT=ROOT/'yado_g2_lti_architectural_ceiling_recheck_v3_receipt.json'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1';CAP_RES='RESOURCE-PORTFOLIO-V1'
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))
head=load(HEAD);core=load(CORE);ledger=load(LEDGER);state=load(STATE);validate_ledger_v2(ledger)
allowed=[['LTI_ARCHITECTURAL_CEILING_RECHECK_V3'],['INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1']]
if ledger.get('open_deficits') not in allowed:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('open_deficits')==['INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1']:
    prev=REPO/'receipts'/'yado-g2-lti-architectural-ceiling-recheck-v3-run-33442875154.json'
    if not prev.exists():raise RuntimeError('V3_GATE_REPAIR_RETRY_WITHOUT_PRIOR_WITHHOLD')
    pr=load(prev)
    if pr.get('status')!='WITHHOLD_LTI_ARCHITECTURAL_CEILING_RECHECK_V3' or pr.get('planes',{}).get('LOGIC',{}).get('score')!=1.0 or pr.get('planes',{}).get('THINKING',{}).get('score')!=1.0:
        raise RuntimeError('V3_GATE_REPAIR_PRIOR_EVIDENCE_MISMATCH')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)
if state.get('fixed_architecture_sha256')!=arch_sha:raise RuntimeError('ARCHITECTURE_DRIFT')

# LOGIC V3
L=BoundedCompositionalLogicV1
def br(n,fn,p):
    return [{'input':{f'{p}{i}':v[i] for i in range(n)},'expected':'YES' if fn(v) else 'NO'} for v in product([False,True],repeat=n)]
lf={}
for name,rows in [('PARITY8',br(8,lambda v:sum(v)%2==1,'p')),('EXACT5OF10',br(10,lambda v:sum(v)==5,'e')),('THRESHOLD7OF11',br(11,lambda v:sum(v)>=7,'t'))]:
    m=L.learn_symmetric_boolean(rows);lf[name]=sum(L.predict_symmetric_boolean(m,z['input'])==z['expected'] for z in rows)/len(rows)
pts=[(x,y) for x in range(-4,5) for y in range(-4,5)]
poly=[{'x':x,'y':y,'expected':3*x**3-2*x*x*y+y**3+2*x-4} for x,y in pts]
pm=L.fit_polynomial(poly,max_degree=3);lf['CUBIC_V3']=sum(L.predict_polynomial(pm,z['x'],z['y'])==Fraction(z['expected']) for z in poly)/len(poly)
# non-symmetric bounded DNF regression
rows=br(5,lambda v:(v[0] and not v[1]) or (v[2] and v[3]) or (v[4] and v[1]),'n')
dp=BoundedDNFRelationPolicyInducerV1.synthesize('V3_NONSYM','LOGIC',rows,min_support=1,max_clauses=12,validation_cases=rows)
lf['NONSYMMETRIC_DNF']=program_acc(dp,rows)
logic_score=avg(list(lf.values()))

# THINKING V3
P=BoundedAdaptiveContingentPlannerV1;S=ContingentStage;tf={}
ok=0;n=100
for i in range(n):
    ids=[f'T{i}_{j}' for j in range(7)]
    stages=[S(ids[0],1,.05,1,True,.1,False,())]+[S(ids[j],1,.14,1,False,.1,False,(ids[j-1],)) for j in range(1,7)]
    p=P.next_after_observation(.18,.98,8,stages,ids[0],.05)
    ok+=p.action==ids[1] and p.expected_confidence>=.98-1e-9
tf['DEPENDENCY_CHAIN6']=ok/n
ok=0
for i in range(n):
    stages=[S(f'H{i}_{j}',1,.08,1,True,.1,False,()) for j in range(8)]
    p=P.plan(.20,.84,8,stages);ok+=p.expected_confidence>=.84-1e-9
tf['HORIZON8']=ok/n
ok=0
for i in range(n):
    a=f'A{i}';b=f'B{i}';c=f'C{i}'
    ss=[S(a,1,.1,1,True,.1,False,()),S(b,1,.25,1,True,.1,False,()),S(c,1,.25,1,True,.1,False,())]
    obs=(-.15,-.28)[i%2];p=P.next_after_observation(.7,.85,3,ss,a,obs)
    base=max(0,.7+obs);gain=sum(next(s.expected_gain for s in ss if s.stage_id==q) for q in p.sequence)
    ok+=abs(p.expected_confidence-min(1,base+gain))<1e-9
tf['SIGNED_UPDATE_V3']=ok/n
thinking_score=avg(list(tf.values()))

# INTELLIGENCE V3
def label(x):
    if x['budget_limited'] or x['quota_limited']:return CAP_BUD
    if x['external_evidence_needed']:return CAP_RES
    if x['relation_needed'] or x['disjunction_needed']:return CAP_REL
    return CAP_CONJ
def rr(seed,n):
    r=random.Random(seed);out=[]
    for _ in range(n):
        x={'budget_limited':r.random()<.23,'quota_limited':r.random()<.08,'external_evidence_needed':r.random()<.2,'relation_needed':r.random()<.25,'disjunction_needed':r.random()<.1,'noise':r.randrange(10**9)}
        out.append({'input':x,'expected':label(x)})
    return out
router=BoundedCapabilityRouterLearnerV1.synthesize(rr(91301,1600),rr(91302,700),CAP_CONJ,min_support=7)
test=rr(91303,650);single=sum(router.execute(z['input'])==z['expected'] for z in test)/len(test)
comp=[]
for i in range(300):
    x={'budget_limited':i%3==0,'quota_limited':False,'external_evidence_needed':True,'relation_needed':i%3!=0,'disjunction_needed':False}
    exp={CAP_RES,CAP_BUD} if i%3==0 else {CAP_RES,CAP_REL};comp.append((x,exp))
compose=sum(isinstance(router.execute(x),(list,tuple,set)) and set(router.execute(x))==exp for x,exp in comp)/len(comp)
alias=0
for i in range(300):
    z=test[i%len(test)];x=z['input'];a={'u':x['budget_limited'],'v':x['quota_limited'],'w':x['external_evidence_needed'],'r':x['relation_needed'],'d':x['disjunction_needed']}
    try:g=router.execute(a)
    except Exception:g=None
    alias+=g==z['expected']
alias/=300
sel=0
for i in range(200):
    r=random.Random(91400+i);cs=[];scores=[]
    for j in range(6):
        ev=r.random();cx=r.random();rk=r.random();nv=r.random();tok=f'S{i}_{j}';cs.append(EvidenceCandidate(tok,ev,cx,rk,nv));scores.append((ev-.05*cx-.25*rk+.03*nv,tok))
    got=NeutralEvidenceProfileSelectorV1.select(cs)['selected_token'];exp=sorted(scores,key=lambda q:(-q[0],q[1]))[0][1];sel+=got==exp
sel/=200
inf={'SINGLE_ROUTING_V3':single,'MULTI_CAPABILITY_COMPOSITION_V3':compose,'ZERO_SHOT_SCHEMA_ALIAS_V3':alias,'EVIDENCE_META_SELECTION_V3':sel}
intelligence_score=avg(list(inf.values()))

planes={'LOGIC':{'score':logic_score,'families':lf},'THINKING':{'score':thinking_score,'families':tf},'INTELLIGENCE':{'score':intelligence_score,'families':inf}}
ranking=sorted(planes,key=lambda p:(planes[p]['score'],p));weakest=ranking[0];threshold=float(state['ceiling_definition']['success_threshold_per_family'])
failed={p:[k for k,v in planes[p]['families'].items() if v<threshold] for p in planes}
all_at_target=all(not failed[p] for p in failed)
active=set()
for p in core.get('planes',[]): active.update(p.get('active_components',[]))
checks={'architecture_fixed':fsha(ARCH)==arch_sha,'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'logic_component_present':'ALG-G2-BOUNDED-COMPOSITIONAL-LOGIC-V1' in active,
 'thinking_component_present':'ALG-G2-BOUNDED-ADAPTIVE-CONTINGENT-PLANNER-V1' in active,'g3_not_started':head.get('g3_genesis_performed') is False}
passed=all(checks.values())
next_cap='LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V1' if all_at_target else f'{weakest}_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1'
state['round']=3;state['planes']=planes;state['ranking']=ranking;state['failed_families']=failed;state['self_selected_weakest_plane']=weakest
state['status']='ALL_FAMILIES_AT_THRESHOLD' if all_at_target else 'EVOLVING_TO_CEILING';state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.lti_architectural_ceiling_recheck.v3','status':'PASS_LTI_ARCHITECTURAL_CEILING_RECHECK_V3' if passed else 'WITHHOLD_LTI_ARCHITECTURAL_CEILING_RECHECK_V3',
 'planes':planes,'ranking':ranking,'failed_families':failed,'self_selected_weakest_plane':weakest,'all_families_at_threshold':all_at_target,'threshold':threshold,'checks':checks,
 'architecture_sha256':arch_sha,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'FRESH THREE-PLANE RECHECK AFTER CANONICAL THINKING+LOGIC IMPROVEMENTS; NEXT PLANE IS SELF-SELECTED UNDER FIXED G2 TOPOLOGY.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LTI_CEILING_RECHECK_V3",'event_type':'FIXED_ARCHITECTURE_CAPABILITY_CEILING_RECHECK',
 'status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':'LTI_ARCHITECTURAL_CEILING_RECHECK_V3',
 'effect':f"WEAKEST={weakest}; LOGIC={logic_score:.6f}; THINKING={thinking_score:.6f}; INTELLIGENCE={intelligence_score:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-lti-architectural-ceiling-recheck-v3-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'planes':planes,'ranking':ranking,'failed_families':failed,'self_selected_weakest_plane':weakest,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LTI_CEILING_RECHECK_V3_WITHHELD')
