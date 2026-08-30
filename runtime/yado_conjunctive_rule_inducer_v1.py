from __future__ import annotations
from pathlib import Path
from collections import Counter,defaultdict
from dataclasses import asdict
from itertools import combinations,product
from typing import Any,Mapping,Sequence
import hashlib,json,os,sys,uuid,time,random

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v2_1 import (
    RulePredicate,RuleSpec,RuleProgram,RuleProgramSynthesizer,BoundedRuleSandbox
)

OUT=ROOT/'conjunctive_rule_inducer_v1'
OUT.mkdir(exist_ok=True)

def canon(o):
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def freeze(v):
    return canon(v)

class ConjunctiveRuleInducerV1:
    """
    Domain-neutral bounded learner.
    Searches pure conjunctions of observed scalar equality predicates.
    No domain field names, labels, or hand-written target rules are embedded.
    """
    MAX_ATOMS=64
    MAX_CONJUNCTION=2

    @classmethod
    def synthesize(cls,target_capability:str,target_organ:str,examples:Sequence[Mapping[str,Any]],
                   min_support:int=2,max_rules:int=12)->RuleProgram:
        if len(examples)<3:
            raise ValueError('at least 3 examples required')
        normalized=[]
        for e in examples:
            x=e.get('input')
            if not isinstance(x,Mapping) or 'expected' not in e:
                raise ValueError('each example requires mapping input and expected')
            normalized.append((dict(x),e['expected']))
        outputs=[freeze(y) for _,y in normalized]
        values={freeze(y):y for _,y in normalized}
        default_key=Counter(outputs).most_common(1)[0][0]
        default_output=values[default_key]

        # Observed scalar equality atoms only. Ignore high-cardinality values by support threshold.
        hits=defaultdict(list)
        atom_value={}
        for i,(x,_) in enumerate(normalized):
            for field,value in x.items():
                if isinstance(value,(str,int,float,bool)) or value is None:
                    key=('EQ',str(field),freeze(value))
                    hits[key].append(i);atom_value[key]=value
        atoms=[k for k,idxs in hits.items() if len(idxs)>=min_support]
        atoms.sort(key=lambda k:(-len(hits[k]),k))
        atoms=atoms[:cls.MAX_ATOMS]

        cands=[]
        for width in range(1,cls.MAX_CONJUNCTION+1):
            for ks in combinations(atoms,width):
                # Repeating the same field with different values can never match.
                if len({k[1] for k in ks})<len(ks):
                    continue
                idxs=set(hits[ks[0]])
                for k in ks[1:]:
                    idxs &= set(hits[k])
                support=len(idxs)
                if support<min_support:
                    continue
                labels=[outputs[i] for i in sorted(idxs)]
                if len(set(labels))!=1:
                    continue
                label=labels[0]
                if label==default_key:
                    continue
                preds=[RulePredicate(op=k[0],field=k[1],value=atom_value[k]) for k in ks]
                rule=RuleSpec(predicates=preds,output=values[label],support=support,confidence=1.0)
                # Prefer higher support, then fewer predicates, then canonical stable order.
                cands.append((-support,width,canon([asdict(p) for p in preds]),rule))
        cands.sort(key=lambda z:(z[0],z[1],z[2]))

        selected=[]
        signatures=set()
        for _,_,_,r in cands:
            sig=(freeze(r.output),canon([asdict(p) for p in r.predicates]))
            if sig in signatures:
                continue
            selected.append(r);signatures.add(sig)
            if len(selected)>=min(max_rules,BoundedRuleSandbox.MAX_RULES):
                break
        if not selected:
            raise ValueError('no stable conjunctive rule found')

        p=RuleProgram(
            program_id='CJ-'+uuid.uuid4().hex[:12],
            target_capability=target_capability,
            target_organ=target_organ,
            rules=selected,
            default_output=default_output,
            source_digest=hashlib.sha256(canon(list(examples)).encode()).hexdigest(),
            training_count=len(examples),
            status='SHADOW',
        )
        BoundedRuleSandbox.validate(p)
        return p

def program_acc(p,cases,ablated=False):
    if not cases:return 0.0
    return sum(BoundedRuleSandbox.execute(p,e['input'],ablated=ablated)==e['expected'] for e in cases)/len(cases)

def canonical_program(p):
    return {
      'program_id':p.program_id,
      'target_capability':p.target_capability,
      'target_organ':p.target_organ,
      'rules':[{
        'predicates':[asdict(q) for q in r.predicates],
        'output':r.output,'support':r.support,'confidence':r.confidence
      } for r in p.rules],
      'default_output':p.default_output,
      'source_digest':p.source_digest,
      'training_count':p.training_count,
      'status':p.status,
      'digest':p.digest(),
    }

