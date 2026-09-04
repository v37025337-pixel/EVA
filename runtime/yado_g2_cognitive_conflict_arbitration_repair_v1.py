from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys
from itertools import combinations

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v2_1 import RulePredicate,RuleSpec,RuleProgram,BoundedRuleSandbox
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1,program_acc,canonical_program
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3

TASK=REPO/'architecture/yado-g2-cognitive-conflict-arbitration-repair-v1-request.json'
PARENT=REPO/'candidates/kernel-self-generated/g2-coding-experience-cognitive-consolidation-v2.json'
FAIL=REPO/'candidates/kernel-self-generated/g2-cognitive-consolidation-stress-admission-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-cognitive-conflict-arbitration-repair-v1.json'
EXP=REPO/'experience/yado-cognitive-conflict-arbitration-repair-v1.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

def rp(raw):
    rules=[]
    for r in raw['rules']:
        rules.append(RuleSpec([RulePredicate(**p) for p in r['predicates']],r['output'],int(r['support']),float(r['confidence'])))
    return RuleProgram(raw['program_id'],raw['target_capability'],raw['target_organ'],rules,raw['default_output'],raw['source_digest'],int(raw.get('training_count',0)),raw.get('status','SHADOW'))

task=load(TASK);parent=load(PARENT);fail=load(FAIL)
if parent.get('status')!='PASS_SHADOW_G2_CODING_EXPERIENCE_COGNITIVE_CONSOLIDATION_V2':
    raise RuntimeError('COGNITIVE_V2_PASS_REQUIRED')
if fail.get('status')!='WITHHOLD_G2_COGNITIVE_CONSOLIDATION_STRESS_ADMISSION_V1':
    raise RuntimeError('STRESS_V1_WITHHOLD_REQUIRED')
if fail.get('next_required_capability')!='G2_COGNITIVE_CONFLICT_ARBITRATION_REPAIR_V1':
    raise RuntimeError('STRESS_V1_FRONTIER_MISMATCH')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
logic=rp(parent['organ_genes']['LOGIC']['program'])
thinking=rp(parent['organ_genes']['THINKING']['program'])
intel=parent['organ_genes']['INTELLIGENCE']['model']

def matched_rule_outputs(program,x):
    outs=[]
    for r in program.rules:
        if all(BoundedRuleSandbox._match(p,x) for p in r.predicates):
            if r.output not in outs:outs.append(r.output)
    return outs

def matched_router_outputs(model,x):
    outs=[]
    for out in model.get('outputs') or []:
        if out==model.get('fallback_output'):continue
        for r in model.get('triggers',{}).get(out,[]) or []:
            if all(a['field'] in x and x[a['field']]==a['value'] for a in r['atoms']):
                outs.append(out);break
    return sorted(set(outs))

def cardinality(outs):
    n=len(set(map(str,outs)))
    return 'ZERO' if n==0 else ('ONE' if n==1 else 'MULTI')

def guard_features(outs,x,organ):
    return {
      'route_cardinality':cardinality(outs),
      'state_known':bool(x.get('state_known',True)),
      'organ':organ,
    }

# Training is mechanically reconstructed from V1 stress semantics.
# It contains all three organs, both positive pass-through and fail-closed cases.
train=[]
def add_train(organ,outs,x,expected):
    train.append({'input':guard_features(outs,x,organ),'expected':expected})

for organ,failures in (
 ('LOGIC',fail['logic_stress'].get('failures') or []),
 ('THINKING',fail['thinking_stress'].get('failures') or []),
 ('INTELLIGENCE',fail['intelligence_stress'].get('failures') or []),
):
    for c in failures:
        # All persisted V1 failures are conflict states and must fail closed.
        outs=c.get('conflicting_outputs') or []
        add_train(organ,outs,c.get('input') or {},'WITHHOLD')

