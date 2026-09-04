from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys
from itertools import product

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v2_1 import RulePredicate,RuleSpec,RuleProgram,BoundedRuleSandbox

TASK=REPO/'architecture/yado-g2-cognitive-consolidation-stress-admission-v2-request.json'
BASE=REPO/'candidates/kernel-self-generated/g2-coding-experience-cognitive-consolidation-v2.json'
PARENT=REPO/'candidates/kernel-self-generated/g2-cognitive-conflict-arbitration-repair-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-cognitive-consolidation-stress-admission-v2.json'
EXP=REPO/'experience/yado-cognitive-consolidation-stress-v2.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

def rp(raw):
    rules=[]
    for r in raw['rules']:
        rules.append(RuleSpec([RulePredicate(**p) for p in r['predicates']],r['output'],int(r['support']),float(r['confidence'])))
    return RuleProgram(raw['program_id'],raw['target_capability'],raw['target_organ'],rules,raw['default_output'],raw['source_digest'],int(raw.get('training_count',0)),raw.get('status','SHADOW'))

task=load(TASK);base=load(BASE);parent=load(PARENT)
if parent.get('status')!='PASS_SHADOW_G2_COGNITIVE_CONFLICT_ARBITRATION_REPAIR_V1':
    raise RuntimeError('CONFLICT_REPAIR_PASS_REQUIRED')
if parent.get('next_required_capability')!='G2_COGNITIVE_CONSOLIDATION_STRESS_AND_ADMISSION_V2':
    raise RuntimeError('CONFLICT_REPAIR_FRONTIER_MISMATCH')
if base.get('status')!='PASS_SHADOW_G2_CODING_EXPERIENCE_COGNITIVE_CONSOLIDATION_V2':
    raise RuntimeError('BASE_COGNITIVE_V2_PASS_REQUIRED')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
logic=rp(base['organ_genes']['LOGIC']['program'])
thinking=rp(base['organ_genes']['THINKING']['program'])
intel=base['organ_genes']['INTELLIGENCE']['model']
arbiter=rp(parent['guard_gene']['program'])

def rule_outputs(program,x):
    outs=[]
    for r in program.rules:
        if all(BoundedRuleSandbox._match(p,x) for p in r.predicates):
            if str(r.output) not in outs:outs.append(str(r.output))
    return outs

def router_outputs(model,x):
    outs=[]
    for out in model.get('outputs') or []:
        if out==model.get('fallback_output'):continue
        for r in model.get('triggers',{}).get(out,[]) or []:
            if all(a['field'] in x and x[a['field']]==a['value'] for a in r['atoms']):
                outs.append(str(out));break
    return sorted(set(outs))

def card(outs):
    n=len(set(outs));return 'ZERO' if n==0 else ('ONE' if n==1 else 'MULTI')

def guard(organ,outs,x,ablated=False):
    return BoundedRuleSandbox.execute(arbiter,{
      'route_cardinality':card(outs),'state_known':bool(x.get('state_known',True)),'organ':organ
    },ablated=ablated)

def final_decision(organ,outs,x,ablated=False):
    g=guard(organ,outs,x,ablated=ablated)
    if g=='PASS_THROUGH' and bool(x.get('state_known',True)) and len(set(outs))==1:return outs[0]
    return 'WITHHOLD'

def expected_decision(outs,x):
    # Generic admission invariant, independent of task-specific action semantics.
    if not bool(x.get('state_known',True)):return 'WITHHOLD'
    return outs[0] if len(set(outs))==1 else 'WITHHOLD'

def bool_fields_rule(program):
    vals={}
    for r in program.rules:
        for p in r.predicates:
            if isinstance(p.value,bool):vals[p.field]=True
    vals['state_known']=True
    return sorted(vals)

def bool_fields_router(model):
    vals={}
    for out in model.get('outputs') or []:
        for r in model.get('triggers',{}).get(out,[]) or []:
            for a in r['atoms']:
                if isinstance(a.get('value'),bool):vals[a['field']]=True
    vals['state_known']=True
    return sorted(vals)

def exhaustive(organ,fields,matcher):
    cases=[]
    for bits in product([False,True],repeat=len(fields)):
        x=dict(zip(fields,bits))
        outs=matcher(x);exp=expected_decision(outs,x)
        got=final_decision(organ,outs,x,False);abl=final_decision(organ,outs,x,True)
        cases.append({'input':x,'matched_outputs':outs,'expected':exp,'got':got,'ablated':abl,'pass':got==exp,'ablation_pass':abl==exp})
        # New irrelevant perturbation never seen by the repair learner.
        y=dict(x);y['admission_noise']='Q'+hashlib.sha256(canon(x).encode()).hexdigest()[:8];y['admission_int']=len(outs)
        outs2=matcher(y);exp2=expected_decision(outs2,y);got2=final_decision(organ,outs2,y,False);abl2=final_decision(organ,outs2,y,True)
        cases.append({'input':y,'matched_outputs':outs2,'expected':exp2,'got':got2,'ablated':abl2,'pass':got2==exp2,'ablation_pass':abl2==exp2})
    return cases

logic_cases=exhaustive('LOGIC',bool_fields_rule(logic),lambda x:rule_outputs(logic,x))
thinking_cases=exhaustive('THINKING',bool_fields_rule(thinking),lambda x:rule_outputs(thinking,x))
intel_cases=exhaustive('INTELLIGENCE',bool_fields_router(intel),lambda x:router_outputs(intel,x))

