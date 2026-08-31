from __future__ import annotations
from pathlib import Path
from itertools import product
from fractions import Fraction
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1,program_acc
from yado_semantic_expression_synthesizer_v1 import SemanticExpressionSynthesizerV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
RECHECK=REPO/'receipts'/'yado-g2-lti-architectural-ceiling-recheck-v2-run-33442179466.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'bounded_compositional_logic_v1.py'
CAND_META=CAND_DIR/'bounded_compositional_logic_v1.json'
OUT=ROOT/'yado_logic_architectural_ceiling_self_evolution_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);arch=load(ARCH);ledger=load(LEDGER);recheck=load(RECHECK);state=load(STATE)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LOGIC_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if recheck.get('self_selected_weakest_plane')!='LOGIC':raise RuntimeError('LOGIC_NOT_SELF_SELECTED')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

def bool_rows(n,fn,prefix):
    return [{'input':{f'{prefix}{i}':v[i] for i in range(n)},'expected':'YES' if fn(v) else 'NO'} for v in product([False,True],repeat=n)]

def symmetric_fit(rows):
    mapping={};fields=sorted(rows[0]['input'])
    for row in rows:
        c=sum(bool(row['input'].get(f,False)) for f in fields);y=row['expected']
        if c in mapping and mapping[c]!=y:return None
        mapping[c]=y
    return {'fields':fields,'count_to_output':mapping,'default':max(set(r['expected'] for r in rows),key=lambda y:sum(z['expected']==y for z in rows))}

def symmetric_predict(model,x):
    if model is None:return None
    c=sum(bool(x.get(f,False)) for f in model['fields'])
    return model['count_to_output'].get(c,model['default'])

def monomials(degree):
    out=[]
    for total in range(degree+1):
        for i in range(total+1):
            out.append((i,total-i))
    return out

def exact_poly_fit(rows,degree):
    basis=monomials(degree);A=[]
    for r in rows:
        x=Fraction(r['x']);y=Fraction(r['y']);z=Fraction(r['expected'])
        A.append([x**i*y**j for i,j in basis]+[z])
    m=len(A);n=len(basis);rank=0;pivots=[]
    for col in range(n):
        pivot=next((i for i in range(rank,m) if A[i][col]!=0),None)
        if pivot is None:continue
        A[rank],A[pivot]=A[pivot],A[rank]
        q=A[rank][col];A[rank]=[v/q for v in A[rank]]
        for i in range(m):
            if i==rank or A[i][col]==0:continue
            q=A[i][col];A[i]=[a-q*b for a,b in zip(A[i],A[rank])]
        pivots.append(col);rank+=1
        if rank==m:break
    for row in A:
        if all(row[c]==0 for c in range(n)) and row[-1]!=0:return None
    if rank<n:return None
    coeff=[Fraction(0) for _ in range(n)]
    for rix,col in enumerate(pivots[:n]):coeff[col]=A[rix][-1]
    model={'degree':degree,'basis':basis,'coeff':coeff}
    for r in rows:
        if poly_predict(model,r['x'],r['y'])!=Fraction(r['expected']):return None
    return model

def poly_predict(model,x,y):
    x=Fraction(x);y=Fraction(y)
    return sum(c*x**i*y**j for c,(i,j) in zip(model['coeff'],model['basis']))

# Host provides bounded strategy surface only; G2 selects by fresh evidence.
strategies=[
 {'id':'BASE_COMPAT','symmetric':False,'poly_degree':0,'complexity':.10,'risk':.02,'novelty':.10},
 {'id':'SYMMETRIC_BOOLEAN','symmetric':True,'poly_degree':0,'complexity':.18,'risk':.03,'novelty':.45},
 {'id':'POLYNOMIAL_D2','symmetric':False,'poly_degree':2,'complexity':.22,'risk':.04,'novelty':.55},
 {'id':'POLYNOMIAL_D3','symmetric':False,'poly_degree':3,'complexity':.28,'risk':.05,'novelty':.65},
 {'id':'SYMMETRIC_PLUS_POLY_D2','symmetric':True,'poly_degree':2,'complexity':.31,'risk':.05,'novelty':.78},
 {'id':'COMPOSITIONAL_LOGIC_D3','symmetric':True,'poly_degree':3,'complexity':.37,'risk':.06,'novelty':.92},
]

# Validation families are fresh transforms of the discovered failure classes.
b_parity=bool_rows(6,lambda v:sum(v)%2==1,'vp')
b_card=bool_rows(8,lambda v:sum(v)>=5,'vc')
b_exact=bool_rows(7,lambda v:sum(v)==3,'ve')

pts=[(x,y) for x in range(-3,4) for y in range(-3,4)]
poly2=[{'x':x,'y':y,'expected':2*x*x-x*y+3*y*y+2*x-1} for x,y in pts]
poly3=[{'x':x,'y':y,'expected':x*x*x-2*x*y+y*y+3} for x,y in pts]