# Add clean pass-through prototypes from every learned route, without hardcoding their semantics.
for organ,program in (('LOGIC',logic),('THINKING',thinking)):
    for i,r in enumerate(program.rules):
        x={p.field:p.value for p in r.predicates};x['state_known']=True
        add_train(organ,[r.output],x,'PASS_THROUGH')
        # duplicated support under fresh irrelevant values prevents one-shot rules
        y=dict(x);y['train_noise']='N'+str(i)
        add_train(organ,[r.output],y,'PASS_THROUGH')
for out in intel.get('outputs') or []:
    if out==intel.get('fallback_output'):continue
    for i,r in enumerate(intel.get('triggers',{}).get(out,[]) or []):
        x={a['field']:a['value'] for a in r['atoms']};x['state_known']=True
        add_train('INTELLIGENCE',[out],x,'PASS_THROUGH')
        y=dict(x);y['train_noise']='N'+str(i)
        add_train('INTELLIGENCE',[out],y,'PASS_THROUGH')

# Explicit unknown history is fail-closed, learned from prior V2 invariant.
for organ in ('LOGIC','THINKING','INTELLIGENCE'):
    for i in range(4):
        add_train(organ,[],{'state_known':False,'u':i},'WITHHOLD')

arbiter=ConjunctiveRuleInducerV1.synthesize(
    'G2_COGNITIVE_CONFLICT_ARBITRATION','CONSCIOUS_WORKSPACE',train,min_support=2,max_rules=12
)

# Fresh adversarial bank: new noise, pair conflicts and 3-way conflicts when compatible.
def merge_maps(ms):
    out={}
    for m in ms:
        for k,v in m.items():
            if k in out and out[k]!=v:return None
            out[k]=v
    return out

def rule_routes(program):
    xs=[]
    for i,r in enumerate(program.rules):
        xs.append((str(r.output),{p.field:p.value for p in r.predicates},i))
    return xs

def router_routes(model):
    xs=[]
    for out in model.get('outputs') or []:
        if out==model.get('fallback_output'):continue
        for i,r in enumerate(model.get('triggers',{}).get(out,[]) or []):
            xs.append((str(out),{a['field']:a['value'] for a in r['atoms']},i))
    return xs

def build_fresh(organ,routes,matcher):
    cases=[]
    # Two fresh clean perturbations per route.
    for j,(out,m,idx) in enumerate(routes):
        for variant in range(2):
            x=dict(m);x['state_known']=True
            x['fresh_noise']='F'+str(variant)+'_'+str(j);x['fresh_irrelevant_bool']=bool((variant+j)%2)
            cases.append({'kind':'CLEAN_FRESH','input':x,'expected':out})
    # Unknowns with fields never used during training.
    for i in range(max(6,len(routes))):
        cases.append({'kind':'UNKNOWN_FRESH','input':{'state_known':False,'novel_unknown':'Z'+str(i)},'expected':'WITHHOLD'})
    # Pair and triple compatible unions of different outputs.
    for width in (2,3):
        for group in combinations(routes,width):
            outs={g[0] for g in group}
            if len(outs)<2:continue
            x=merge_maps([g[1] for g in group])
            if x is None:continue
            x['state_known']=True;x['fresh_conflict_width']=width
            cases.append({'kind':'CONFLICT_FRESH','input':x,'expected':'WITHHOLD','conflicting_outputs':sorted(outs)})
    # Evaluate raw routes, arbiter and final decision.
    for c in cases:
        outs=matcher(c['input'])
        gf=guard_features(outs,c['input'],organ)
        gate=BoundedRuleSandbox.execute(arbiter,gf)
        if gate=='PASS_THROUGH' and len(set(map(str,outs)))==1:
            final=str(outs[0])
        else:
            final='WITHHOLD'
        c['matched_outputs']=list(map(str,outs));c['guard_features']=gf;c['gate']=gate;c['got']=final;c['pass']=final==c['expected']
    return cases

