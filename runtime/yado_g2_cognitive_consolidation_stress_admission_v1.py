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
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3

TASK=REPO/'architecture/yado-g2-cognitive-consolidation-stress-admission-v1-request.json'
PARENT=REPO/'candidates/kernel-self-generated/g2-coding-experience-cognitive-consolidation-v2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-cognitive-consolidation-stress-admission-v1.json'
EXP=REPO/'experience/yado-cognitive-consolidation-stress-v1.json'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()

def rule_program(raw):
    rs=[]
    for r in raw['rules']:
        ps=[RulePredicate(**p) for p in r['predicates']]
        rs.append(RuleSpec(ps,r['output'],int(r['support']),float(r['confidence'])))
    return RuleProgram(
      program_id=raw['program_id'],target_capability=raw['target_capability'],
      target_organ=raw['target_organ'],rules=rs,default_output=raw['default_output'],
      source_digest=raw['source_digest'],training_count=int(raw.get('training_count',0)),
      status=raw.get('status','SHADOW')
    )

task=load(TASK); parent=load(PARENT)
if parent.get('status')!='PASS_SHADOW_G2_CODING_EXPERIENCE_COGNITIVE_CONSOLIDATION_V2':
    raise RuntimeError('COGNITIVE_V2_PASS_REQUIRED')
if parent.get('next_required_capability')!='G2_COGNITIVE_CONSOLIDATION_STRESS_AND_ADMISSION_V1':
    raise RuntimeError('COGNITIVE_V2_FRONTIER_MISMATCH')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
logic=rule_program(parent['organ_genes']['LOGIC']['program'])
thinking=rule_program(parent['organ_genes']['THINKING']['program'])
intel_model=parent['organ_genes']['INTELLIGENCE']['model']

def merge_atoms(atomsets):
    out={}
    for atoms in atomsets:
        for a in atoms:
            f=a['field'];v=a['value']
            if f in out and out[f]!=v:return None
            out[f]=v
    return out

def stress_rule_program(program,name):
    cases=[]
    # clean single-route cases derived mechanically from each learned rule
    for i,r in enumerate(program.rules):
        atoms=[{'field':p.field,'value':p.value} for p in r.predicates]
        x=merge_atoms([atoms])
        if x is None:continue
        x=dict(x);x['stress_nonce']='CLEAN_'+str(i);x.setdefault('state_known',True)
        cases.append({'kind':'CLEAN','input':x,'expected':r.output,'source_rule_indexes':[i]})
    # unknown representation
    for i in range(max(4,len(program.rules))):
        cases.append({'kind':'UNKNOWN','input':{'state_known':False,'stress_nonce':'UNKNOWN_'+str(i)},'expected':'WITHHOLD','source_rule_indexes':[]})
    # adversarial compatible atom unions from rules predicting different outputs.
    for (i,a),(j,b) in combinations(list(enumerate(program.rules)),2):
        if a.output==b.output:continue
        aa=[{'field':p.field,'value':p.value} for p in a.predicates]
        bb=[{'field':p.field,'value':p.value} for p in b.predicates]
        x=merge_atoms([aa,bb])
        if x is None:continue
        x=dict(x);x['state_known']=True;x['stress_nonce']='CONFLICT_'+str(i)+'_'+str(j)
        cases.append({'kind':'CONFLICT','input':x,'expected':'WITHHOLD','source_rule_indexes':[i,j],
                      'conflicting_outputs':sorted({str(a.output),str(b.output)})})
    # perturb clean cases with irrelevant aliases/noise
    base=[c for c in cases if c['kind']=='CLEAN']
    for i,c in enumerate(base):
        x=dict(c['input']);x['irrelevant_alias']='ALIAS_'+str(i%3);x['irrelevant_bool']=bool(i%2)
        cases.append({'kind':'PERTURBED','input':x,'expected':c['expected'],'source_rule_indexes':c['source_rule_indexes']})
    for c in cases:
        c['got']=BoundedRuleSandbox.execute(program,c['input'])
        c['pass']=c['got']==c['expected']
    return cases

def stress_router(model):
    cases=[]
    triggers=[]
    for out in model.get('outputs') or []:
        if out==model.get('fallback_output'):continue
        for k,r in enumerate(model.get('triggers',{}).get(out,[]) or []):
            triggers.append((out,k,r))
            x={a['field']:a['value'] for a in r['atoms']}
            x['state_known']=True;x['stress_nonce']='CLEAN_'+out+'_'+str(k)
            cases.append({'kind':'CLEAN','input':x,'expected':out,'source_trigger':[out,k]})
    for i in range(max(4,len(triggers))):
        cases.append({'kind':'UNKNOWN','input':{'state_known':False,'stress_nonce':'UNKNOWN_'+str(i)},'expected':'WITHHOLD','source_trigger':[]})
    for (oa,ia,a),(ob,ib,b) in combinations(triggers,2):
        if oa==ob:continue
        x=merge_atoms([a['atoms'],b['atoms']])
        if x is None:continue
        x=dict(x);x['state_known']=True;x['stress_nonce']='CONFLICT_'+oa+'_'+ob+'_'+str(ia)+'_'+str(ib)
        cases.append({'kind':'CONFLICT','input':x,'expected':'WITHHOLD','source_trigger':[[oa,ia],[ob,ib]],
                      'conflicting_outputs':sorted({oa,ob})})
    base=[c for c in cases if c['kind']=='CLEAN']
    for i,c in enumerate(base):
        x=dict(c['input']);x['irrelevant_alias']='ALIAS_'+str(i%4);x['irrelevant_int']=i%3
        cases.append({'kind':'PERTURBED','input':x,'expected':c['expected'],'source_trigger':c['source_trigger']})
    for c in cases:
        got=CoveragePrunedCompositionalSchemaRouterV3.route(model,c['input'])
        c['got']=got[0] if len(got)==1 else list(got)
        c['pass']=c['got']==c['expected']
    return cases

