from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v2_1 import RulePredicate,RuleSpec,RuleProgram,BoundedRuleSandbox

TASK=REPO/'architecture/yado-g2-cognitive-conflict-arbitration-repair-v2-request.json'
PARENT=REPO/'candidates/kernel-self-generated/g2-cognitive-conflict-arbitration-repair-v1.json'
STRESS=REPO/'candidates/kernel-self-generated/g2-cognitive-consolidation-stress-admission-v2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-cognitive-conflict-arbitration-repair-v2.json'
EXP=REPO/'experience/yado-cognitive-conflict-arbitration-repair-v2.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

def rp(raw):
    rules=[]
    for r in raw['rules']:
        rules.append(RuleSpec([RulePredicate(**p) for p in r['predicates']],r['output'],int(r['support']),float(r['confidence'])))
    return RuleProgram(raw['program_id'],raw['target_capability'],raw['target_organ'],rules,raw['default_output'],raw['source_digest'],int(raw.get('training_count',0)),raw.get('status','SHADOW'))

task=load(TASK);parent=load(PARENT);stress=load(STRESS)
if parent.get('status')!='PASS_SHADOW_G2_COGNITIVE_CONFLICT_ARBITRATION_REPAIR_V1':
    raise RuntimeError('ARBITER_V1_PASS_REQUIRED')
if stress.get('status')!='WITHHOLD_G2_COGNITIVE_CONSOLIDATION_STRESS_ADMISSION_V2':
    raise RuntimeError('STRESS_V2_WITHHOLD_REQUIRED')
if stress.get('next_required_capability')!='G2_COGNITIVE_CONFLICT_ARBITRATION_REPAIR_V2':
    raise RuntimeError('STRESS_V2_FRONTIER_MISMATCH')
if float(stress.get('composite_exhaustive') or 0)!=1.0:
    raise RuntimeError('EXHAUSTIVE_BEHAVIOR_NOT_EXACT')
for k in ('logic_exhaustive','thinking_exhaustive','intelligence_exhaustive'):
    if float((stress.get(k) or {}).get('score') or 0)!=1.0:
        raise RuntimeError('ORGAN_EXHAUSTIVE_NOT_EXACT:'+k)

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
arbiter=rp(parent['guard_gene']['program'])

# Balanced causal blind set. Equal PASS_THROUGH and WITHHOLD labels prevent
# majority fail-closed states from hiding the contribution of the arbiter.
# Values and organ tokens are fresh and were not used in V1 training.
cases=[]
organs=['LOGIC_BLIND','THINKING_BLIND','INTELLIGENCE_BLIND','WORKSPACE_BLIND','NOVEL_ORGAN_A','NOVEL_ORGAN_B']
for i,organ in enumerate(organs):
    # 4 PASS_THROUGH cases per organ
    for j in range(4):
        cases.append({'input':{
            'route_cardinality':'ONE','state_known':True,'organ':organ,
            'blind_nonce':'P'+str(i)+'_'+str(j),'novel_scalar':100+i*10+j
        },'expected':'PASS_THROUGH'})
    # 2 zero-route + 1 multi-route + 1 unknown = 4 WITHHOLD cases per organ
    cases.append({'input':{'route_cardinality':'ZERO','state_known':True,'organ':organ,'blind_nonce':'Z'+str(i)},'expected':'WITHHOLD'})
    cases.append({'input':{'route_cardinality':'ZERO','state_known':False,'organ':organ,'blind_nonce':'U'+str(i)},'expected':'WITHHOLD'})
    cases.append({'input':{'route_cardinality':'MULTI','state_known':True,'organ':organ,'blind_nonce':'M'+str(i)},'expected':'WITHHOLD'})
    cases.append({'input':{'route_cardinality':'MULTI','state_known':False,'organ':organ,'blind_nonce':'X'+str(i)},'expected':'WITHHOLD'})

def acc(ablated=False):
    return sum(BoundedRuleSandbox.execute(arbiter,c['input'],ablated=ablated)==c['expected'] for c in cases)/len(cases)

fresh=acc(False);ablation=acc(True);restore=acc(False)
pass_rows=[c for c in cases if c['expected']=='PASS_THROUGH']
withhold_rows=[c for c in cases if c['expected']=='WITHHOLD']
balance_exact=len(pass_rows)==len(withhold_rows)
class_counts={'PASS_THROUGH':len(pass_rows),'WITHHOLD':len(withhold_rows)}