def metric(cases):
    score=sum(c['pass'] for c in cases)/len(cases)
    abl=sum(c['ablation_pass'] for c in cases)/len(cases)
    cats={'ZERO':[],'ONE':[],'MULTI':[],'UNKNOWN':[]}
    for c in cases:
        k='UNKNOWN' if not c['input'].get('state_known',True) else card(c['matched_outputs'])
        cats[k].append(c)
    by={k:(sum(z['pass'] for z in xs)/len(xs) if xs else None) for k,xs in cats.items()}
    return {'count':len(cases),'score':score,'ablation':abl,'ablation_drop':score-abl,'by_route_state':by,
            'failures':[c for c in cases if not c['pass']][:20]}

lm=metric(logic_cases);tm=metric(thinking_cases);im=metric(intel_cases)
composite=min(lm['score'],tm['score'],im['score'])
min_ablation_drop=min(lm['ablation_drop'],tm['ablation_drop'],im['ablation_drop'])
case_count=len(logic_cases)+len(thinking_cases)+len(intel_cases)

# Additional direct guard perturbations with unseen organ token verify organ is irrelevant.
guard_direct=[]
for organ in ('LOGIC','THINKING','INTELLIGENCE','NOVEL_ORGAN'):
  for rc in ('ZERO','ONE','MULTI'):
    for known in (False,True):
      x={'route_cardinality':rc,'state_known':known,'organ':organ,'never_seen':'R'}
      expected='PASS_THROUGH' if rc=='ONE' else 'WITHHOLD'
      got=BoundedRuleSandbox.execute(arbiter,x)
      guard_direct.append({'input':x,'expected':expected,'got':got,'pass':got==expected})
guard_direct_score=sum(x['pass'] for x in guard_direct)/len(guard_direct)

checks={
 'repair_v1_consumed':True,
 'exhaustive_boolean_state_space_used':True,
 'exhaustive_case_count_material':case_count>=100,
 'logic_exhaustive_exact':lm['score']==1.0,
 'thinking_exhaustive_exact':tm['score']==1.0,
 'intelligence_exhaustive_exact':im['score']==1.0,
 'composite_exhaustive_exact':composite==1.0,
 'organ_ablation_material':min_ablation_drop>=.25,
 'direct_guard_novel_organ_exact':guard_direct_score==1.0,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'external_models_used':False,'automatic_canonical_promotion':False,'host_selected_easy_subset':False
}
positive=[k for k in checks if k not in ('external_models_used','automatic_canonical_promotion','host_selected_easy_subset')]
passed=all(checks[k] is True for k in positive) and checks['external_models_used'] is False and checks['automatic_canonical_promotion'] is False and checks['host_selected_easy_subset'] is False
status='PASS_SHADOW_G2_COGNITIVE_CONSOLIDATION_STRESS_ADMISSION_V2' if passed else 'WITHHOLD_G2_COGNITIVE_CONSOLIDATION_STRESS_ADMISSION_V2'

experience={
 'schema':'yado.g2.cognitive_consolidation_stress.experience.v2',
 'status':'PASS' if passed else 'WITHHOLD',
 'parent_cognitive_gene_id':parent.get('cognitive_gene_id'),'guard_gene_id':parent.get('guard_gene_id'),
 'case_count':case_count,'logic':lm,'thinking':tm,'intelligence':im,
 'composite':composite,'min_ablation_drop':min_ablation_drop,'guard_direct_score':guard_direct_score,
 'canonical_mutation':False,
 'semantic_boundary':'EXHAUSTIVE BOOLEAN COMBINATION STRESS OVER EVERY BOOLEAN FIELD USED BY THE CURRENT BOUNDED ORGAN ROUTES, WITH AN UNSEEN IRRELEVANT PERTURBATION FOR EVERY STATE. THE EXPECTED DECISION USES ONLY THE GENERIC ARBITRATION INVARIANT: EXACTLY ONE KNOWN ROUTE MAY PASS; ZERO, MULTI OR UNKNOWN FAIL CLOSED. THIS IS A BOUNDED ADMISSION TEST, NOT GENERAL COGNITIVE PROOF.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.cognitive_consolidation_stress_admission.v2','status':status,'task':task,
 'parent_cognitive_gene_id':parent.get('cognitive_gene_id'),'guard_gene_id':parent.get('guard_gene_id'),
 'case_count':case_count,'logic_exhaustive':lm,'thinking_exhaustive':tm,'intelligence_exhaustive':im,
 'composite_exhaustive':composite,'min_ablation_drop':min_ablation_drop,'guard_direct_score':guard_direct_score,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'admission_state':'SHADOW_ADMISSION_READY' if passed else 'WITHHOLD_STRESS_V2',
 'next_required_capability':'G2_COGNITIVE_LAYER_CANONICAL_ADMISSION_V1' if passed else 'G2_COGNITIVE_CONFLICT_ARBITRATION_REPAIR_V2',
 'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'case_count':case_count,'logic':lm['score'],'thinking':tm['score'],'intelligence':im['score'],
 'composite':composite,'min_ablation_drop':min_ablation_drop,'guard_direct_score':guard_direct_score,
 'admission_state':report['admission_state'],'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