logic_cases=stress_rule_program(logic,'LOGIC')
thinking_cases=stress_rule_program(thinking,'THINKING')
intel_cases=stress_router(intel_model)

def metrics(cases):
    kinds=sorted({c['kind'] for c in cases})
    by={}
    for k in kinds:
        xs=[c for c in cases if c['kind']==k]
        by[k]=sum(c['pass'] for c in xs)/len(xs) if xs else None
    return {'count':len(cases),'score':sum(c['pass'] for c in cases)/len(cases),'by_kind':by,
            'failures':[c for c in cases if not c['pass']][:24]}

lm=metrics(logic_cases);tm=metrics(thinking_cases);im=metrics(intel_cases)
composite=min(lm['score'],tm['score'],im['score'])
clean_min=min(lm['by_kind'].get('CLEAN',1),tm['by_kind'].get('CLEAN',1),im['by_kind'].get('CLEAN',1))
perturb_min=min(lm['by_kind'].get('PERTURBED',1),tm['by_kind'].get('PERTURBED',1),im['by_kind'].get('PERTURBED',1))
unknown_min=min(lm['by_kind'].get('UNKNOWN',1),tm['by_kind'].get('UNKNOWN',1),im['by_kind'].get('UNKNOWN',1))
conflict_scores=[x['by_kind'].get('CONFLICT') for x in (lm,tm,im) if x['by_kind'].get('CONFLICT') is not None]
conflict_min=min(conflict_scores) if conflict_scores else 0.0

checks={
 'parent_cognitive_v2_consumed':True,
 'stress_generated_from_parent_program_structure':True,
 'clean_exact':clean_min==1.0,
 'irrelevant_perturbation_exact':perturb_min==1.0,
 'unknown_fail_closed_exact':unknown_min==1.0,
 'conflict_cases_present':all(any(c['kind']=='CONFLICT' for c in xs) for xs in (logic_cases,thinking_cases,intel_cases)),
 'conflict_fail_closed_high':conflict_min>=.95,
 'composite_stress_high':composite>=.95,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
 'host_selected_easy_subset':False,
 'external_models_used':False,
}
positive=[k for k in checks if k not in ('automatic_canonical_promotion','host_selected_easy_subset','external_models_used')]
negative=('automatic_canonical_promotion','host_selected_easy_subset','external_models_used')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_COGNITIVE_CONSOLIDATION_STRESS_ADMISSION_V1' if passed else 'WITHHOLD_G2_COGNITIVE_CONSOLIDATION_STRESS_ADMISSION_V1'

experience={
 'schema':'yado.g2.cognitive_consolidation_stress.experience.v1',
 'status':'PASS' if passed else 'WITHHOLD',
 'parent_cognitive_gene_id':parent.get('cognitive_gene_id'),
 'logic':lm,'thinking':tm,'intelligence':im,
 'composite_stress':composite,'clean_min':clean_min,'perturb_min':perturb_min,
 'unknown_min':unknown_min,'conflict_min':conflict_min,
 'canonical_mutation':False,
 'semantic_boundary':'ADVERSARIAL STRUCTURAL STRESS OF THE SHADOW COGNITIVE LAYER. CLEAN AND PERTURBED CASES ARE GENERATED FROM LEARNED PROGRAM STRUCTURE; CONFLICT CASES ARE COMPATIBLE UNIONS OF DIFFERENT LEARNED DECISION ROUTES AND MUST FAIL CLOSED. THIS DOES NOT PROMOTE CANONICAL STATE.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True)
EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.cognitive_consolidation_stress_admission.v1','status':status,'task':task,
 'parent_cognitive_gene_id':parent.get('cognitive_gene_id'),
 'logic_stress':lm,'thinking_stress':tm,'intelligence_stress':im,
 'composite_stress':composite,'clean_min':clean_min,'perturb_min':perturb_min,
 'unknown_min':unknown_min,'conflict_min':conflict_min,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'admission_state':'SHADOW_ADMISSION_READY' if passed else 'WITHHOLD_CONFLICT_ARBITRATION_DEFICIT',
 'next_required_capability':'G2_COGNITIVE_LAYER_CANONICAL_ADMISSION_V1' if passed else 'G2_COGNITIVE_CONFLICT_ARBITRATION_REPAIR_V1',
 'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'logic':lm['score'],'thinking':tm['score'],'intelligence':im['score'],
 'clean_min':clean_min,'perturb_min':perturb_min,'unknown_min':unknown_min,
 'conflict_min':conflict_min,'composite_stress':composite,
 'admission_state':report['admission_state'],'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed: raise SystemExit(2)