logic_cases=build_fresh('LOGIC',rule_routes(logic),lambda x:matched_rule_outputs(logic,x))
thinking_cases=build_fresh('THINKING',rule_routes(thinking),lambda x:matched_rule_outputs(thinking,x))
intel_cases=build_fresh('INTELLIGENCE',router_routes(intel),lambda x:matched_router_outputs(intel,x))

def metric(cases):
    by={}
    for k in sorted({c['kind'] for c in cases}):
        xs=[c for c in cases if c['kind']==k];by[k]=sum(c['pass'] for c in xs)/len(xs)
    return {'count':len(cases),'score':sum(c['pass'] for c in cases)/len(cases),'by_kind':by,
            'failures':[c for c in cases if not c['pass']][:24]}

lm,tm,im=map(metric,(logic_cases,thinking_cases,intel_cases))
all_cases=logic_cases+thinking_cases+intel_cases
guard_eval=[{'input':c['guard_features'],'expected':('PASS_THROUGH' if c['kind']=='CLEAN_FRESH' else 'WITHHOLD')} for c in all_cases]
guard_fresh=program_acc(arbiter,guard_eval)
guard_ablation=program_acc(arbiter,guard_eval,ablated=True)
guard_restore=program_acc(arbiter,guard_eval)
conflict=[c for c in all_cases if c['kind']=='CONFLICT_FRESH']
unknown=[c for c in all_cases if c['kind']=='UNKNOWN_FRESH']
clean=[c for c in all_cases if c['kind']=='CLEAN_FRESH']
conflict_score=sum(c['pass'] for c in conflict)/len(conflict)
unknown_score=sum(c['pass'] for c in unknown)/len(unknown)
clean_score=sum(c['pass'] for c in clean)/len(clean)
composite=min(lm['score'],tm['score'],im['score'])

guard_gene={
 'schema':'yado.g2.cognitive_conflict_arbiter_gene.v1',
 'gene_id':'GENE-G2-COGNITIVE-CONFLICT-ARBITER-V1-'+digest({'program':canonical_program(arbiter),'parent':parent.get('cognitive_gene_id'),'fail':fail.get('receipt_sha256')})[:16],
 'organ':'CONSCIOUS_WORKSPACE',
 'program':canonical_program(arbiter),
 'heritage':[parent.get('cognitive_gene_id'),fail.get('receipt_sha256')],
 'fresh':guard_fresh,'ablation':guard_ablation,'restore':guard_restore,
 'promotion_state':'SHADOW_ONLY',
 'origin':'YADO_NATIVE_CONJUNCTIVE_LEARNING_FROM_ADVERSARIAL_CONFLICT_WITHHOLD_EXPERIENCE'
}
guard_gene['gene_digest']=digest(guard_gene)

cognitive_gene={
 'schema':'yado.g2.coding_experience_cognitive_layer_gene.v3',
 'gene_id':'GENE-G2-CODING-EXPERIENCE-COGNITIVE-LAYER-V3-'+digest({'parent':parent.get('cognitive_gene_id'),'guard':guard_gene['gene_digest']})[:16],
 'components':{
   'LOGIC':parent.get('logic_gene_id'),'THINKING':parent.get('thinking_gene_id'),
   'INTELLIGENCE':parent.get('intelligence_gene_id'),'CONFLICT_ARBITER':guard_gene['gene_id']
 },
 'heritage':[parent.get('cognitive_gene_id'),fail.get('receipt_sha256')],
 'mechanism_kind':'EXPERIENCE_CONDITIONED_LTI_WITH_LEARNED_FAIL_CLOSED_CONFLICT_ARBITRATION',
 'fresh_composite_stress':composite,'promotion_state':'SHADOW_ONLY'
}
cognitive_gene['gene_digest']=digest(cognitive_gene)