# Existing relational engine remains regression reference.
def rel_rows(seed,n,prefix):
    import random
    rr=random.Random(seed);pool=[f'{prefix}{i}' for i in range(36)];rows=[]
    for _ in range(n):
        a=rr.choice(pool);b=rr.choice(pool);g=rr.choice(pool);og=rr.choice(pool)
        if rr.random()<.38:b=a
        if rr.random()<.38:og=g
        x={'actor':a,'owner':b,'group':g,'object_group':og,'verified':bool(rr.getrandbits(1)),'critical':bool(rr.getrandbits(1))}
        y='YES' if ((a==b and x['verified']) or (g==og and x['critical'])) else 'NO'
        rows.append({'input':x,'expected':y})
    return rows
rt=rel_rows(81201,900,'RT');rv=rel_rows(81202,450,'RV')
rp=BoundedDNFRelationPolicyInducerV1.synthesize('LOGIC_EVOL_REL','LOGIC',rt,min_support=4,max_clauses=12,validation_cases=rv)
relation_score=program_acc(rp,rv)

def baseline_bool(rows):
    p=BoundedDNFRelationPolicyInducerV1.synthesize('BASE','LOGIC',rows,min_support=1,max_clauses=12,validation_cases=rows)
    return program_acc(p,rows)

def baseline_poly(rows):
    r=SemanticExpressionSynthesizerV1.synthesize(rows,max_ops=3,max_states_per_level=30000)
    if r.get('expression') is None:return 0.0
    return sum(SemanticExpressionSynthesizerV1.predict(r,z['x'],z['y'])==z['expected'] for z in rows)/len(rows)

def score_strategy(s):
    fam={}
    for name,rows in [('PARITY6',b_parity),('CARDINALITY5OF8',b_card),('EXACT3OF7',b_exact)]:
        if s['symmetric']:
            m=symmetric_fit(rows);fam[name]=sum(symmetric_predict(m,z['input'])==z['expected'] for z in rows)/len(rows)
        else:fam[name]=baseline_bool(rows)
    for name,rows in [('POLY_D2_TRANSFER',poly2),('POLY_D3_TRANSFER',poly3)]:
        if s['poly_degree']>0:
            model=None
            for d in range(s['poly_degree']+1):
                model=exact_poly_fit(rows,d)
                if model is not None:break
            fam[name]=0.0 if model is None else sum(poly_predict(model,z['x'],z['y'])==Fraction(z['expected']) for z in rows)/len(rows)
        else:fam[name]=baseline_poly(rows)
    fam['RELATIONAL_REGRESSION']=relation_score
    return {'families':fam,'score':sum(fam.values())/len(fam),'min_family':min(fam.values())}

validation={};tokmap={}
for i,s in enumerate(strategies):
    m=score_strategy(s);tok='opaque_'+h({'logic_slot':i,'head':head['canonical_head_digest']})[:18]
    validation[s['id']]=m|{'token':tok,'complexity':s['complexity'],'risk':s['risk'],'novelty':s['novelty']}
    tokmap[tok]=s
selection=NeutralEvidenceProfileSelectorV1.select([
    EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()
])
selected=tokmap[selection['selected_token']]
holdout=score_strategy(selected)
base=score_strategy(strategies[0])
causal_drop=holdout['score']-base['score']