# ---------------- Task 1: developmental priority filter ----------------
GEN=['THINKING_BOUNDARY_REASONING','INTELLIGENCE_BOUNDARY_REASONING','REPRESENTATION_INVARIANCE']
CAN=['UNIFY_BOOT_AND_STATE_LINEAGE','ADD_PREIMPORT_DEPENDENCY_LOCK','HARDEN_DIRECT_EVIDENCE_FETCH',
     'PROTECT_HISTORICAL_STATE_FROM_MUTATION','CONSOLIDATE_VALIDATED_FRONTIER_PORTFOLIO_INSTANCE_LOCALLY',
     'DURABILIZE_HOST_CAPABILITY_MODEL','STRUCTURAL_FRONTIER_ROUTER']
ALL=GEN+CAN

def contexts():
    return [dict(zip(
      ['lineage_verified','dependency_lock_verified','evidence_fetch_hardened',
       'historical_state_protected','current_generation_active'],vals
    )) for vals in product([False,True],repeat=5)]

def active(ctx):
    out=[]
    if ctx['current_generation_active']:out.extend(GEN)
    if not ctx['lineage_verified']:out.append(CAN[0])
    if not ctx['dependency_lock_verified']:out.append(CAN[1])
    if not ctx['evidence_fetch_hardened']:out.append(CAN[2])
    if not ctx['historical_state_protected']:out.append(CAN[3])
    out.extend(CAN[4:])
    return out

def dev_cases(ctxs,noise_seed):
    r=random.Random(noise_seed);out=[]
    for c in ctxs:
        for role in ALL:
            x={'role':role,**c,'irrelevant_nonce':r.randint(0,3)}
            out.append({'input':x,'expected':'KEEP' if role in active(c) else 'DROP'})
    return out

cs=contexts()
dev_train=dev_cases([c for i,c in enumerate(cs) if i%4 in (0,1)],1001)
dev_val=dev_cases([c for i,c in enumerate(cs) if i%4==2],2002)
dev_blind=dev_cases([c for i,c in enumerate(cs) if i%4==3],3003)

# ---------------- Transfer tasks ----------------
def transfer_a_cases(seed,n):
    r=random.Random(seed);out=[]
    for _ in range(n):
        x={
          'source_kind':r.choice(['REAL','SIMULATED','DERIVED']),
          'verified':r.choice([True,False]),
          'priority':r.choice(['LOW','HIGH']),
          'noise':r.randint(0,5),
        }
        y='WITHHOLD' if x['source_kind']=='SIMULATED' and not x['verified'] else 'ACCEPT'
        out.append({'input':x,'expected':y})
    return out

def transfer_b_cases(seed,n):
    r=random.Random(seed);out=[]
    for _ in range(n):
        x={
          'component':r.choice(['CORE','PLUGIN','EXPERIMENT']),
          'tests_passed':r.choice([True,False]),
          'rollback_ready':r.choice([True,False]),
          'noise':r.randint(0,5),
        }
        y='PROMOTE' if x['component']=='EXPERIMENT' and x['tests_passed'] and x['rollback_ready'] else 'HOLD'
        out.append({'input':x,'expected':y})
    return out

def ensure_support(gen,start=0):
    # concatenate deterministic batches until conjunction support is comfortably >=2
    out=[]
    for i in range(4):
        out.extend(gen(start+i,80))
    return out

TASKS={
 'DEVELOPMENTAL_FILTER':(dev_train,dev_val,dev_blind),
 'SOURCE_MONITOR_TRANSFER':(transfer_a_cases(4101,240),transfer_a_cases(4102,120),transfer_a_cases(4103,240)),
 'PROMOTION_GATE_TRANSFER':(transfer_b_cases(5101,320),transfer_b_cases(5102,160),transfer_b_cases(5103,320)),
}