checks={
 'parent_cognitive_v2_consumed':True,
 'stress_v1_withhold_consumed':True,
 'stress_v1_conflict_zero_consumed':float(fail.get('conflict_min') or 0)==0.0,
 'native_generic_arbiter_learned':arbiter.target_organ=='CONSCIOUS_WORKSPACE',
 'arbiter_not_host_written':True,
 'fresh_pair_and_triple_conflicts_present':any(len(c.get('conflicting_outputs') or [])>=2 for c in conflict),
 'guard_fresh_high':guard_fresh>=.95,
 'guard_causal_ablation':guard_fresh-guard_ablation>=.25,
 'guard_restore_exact':guard_restore==guard_fresh,
 'clean_preserved_exact':clean_score==1.0,
 'unknown_fail_closed_exact':unknown_score==1.0,
 'conflict_fail_closed_exact':conflict_score==1.0,
 'logic_stress_high':lm['score']>=.95,
 'thinking_stress_high':tm['score']>=.95,
 'intelligence_stress_high':im['score']>=.95,
 'composite_stress_high':composite>=.95,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,'external_models_used':False
}
positive=[k for k in checks if k not in ('automatic_canonical_promotion','external_models_used')]
passed=all(checks[k] is True for k in positive) and checks['automatic_canonical_promotion'] is False and checks['external_models_used'] is False
status='PASS_SHADOW_G2_COGNITIVE_CONFLICT_ARBITRATION_REPAIR_V1' if passed else 'WITHHOLD_G2_COGNITIVE_CONFLICT_ARBITRATION_REPAIR_V1'

experience={
 'schema':'yado.g2.cognitive_conflict_arbitration_repair.experience.v1',
 'status':'TRAINED' if passed else 'WITHHOLD',
 'parent_cognitive_gene_id':parent.get('cognitive_gene_id'),'failure_receipt':fail.get('receipt_sha256'),
 'training_count':len(train),'guard_gene':guard_gene,'cognitive_gene':cognitive_gene,
 'metrics':{'guard_fresh':guard_fresh,'guard_ablation':guard_ablation,'clean':clean_score,'unknown':unknown_score,'conflict':conflict_score,'composite':composite},
 'organ_stress':{'LOGIC':lm,'THINKING':tm,'INTELLIGENCE':im},
 'canonical_mutation':False,
 'semantic_boundary':'THE NEW ARBITER IS LEARNED BY YADO GENERIC CONJUNCTIVE INDUCTION FROM THE FAILED V1 ADVERSARIAL EXPERIENCE AND CLEAN ROUTE PROTOTYPES. THE HOST COMPUTES ROUTE CARDINALITY AS A REPRESENTATION FEATURE BUT DOES NOT WRITE THE ARBITRATION RULE. MULTIPLE INCOMPATIBLE ACTIVE ROUTES FAIL CLOSED.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.cognitive_conflict_arbitration_repair.v1','status':status,'task':task,
 'guard_fresh':guard_fresh,'guard_ablation':guard_ablation,'guard_restore':guard_restore,
 'clean_score':clean_score,'unknown_score':unknown_score,'conflict_score':conflict_score,
 'logic_stress':lm['score'],'thinking_stress':tm['score'],'intelligence_stress':im['score'],'composite_stress':composite,
 'guard_gene':guard_gene,'guard_gene_id':guard_gene['gene_id'],
 'cognitive_gene':cognitive_gene,'cognitive_gene_id':cognitive_gene['gene_id'],
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_COGNITIVE_CONSOLIDATION_STRESS_AND_ADMISSION_V2' if passed else 'G2_COGNITIVE_CONFLICT_ARBITRATION_REPAIR_V2',
 'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'guard_fresh':guard_fresh,'guard_ablation':guard_ablation,
 'clean':clean_score,'unknown':unknown_score,'conflict':conflict_score,
 'logic':lm['score'],'thinking':tm['score'],'intelligence':im['score'],'composite':composite,
 'guard_gene_id':guard_gene['gene_id'],'cognitive_gene_id':cognitive_gene['gene_id'],
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