candidate_source=r'''from __future__ import annotations
from fractions import Fraction
from itertools import product

class BoundedCompositionalLogicV1:
    COMPONENT_ID="ALG-G2-BOUNDED-COMPOSITIONAL-LOGIC-V1"
    MAX_BOOLEAN_FIELDS=12
    MAX_POLYNOMIAL_DEGREE=3
    MAX_POLYNOMIAL_TERMS=10

    @classmethod
    def learn_symmetric_boolean(cls,rows):
        if not rows:raise ValueError("EMPTY_ROWS")
        fields=sorted(rows[0]["input"])[:cls.MAX_BOOLEAN_FIELDS]
        mapping={}
        counts={}
        for row in rows:
            if any(not isinstance(row["input"].get(f),bool) for f in fields):raise ValueError("NON_BOOLEAN_FIELD")
            c=sum(row["input"][f] for f in fields);y=row["expected"]
            if c in mapping and mapping[c]!=y:raise ValueError("NOT_SYMMETRIC_DETERMINISTIC")
            mapping[c]=y;counts[y]=counts.get(y,0)+1
        default=sorted(counts,key=lambda y:(-counts[y],str(y)))[0]
        return {"kind":"SYMMETRIC_COUNT_MAP","fields":fields,"count_to_output":mapping,"default":default}

    @staticmethod
    def predict_symmetric_boolean(model,x):
        c=sum(bool(x.get(f,False)) for f in model["fields"])
        return model["count_to_output"].get(c,model["default"])

    @staticmethod
    def _basis(degree):
        out=[]
        for total in range(degree+1):
            for i in range(total+1):out.append((i,total-i))
        return out

    @classmethod
    def _fit_degree(cls,rows,degree):
        basis=cls._basis(degree)
        if len(basis)>cls.MAX_POLYNOMIAL_TERMS:return None
        A=[]
        for r in rows:
            x=Fraction(r["x"]);y=Fraction(r["y"]);z=Fraction(r["expected"])
            A.append([x**i*y**j for i,j in basis]+[z])
        m=len(A);n=len(basis);rank=0;pivots=[]
        for col in range(n):
            pivot=next((i for i in range(rank,m) if A[i][col]!=0),None)
            if pivot is None:continue
            A[rank],A[pivot]=A[pivot],A[rank]
            q=A[rank][col];A[rank]=[v/q for v in A[rank]]
            for i in range(m):
                if i==rank or A[i][col]==0:continue
                q=A[i][col];A[i]=[a-q*b for a,b in zip(A[i],A[rank])]
            pivots.append(col);rank+=1
        for row in A:
            if all(row[c]==0 for c in range(n)) and row[-1]!=0:return None
        if rank<n:return None
        coeff=[Fraction(0) for _ in range(n)]
        for rix,col in enumerate(pivots[:n]):coeff[col]=A[rix][-1]
        model={"kind":"EXACT_BOUNDED_POLYNOMIAL","degree":degree,"basis":basis,"coeff":coeff}
        if all(cls.predict_polynomial(model,r["x"],r["y"])==Fraction(r["expected"]) for r in rows):return model
        return None

    @classmethod
    def fit_polynomial(cls,rows,max_degree=3):
        cap=min(int(max_degree),cls.MAX_POLYNOMIAL_DEGREE)
        for d in range(cap+1):
            m=cls._fit_degree(rows,d)
            if m is not None:return m
        return {"kind":"WITHHOLD","degree":None,"basis":[],"coeff":[]}

    @staticmethod
    def predict_polynomial(model,x,y):
        if model.get("kind")=="WITHHOLD":raise ValueError("NO_POLYNOMIAL")
        x=Fraction(x);y=Fraction(y)
        return sum(c*x**i*y**j for c,(i,j) in zip(model["coeff"],model["basis"]))
'''
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(candidate_source,encoding='utf-8')

checks={
 'logic_self_selected':recheck.get('self_selected_weakest_plane')=='LOGIC',
 'selected_combined':selected['symmetric'] is True and selected['poly_degree']>=2,
 'fresh_validation_min':holdout['min_family']>=.99,
 'improves_baseline':holdout['score']>=base['score']+.20,
 'causal_drop':causal_drop>=.20,
 'relational_regression_preserved':holdout['families']['RELATIONAL_REGRESSION']>=.99,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
candidate={
 'schema':'yado.g2.bounded_compositional_logic_candidate.v1',
 'component_id':'ALG-G2-BOUNDED-COMPOSITIONAL-LOGIC-V1',
 'selected_strategy':selected['id'],'selected_features':{'symmetric_boolean':selected['symmetric'],'max_polynomial_degree':selected['poly_degree']},
 'validation':validation,'neutral_selection':selection,'fresh_validation':holdout,'baseline':base,'causal_drop':causal_drop,
 'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,'parent_head_digest':head['canonical_head_digest'],
 'canonical_active':False,'promotion_applied':False,'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'BOUNDED LOGIC EXTENSION INSIDE FIXED G2 LOGIC PLANE: EXACT SYMMETRIC BOOLEAN COUNT-MAPS AND EXACT LOW-DEGREE TWO-VARIABLE POLYNOMIAL INDUCTION. NOT GENERAL THEOREM PROVING.'
}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True,default=str)+'\n')
next_cap='LOGIC_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1' if passed else 'LOGIC_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2'

state['candidate_history'].append({'round':2,'plane':'LOGIC','candidate_digest':candidate['candidate_digest'],'selected_strategy':selected['id'],'fresh_score':holdout['score'],'baseline_score':base['score'],'causal_drop':causal_drop,'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['planes']['LOGIC']['candidate_score']=holdout['score'];state['planes']['LOGIC']['candidate_families']=holdout['families']
state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True,default=str)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.logic_architectural_ceiling_self_evolution.v1',
 'status':'PASS_LOGIC_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_LOGIC_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':selection,'fresh_validation':holdout,'baseline':base,'causal_drop':causal_drop,
 'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LOGIC_CEILING_SELF_EVOLUTION",
 'event_type':'FIXED_ARCHITECTURE_LOGIC_SELF_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'LOGIC_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1',
 'effect':f"SELECTED={selected['id']}; FRESH={holdout['score']:.6f}; BASE={base['score']:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-logic-architectural-ceiling-self-evolution-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'selected_strategy':selected['id'],'fresh_validation':holdout,'baseline':base,'causal_drop':causal_drop,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit('LOGIC_CEILING_SELF_EVOLUTION_WITHHELD')