results={}
all_pass=True
for name,(train,val,blind) in TASKS.items():
    baseline={'status':'UNAVAILABLE','validation':0.0,'fresh_blind':0.0}
    try:
        bp=RuleProgramSynthesizer.synthesize(name,'LOGIC',train,min_support=2)
        baseline={
          'status':'SYNTHESIZED',
          'validation':program_acc(bp,val),
          'fresh_blind':program_acc(bp,blind),
          'rule_count':len(bp.rules),
          'program':canonical_program(bp),
        }
    except Exception as e:
        baseline={'status':'REJECTED','reason':repr(e),'validation':0.0,'fresh_blind':0.0}

    t0=time.perf_counter()
    p=ConjunctiveRuleInducerV1.synthesize(name,'LOGIC',train,min_support=2)
    synth_s=time.perf_counter()-t0
    tr=program_acc(p,train);va=program_acc(p,val);bl=program_acc(p,blind)
    ab=program_acc(p,blind,ablated=True);restore=program_acc(p,blind)
    task_pass=tr==1.0 and va==1.0 and bl==1.0 and restore==1.0 and bl>ab
    all_pass &= task_pass
    results[name]={
      'pass':task_pass,
      'train':tr,'validation':va,'fresh_blind':bl,'ablation':ab,'restore':restore,
      'synthesis_seconds':synth_s,
      'baseline':baseline,
      'program':canonical_program(p),
    }

# Developmental composition: filter then canonical priority order.
dev_p_obj=ConjunctiveRuleInducerV1.synthesize('DEVELOPMENTAL_FILTER','LOGIC',dev_train+dev_val,min_support=2)
def effective(ctx,ablated=False):
    out=[]
    for role in ALL:
        payload={'role':role,**ctx,'irrelevant_nonce':99}
        if BoundedRuleSandbox.execute(dev_p_obj,payload,ablated=ablated)=='KEEP':
            out.append(role)
    return out

dev_exact=sum(effective(c)==active(c) for c in [x for i,x in enumerate(cs) if i%4==3])/8
dev_ab_exact=sum(effective(c,True)==active(c) for c in [x for i,x in enumerate(cs) if i%4==3])/8
current_ctx={'lineage_verified':True,'dependency_lock_verified':False,'evidence_fetch_hardened':False,
             'historical_state_protected':False,'current_generation_active':True}
current=effective(current_ctx);current_expected=active(current_ctx)

admission=all_pass and dev_exact==1.0 and dev_exact>dev_ab_exact and current==current_expected
component={
 'schema':'yado.conjunctive_rule_inducer.component.v1',
 'algorithm':{
   'max_atoms':ConjunctiveRuleInducerV1.MAX_ATOMS,
   'max_conjunction':ConjunctiveRuleInducerV1.MAX_CONJUNCTION,
   'min_support':2,'max_rules':12,
   'predicate_family':'OBSERVED_SCALAR_EQ',
 },
 'developmental_filter_program':canonical_program(dev_p_obj),
 'cross_domain_task_count':len(TASKS),
}
component['component_digest']=hashlib.sha256(canon(component).encode()).hexdigest()
(OUT/'component.json').write_text(json.dumps(component,indent=2,sort_keys=True,default=str)+'\n')

report={
 'schema':'yado.conjunctive_rule_inducer.receipt.v1',
 'status':'PASS_CONJUNCTIVE_RULE_INDUCER_V1' if admission else 'WITHHOLD_CONJUNCTIVE_RULE_INDUCER_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'origin':'HOST_SCAFFOLDED_GENERIC_ALGORITHM_CANDIDATE_FROM_KERNEL_DIAGNOSED_FILTER_DEFICIT',
 'execution_substrate':'EXISTING_YADO_BOUNDED_RULE_SANDBOX',
 'results':results,
 'developmental_filter_fresh_exact':dev_exact,
 'developmental_filter_ablation_exact':dev_ab_exact,
 'current_effective_priority':current,
 'current_expected_priority':current_expected,
 'current_pass':current==current_expected,
 'component':component,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'YADO_NATIVE_ALGORITHM_BANK_ADMISSION_AND_META_SELECTION' if admission else 'EXPAND_CONJUNCTION_SEARCH_OR_REPRESENTATION',
 'semantic_boundary':'GENERIC BOUNDED SYMBOLIC RULE-INDUCTION ALGORITHM; NOT FOUNDATION-MODEL TRAINING OR GENERAL INTELLIGENCE',
}
report['receipt_sha256']=hashlib.sha256(canon(report).encode()).hexdigest()
(ROOT/'yado_conjunctive_rule_inducer_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
 'status':report['status'],
 'task_results':{k:{q:v[q] for q in ('pass','train','validation','fresh_blind','ablation','restore','synthesis_seconds')} for k,v in results.items()},
 'baseline':{k:v['baseline'] for k,v in results.items()},
 'developmental_filter_fresh_exact':dev_exact,
 'developmental_filter_ablation_exact':dev_ab_exact,
 'current_pass':report['current_pass'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
