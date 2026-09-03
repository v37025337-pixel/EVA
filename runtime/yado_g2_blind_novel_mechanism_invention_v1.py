from __future__ import annotations
from pathlib import Path
import hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_unified_execution_fabric_v3 import G2UnifiedExecutionFabricV3
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11
from yado_evolutionary_genome_v2 import YADOEvolutionaryGenomeV2
from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'
CAP_LOGIC_V2='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

def desc(cap):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False}
    if cap==CAP_BUD:d['budget_limited']=True
    elif cap==CAP_RES:d['external_evidence_needed']=True
    elif cap==CAP_REL:d['relation_needed']=True
    return d

def build_fabric(core):
    route=[]
    for i in range(20):
        for cap in [CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]:
            route.append({'input':desc(cap)|{'nonce':i%3},'expected':cap})
    router=BoundedCapabilityRouterLearnerV1.synthesize(route,route,CAP_CONJ,min_support=4)
    rows=[]
    for a in [False,True]:
      for b in [False,True]:
        for c in [False,True]:
          for _ in range(4):rows.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
    scalar=ConjunctiveRuleInducerV1.synthesize('BLIND_NOVEL_MECH_SCALAR','LOGIC',rows,min_support=2,max_rules=12)
    class Rel:
        def execute(self,x):return 'ALLOW' if x.get('allow') else 'DENY'
    base=G2TypedRecurrentCapabilityGraphRuntimeV1(core.architecture,router,scalar,Rel(),core.portfolio)
    return G2UnifiedExecutionFabricV3(base)

def truth(relation,start):
    state={start}
    for _ in range(128):
        nxt=state|{b for a,b in relation if a in state}
        if nxt==state:break
        state=nxt
    return tuple(sorted(state,key=lambda x:(str(type(x)),str(x))))