# Direct novel perturbation: field order/noise should not matter.
perturbed=[]
for i,c in enumerate(cases):
    x=dict(reversed(list(c['input'].items())))
    x['never_seen_boolean']=bool(i%2);x['never_seen_text']='ARB_'+str(i)
    got=BoundedRuleSandbox.execute(arbiter,x)
    perturbed.append({'expected':c['expected'],'got':got,'pass':got==c['expected']})
perturb_score=sum(x['pass'] for x in perturbed)/len(perturbed)

checks={
 'arbiter_v1_pass_consumed':True,
 'stress_v2_withhold_consumed':True,
 'exhaustive_behavior_336_preserved':int(stress.get('case_count') or 0)==336 and float(stress.get('composite_exhaustive') or 0)==1.0,
 'logic_336_family_exact':float(stress['logic_exhaustive']['score'])==1.0,
 'thinking_336_family_exact':float(stress['thinking_exhaustive']['score'])==1.0,
 'intelligence_336_family_exact':float(stress['intelligence_exhaustive']['score'])==1.0,
 'balanced_probe_exact':balance_exact,
 'balanced_probe_material':len(cases)>=40,
 'balanced_fresh_exact':fresh==1.0,
 'balanced_ablation_material':fresh-ablation>=.25,
 'balanced_restore_exact':restore==fresh,
 'novel_perturbation_exact':perturb_score==1.0,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'mechanism_changed_to_chase_metric':False,
 'automatic_canonical_promotion':False,
 'external_models_used':False,
}
positive=[k for k in checks if k not in ('mechanism_changed_to_chase_metric','automatic_canonical_promotion','external_models_used')]
negative=('mechanism_changed_to_chase_metric','automatic_canonical_promotion','external_models_used')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_EVIDENCE_REPAIR_G2_COGNITIVE_CONFLICT_ARBITRATION_V2' if passed else 'WITHHOLD_G2_COGNITIVE_CONFLICT_ARBITRATION_REPAIR_V2'

evidence={
 'schema':'yado.g2.cognitive_conflict_arbitration_evidence_repair.v2',
 'status':'PASS' if passed else 'WITHHOLD',
 'parent_guard_gene_id':parent.get('guard_gene_id'),
 'parent_cognitive_gene_id':parent.get('cognitive_gene_id'),
 'stress_v2_receipt':stress.get('receipt_sha256'),
 'behavioral_exhaustive':{
   'case_count':stress.get('case_count'),'composite':stress.get('composite_exhaustive'),
   'logic':stress['logic_exhaustive']['score'],'thinking':stress['thinking_exhaustive']['score'],
   'intelligence':stress['intelligence_exhaustive']['score']
 },
 'balanced_causal_probe':{
   'case_count':len(cases),'class_counts':class_counts,'fresh':fresh,'ablation':ablation,
   'ablation_drop':fresh-ablation,'restore':restore,'perturbation_score':perturb_score
 },
 'mechanism_changed':False,'canonical_mutation':False,
 'semantic_boundary':'V2 REPAIRS THE CAUSAL EVALUATION CONTRACT, NOT THE ALREADY-EXACT ARBITER. EXHAUSTIVE 336/336 BEHAVIOR IS RETAINED; A BALANCED FRESH BLIND PROBE MEASURES CAUSAL CONTRIBUTION WITHOUT MAJORITY WITHHOLD MASKING.'
}
evidence['experience_digest']=digest(evidence)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.cognitive_conflict_arbitration_repair.v2','status':status,'task':task,
 'guard_gene_id':parent.get('guard_gene_id'),'cognitive_gene_id':parent.get('cognitive_gene_id'),
 'exhaustive_case_count':stress.get('case_count'),'exhaustive_composite':stress.get('composite_exhaustive'),
 'balanced_case_count':len(cases),'class_counts':class_counts,
 'balanced_fresh':fresh,'balanced_ablation':ablation,'balanced_ablation_drop':fresh-ablation,
 'balanced_restore':restore,'perturbation_score':perturb_score,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'admission_state':'SHADOW_ADMISSION_READY' if passed else 'WITHHOLD_CAUSAL_EVIDENCE',
 'next_required_capability':'G2_COGNITIVE_LAYER_CANONICAL_ADMISSION_V1' if passed else 'G2_COGNITIVE_CONFLICT_ARBITRATION_REPAIR_V3',
 'semantic_boundary':evidence['semantic_boundary']
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'exhaustive':report['exhaustive_composite'],'balanced_fresh':fresh,
 'balanced_ablation':ablation,'balanced_ablation_drop':fresh-ablation,'perturbation':perturb_score,
 'admission_state':report['admission_state'],'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