def case(rng,n,domain,cycle=False):
    token=''.join(rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(5))
    nodes=[f'{domain}_{token}_{i}' for i in range(n)]
    edges=[(nodes[i],nodes[i+1]) for i in range(n-1)]
    # Add branches reachable from the main chain.
    branch=f'{domain}_{token}_B'
    edges.append((nodes[max(0,n//2-1)],branch))
    # Add disconnected decoy relation so domain-seed shortcuts cannot pass.
    d0=f'{domain}_{token}_D0';d1=f'{domain}_{token}_D1'
    edges.append((d0,d1))
    if cycle and n>=4:edges.append((nodes[-1],nodes[1]))
    rng.shuffle(edges)
    return {'relation':tuple(edges),'start':nodes[0],'expected':truth(edges,nodes[0]),'domain':domain,'node_count':n}

seed=int(os.getenv('GITHUB_RUN_ID','260903')) ^ 0x59AD0
rng=random.Random(seed)
train=[case(rng,n,'TRAIN',cycle=(n%2==0)) for n in [5,6,7,5,7,6,5,7,6,7,5,6]]
holdout=[case(rng,n,'HOLD',cycle=(n%3==0)) for n in [8,9,10,11,12,8,10,12]]
transfer=[]
for domain,n in [('PACKAGE',9),('GENEALOGY',10),('WORKFLOW',11),('NETWORK',12),('DEPENDENCY',8),('CAUSAL',10)]:
    transfer.append(case(rng,n,domain,cycle=(n%2==1)))

core=UnifiedYADOCoreV1(REPO)
fabric=build_fabric(core)

# 1) Current parent CODE repair gets the examples but has no loop/iteration construction.
parent_source='def f(relation, start):\n    return start\n'
repair_examples=[((x['relation'],x['start']),x['expected']) for x in train[:8]]
try:
    parent_repair=AmbiguityAwareProgramRepairV11.repair(parent_source,'f',repair_examples,max_candidates=2500,max_edit_depth=2)
except Exception as e:
    parent_repair={'source':None,'reason':'PARENT_REPAIR_EXCEPTION','error_type':type(e).__name__,'error':str(e)[:512]}
parent_code_solved=bool(parent_repair.get('source'))
if parent_code_solved:
    try:
        parent_hold=sum(AmbiguityAwareProgramRepairV11.execute(parent_repair['source'],'f',(x['relation'],x['start']))==x['expected'] for x in holdout)/len(holdout)
    except Exception:parent_hold=0.0
else:parent_hold=0.0

# 2) Current Logic V2 receives the blind deficit repeatedly and Temporal Kernel must identify stall.
stall_errors=[]
for i in range(21):
    try:
        fabric.execute_capability(CAP_LOGIC_V2,{
          'operation':'infer_variable_depth_relation_state',
          'stream_id':'BLIND-NOVEL-MECHANISM',
          'deficit_id':'BLIND_VARIABLE_DEPTH_RELATIONAL_STATE',
          'progress_token':{'deficit':'BLIND_VARIABLE_DEPTH_RELATIONAL_STATE','resolution':'UNRESOLVED'},
          'prediction':'EXISTING_MECHANISM_MAY_RESOLVE',
          'cause':'BLIND_DEFICIT_ATTEMPT',
          'payload':{'attempt':i},
        })
    except Exception as e:
        stall_errors.append(type(e).__name__+':'+str(e))
stream_state=fabric.temporal_stream_state('BLIND-NOVEL-MECHANISM')
stall_records=[e for e in fabric.base.episodes if e.get('kind')=='TEMPORAL_STALL_SIGNAL']
stall_signal=stall_records[-1] if stall_records else {
  'mechanism_change_required':stream_state.get('mechanism_change_required'),
  'no_progress_ticks':stream_state.get('no_progress_ticks'),
  'tick_id':fabric.temporal_snapshot().get('tick_id'),
  'deficit_id':'BLIND_VARIABLE_DEPTH_RELATIONAL_STATE',
}

# 3) Canonical genome V1 can evolve known chromosomes, but none of its selected shadow gene IDs is this operator.
known_run=core.evolve_cognitive_code_genome()
parent_gene_ids=[x['gene_id'] for x in known_run['child']['chromosomes'].values()]
known_gene_families=[str(x) for x in parent_gene_ids]
known_family_has_relational_iteration=any(any(tok in x.upper() for tok in ('RELATION','STABLE','FIXPOINT','ITERAT')) for x in known_gene_families)

# 4) Shadow genome V2 invents a new operator from generic meta-language after the temporal stall.
parent_state=core.evolutionary_parent_genome()
v2=YADOEvolutionaryGenomeV2(parent_state['parent'],experience_sources=parent_state['experience'])
invented=v2.invent_operator_from_examples(train,stall_signal,parent_gene_ids)
gene=invented.get('gene',{})
program=gene.get('operator_program',{})

def accuracy(program,cases):
    if not program:return 0.0
    ok=0
    for x in cases:
        try:got=GenericRelationalMetaLanguageV1.execute(program,x['relation'],x['start'])
        except Exception:got=None
        ok+=got==x['expected']
    return ok/len(cases)

train_acc=accuracy(program,train)
hold_acc=accuracy(program,holdout)
transfer_acc=accuracy(program,transfer)
ablations=[]
for a in GenericRelationalMetaLanguageV1.ablations(program) if program else []:
    h=accuracy(a['program'],holdout)
    t=accuracy(a['program'],transfer)
    ablations.append({'field':a['ablated_field'],'value':a['ablated_value'],'holdout_accuracy':h,'transfer_accuracy':t,'program_digest':a['program']['program_digest']})
best_ablation=max([max(x['holdout_accuracy'],x['transfer_accuracy']) for x in ablations],default=0.0)

# Fixed shallow baselines from the same meta-language prove variable-depth requirement.
shallow=[]
for mode in ('ONCE','TWICE','THRICE'):
    p={'seed':'START','direction':'FORWARD','merge':'UNION','iteration':mode,'output':'STATE'}
    shallow.append({'iteration':mode,'holdout_accuracy':accuracy(p,holdout),'transfer_accuracy':accuracy(p,transfer)})

all_active=set(core.head.get('active_capabilities',[]))
checks={
 'current_parent_code_not_solution':parent_hold<1.0,
 'logic_parent_repeated_failure':len(stall_errors)==21 and len(set(stall_errors))==1,
 'temporal_stall_reached_20':stream_state.get('no_progress_ticks')==20,
 'temporal_requests_mechanism_change':stream_state.get('mechanism_change_required') is True and stall_signal.get('mechanism_change_required') is True,
 'known_genome_gene_family_not_matching':known_family_has_relational_iteration is False,
 'shadow_v2_self_synthesizes_gene':invented.get('status')=='SELF_SYNTHESIZED_SHADOW_GENE' and gene.get('novel_gene') is True,
 'new_gene_not_parent_gene':gene.get('gene_id') not in set(parent_gene_ids),
 'new_gene_not_active_capability':gene.get('gene_id') not in all_active,
 'train_exact':train_acc==1.0,
 'fresh_long_depth_holdout_exact':hold_acc==1.0,
 'cross_domain_transfer_exact':transfer_acc==1.0,
 'structural_ablation_causes_drop':best_ablation<1.0,
 'shallow_iteration_fails_fresh':all(x['holdout_accuracy']<1.0 and x['transfer_accuracy']<1.0 for x in shallow),
 'gene_remains_shadow':gene.get('promotion_state')=='SHADOW_ONLY',
 'automatic_promotion_false':YADOEvolutionaryGenomeV2.component().get('automatic_canonical_promotion') is False,
 'formal_generation_unchanged':core.head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
 'frontier_unchanged':core.head.get('current_frontier')=='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1',
 'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_BLIND_NOVEL_MECHANISM_INVENTION_V1' if all(checks.values()) else 'WITHHOLD_G2_BLIND_NOVEL_MECHANISM_INVENTION_V1'
report={
 'schema':'yado.g2.blind_novel_mechanism_invention.v1',
 'status':status,
 'checks':checks,
 'blind_deficit':{
   'deficit_id':'BLIND_VARIABLE_DEPTH_RELATIONAL_STATE',
   'training_case_count':len(train),
   'holdout_case_count':len(holdout),
   'transfer_case_count':len(transfer),
   'holdout_node_range':[min(x['node_count'] for x in holdout),max(x['node_count'] for x in holdout)],
   'transfer_domains':[x['domain'] for x in transfer],
   'domain_specific_operator_name_given_to_synthesizer':False,
 },
 'parent_failure':{
   'code_repair':parent_repair,
   'code_holdout_accuracy':parent_hold,
   'logic_error_signature':stall_errors[0] if stall_errors else None,
   'logic_failure_count':len(stall_errors),
   'known_shadow_gene_ids':parent_gene_ids,
 },
 'temporal_stall':{
   'stream_state':stream_state,
   'stall_signal':stall_signal,
   'temporal_snapshot':fabric.temporal_snapshot(),
 },
 'invented':invented,
 'fitness':{
   'train_accuracy':train_acc,
   'holdout_accuracy':hold_acc,
   'cross_domain_transfer_accuracy':transfer_acc,
   'best_structural_ablation_accuracy':best_ablation,
   'shallow_iteration_baselines':shallow,
 },
 'ablations':ablations,
 'meta_language':GenericRelationalMetaLanguageV1.component(),
 'controller_v2':YADOEvolutionaryGenomeV2.component(),
 'canonical_mutation':False,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'BLIND SHADOW TEST OF NOVEL OPERATOR INVENTION. THE SYNTHESIZER RECEIVES IO EXAMPLES AND GENERIC RELATION/STATE PRIMITIVES, NOT A DOMAIN-SPECIFIC OPERATOR NAME. SUCCESS DOES NOT PROMOTE THE GENE OR PROVE OPEN-ENDED SELF-EVOLUTION.'
}
report['receipt_sha256']=digest(report)
out=REPO/'candidates/kernel-self-generated/g2-blind-novel-mechanism-invention-v1.json'
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'checks':checks,
 'parent_code_holdout_accuracy':parent_hold,
 'temporal_no_progress_ticks':stream_state.get('no_progress_ticks'),
 'invented_gene_id':gene.get('gene_id'),
 'invented_program':program,
 'fitness':report['fitness'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if not all(checks.values()):raise SystemExit(2)
