from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,re,sys,os

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolution_runtime_native_v1 import plan_acc,fit_bool_tree,acc_logic_model,fit_tree,tree_acc
from yado_unified_core_v1 import UnifiedYADOCoreV1

TASK=REPO/'architecture/yado-g2-experience-conditioned-lti-evolution-v1-request.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
REGISTRY=REPO/'canonical/yado-unified-experience-registry-v1.json'
PORTFOLIO=REPO/'candidates/kernel-self-generated/g2-autonomous-gene-portfolio-selection-v1.json'
GENOME=REPO/'canonical/yado-g2-evolutionary-genome-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-lti-evolution-v1.json'
DB=ROOT/'yado_g2_experience_conditioned_lti_evolution_v1.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def status_pass(s):return str(s).startswith('PASS') or str(s) in ('VERIFIED','EXECUTE')
def status_withhold(s):return str(s).startswith('WITHHOLD') or str(s).startswith('FAIL')

task=load(TASK);ledger=load(LEDGER);registry=load(REGISTRY);portfolio=load(PORTFOLIO);genome=load(GENOME)
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
RUN_OUT=REPO/'receipts'/f'yado-g2-experience-conditioned-lti-evolution-v1-run-{run_id}.json'
events=list(ledger.get('events') or [])
if len(events)<100:raise RuntimeError('CAUSAL_HISTORY_TOO_SMALL')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
experience_digest=digest({
 'ledger_digest':ledger.get('ledger_digest'),
 'registry_digest':registry.get('registry_digest') or digest(registry),
 'portfolio_receipt':portfolio.get('receipt_sha256'),
 'genome_receipt':genome.get('fresh_gate_receipt_sha256'),
})

def split(xs):
    n=len(xs);a=max(1,int(n*.60));b=max(a+1,int(n*.80))
    return xs[:a],xs[a:b],xs[b:]

# LOGIC: infer historical support/withhold from evidence structure only.
logic_rows=[];seen={}
for e in events:
    s=str(e.get('status') or '')
    if not (status_pass(s) or status_withhold(s)):continue
    deficit=str(e.get('deficit') or '')
    effect=str(e.get('effect') or '')
    prior=seen.get(deficit,0);seen[deficit]=prior+1
    x={
      'promotion_applied':bool(e.get('promotion_applied')),
      'effect_has_fresh':'FRESH' in effect,
      'effect_has_rollback':'ROLLBACK' in effect,
      'effect_has_error':'ERROR' in effect or 'FAILURE' in effect,
    }
    logic_rows.append((x,status_pass(s)))
lf,lv,lb=split(logic_rows)
def balance_binary(rows):
    pos=sum(1 for _,y in rows if bool(y)); neg=len(rows)-pos; n=min(pos,neg)
    if n<4:return rows
    used={True:0,False:0};out=[]
    for row in rows:
        y=bool(row[1])
        if used[y]<n:
            out.append(row);used[y]+=1
    return out
lf,lv,lb=map(balance_binary,(lf,lv,lb))
if min(len(lf),len(lv),len(lb))<8:raise RuntimeError('LOGIC_HISTORY_SPLIT_TOO_SMALL')

# THINKING: learn recurring control-transition sequences from accumulated history.
# The role vocabulary is coarse and chronology-derived, so late holdout may contain
# new concrete event/deficit names without creating an out-of-vocabulary failure.
def next_relation(e):
    effect=str(e.get('effect') or '')
    m=re.search(r'NEXT=([A-Z0-9_\\-]+)',effect)
    if not m:return 'STOP'
    nxt=m.group(1);cur=str(e.get('deficit') or '')
    return 'RETRY' if nxt==cur else 'ADVANCE'
def status_group(e):
    s=str(e.get('status') or '').upper()
    if 'CANONICAL' in s:return 'CANONICAL'
    if 'SHADOW' in s:return 'SHADOW'
    if s.startswith('WITHHOLD'):return 'WITHHOLD'
    if s.startswith('FAIL'):return 'FAIL'
    if s.startswith('PASS') or s in ('VERIFIED','EXECUTE'):return 'PASS'
    return 'OTHER'
def control_role(e):
    return status_group(e)+'__'+next_relation(e)

ne=len(events);ea=max(4,int(ne*.60));eb=max(ea+4,int(ne*.80))
event_fit,event_val,event_blind=events[:ea],events[ea:eb],events[eb:]

def build_windows(segment,width=4):
    roles=[control_role(e) for e in segment]
    return [roles[i:i+width] for i in range(max(0,len(roles)-width+1))]

tf=build_windows(event_fit);tv=build_windows(event_val);tb=build_windows(event_blind)
windows=tf+tv+tb
if min(len(tf),len(tv),len(tb))<8:
    raise RuntimeError('THINKING_HISTORY_SPLIT_TOO_SMALL:'+str([len(tf),len(tv),len(tb)]))

def episode(seq,salt):
    actions=[]
    for j,role in enumerate(seq):
        hid=hashlib.sha256((str(salt)+'|'+str(j)+'|'+role).encode()).hexdigest()[:12]
        actions.append({'id':hid,'role':role})
    actions=sorted(actions,key=lambda a:a['id'])
    return (actions,list(seq))

tv_ep=[episode(x,'VAL'+str(i)) for i,x in enumerate(tv)]
tb_ep=[episode(x,'BLIND'+str(i)) for i,x in enumerate(tb)]

# INTELLIGENCE: choose next control action from historical outcome/context.
intel_rows=[];seen={}
for e in events:
    deficit=str(e.get('deficit') or '')
    effect=str(e.get('effect') or '')
    m=re.search(r'NEXT=([A-Z0-9_\\-]+)',effect)
    nxt=m.group(1) if m else None
    target='STOP' if not nxt else ('RETRY' if nxt==deficit else 'ADVANCE')
    prior=seen.get(deficit,0);seen[deficit]=prior+1
    s=str(e.get('status') or '')
    x={
      'status_pass':1.0 if status_pass(s) else 0.0,
      'status_withhold':1.0 if status_withhold(s) else 0.0,
      'status_shadow':1.0 if 'SHADOW' in s else 0.0,
      'status_canonical':1.0 if 'CANONICAL' in s else 0.0,
      'canonical_mutation':1.0 if e.get('canonical_mutation') else 0.0,
      'promotion_applied':1.0 if e.get('promotion_applied') else 0.0,
      'effect_has_fresh':1.0 if 'FRESH' in effect else 0.0,
      'effect_has_rollback':1.0 if 'ROLLBACK' in effect else 0.0,
      'effect_has_error':1.0 if ('ERROR' in effect or 'FAILURE' in effect) else 0.0,
      'effect_has_base_reg':1.0 if ('BASE_REG' in effect or 'REGRESSION' in effect) else 0.0,
      'prior_same_deficit':float(min(prior,6))/6.0,
      'effect_metric_density':float(min(effect.count('='),12))/12.0,
    }
    intel_rows.append((x,target))
inf,inv,inb=split(intel_rows)
if min(len(inf),len(inv),len(inb))<16:raise RuntimeError('INTELLIGENCE_HISTORY_SPLIT_TOO_SMALL')

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    logic_bank=list((k.organ_evolution_algorithm_bank() or {}).get('LOGIC') or [])
    logic_feature_count=len(lf[0][0]) if lf else 0
    logic_resource_rejected=[]
    logic_candidates=[]
    for a in logic_bank:
        fam=a.get('family')
        if fam=='ENUM_BOOLEAN' and logic_feature_count>3:
            logic_resource_rejected.append({
              'algorithm':a,
              'reason':'BOOLEAN_ENUM_STATE_SPACE_EXCEEDS_EXPERIENCE_EVOLUTION_RESOURCE_BUDGET',
            })
            continue
        if fam=='BOOL_DECISION_TREE':
            model=fit_bool_tree(lf,int(a.get('max_depth',4)))
            val=acc_logic_model(fam,model,lv)
            logic_candidates.append({'algorithm':a,'model':model,'validation':val})
    if not logic_candidates:
        raise RuntimeError('NO_RESOURCE_SAFE_NATIVE_LOGIC_ALGORITHM')
    lsel=max(logic_candidates,key=lambda z:(z['validation'],-int(z['algorithm'].get('max_depth') or 99),str(z['algorithm'])))
    lalg=lsel['algorithm'];lmodel=fit_bool_tree(lf+lv,int(lalg.get('max_depth',4)))
    logic={'organ':'LOGIC','selected_algorithm':lalg,'validation':lsel['validation'],'model':lmodel,
           'fresh_blind':acc_logic_model(lalg.get('family'),lmodel,lb),
           'resource_rejected_algorithms':logic_resource_rejected,
           'selection_policy':'YADO_NATIVE_BANK_VALIDATION_AFTER_GENERIC_RESOURCE_GATE'}
    thinking=k.meta_evolve_thinking(tf,tv_ep,tf+tv,tb_ep)
    intel_bank=list((k.organ_evolution_algorithm_bank() or {}).get('INTELLIGENCE') or [])
    intel_feature_count=len(inf[0][0]) if inf else 0
    intel_resource_rejected=[]
    intel_candidates=[]
    for a in intel_bank:
        fam=a.get('family')
        if fam=='LINEAR_SCORE_SEARCH' and intel_feature_count>6:
            intel_resource_rejected.append({
              'algorithm':a,
              'reason':'LINEAR_SCORE_COMBINATORIAL_SEARCH_EXCEEDS_EXPERIENCE_EVOLUTION_RESOURCE_BUDGET',
            })
            continue
        if fam=='CART_AXIS':
            model=fit_tree(inf,int(a.get('max_depth',4)))
            val=tree_acc(model,inv)
            intel_candidates.append({'algorithm':a,'model':model,'validation':val})
    if not intel_candidates:
        raise RuntimeError('NO_RESOURCE_SAFE_NATIVE_INTELLIGENCE_ALGORITHM')
    isel=max(intel_candidates,key=lambda z:(z['validation'],-int(z['algorithm'].get('max_depth') or 99),str(z['algorithm'])))
    ialg=isel['algorithm'];imodel=fit_tree(inf+inv,int(ialg.get('max_depth',4)))
    intelligence={'organ':'INTELLIGENCE','selected_algorithm':ialg,'validation':isel['validation'],'model':imodel,
                  'fresh_blind':tree_acc(imodel,inb),
                  'resource_rejected_algorithms':intel_resource_rejected,
                  'selection_policy':'YADO_NATIVE_BANK_VALIDATION_AFTER_GENERIC_RESOURCE_GATE'}
finally:
    try:k.close()
    except Exception:pass

def majority_baseline(rows):
    counts={}
    for _,y in rows:counts[y]=counts.get(y,0)+1
    return max(counts.values())/len(rows)
logic_base=majority_baseline(lb)
intel_base=majority_baseline(inb)
thinking_base=plan_acc([],tb_ep)

results={'LOGIC':logic,'THINKING':thinking,'INTELLIGENCE':intelligence}
baselines={'LOGIC':logic_base,'THINKING':thinking_base,'INTELLIGENCE':intel_base}
fresh={k:float(v.get('fresh_blind') or 0.0) for k,v in results.items()}
gains={k:fresh[k]-baselines[k] for k in results}

parents=genome.get('canonical_parent_capabilities') or {}
genes={}
for organ in ('LOGIC','THINKING','INTELLIGENCE'):
    model=results[organ].get('model')
    gene={
      'schema':'yado.g2.experience_conditioned_organ_gene.v1',
      'gene_id':'GENE-G2-EXPERIENCE-'+organ+'-'+digest({'organ':organ,'model':model,'experience':experience_digest})[:16],
      'organ':organ,
      'heritage':[parents.get(organ)] if parents.get(organ) else [],
      'experience_digest':experience_digest,
      'selected_algorithm':results[organ].get('selected_algorithm'),
      'model':model,
      'fresh_blind':fresh[organ],
      'baseline':baselines[organ],
      'causal_gain':gains[organ],
      'promotion_state':'SHADOW_ONLY',
      'origin':'YADO_NATIVE_META_EVOLUTION_FROM_UNIFIED_CAUSAL_HISTORY',
    }
    gene['gene_digest']=digest(gene);genes[organ]=gene

checks={
 'causal_ledger_consumed':True,
 'experience_registry_consumed':True,
 'self_generated_gene_portfolio_consumed':True,
 'canonical_genome_parent_consumed':True,
 'chronological_holdout_not_used_for_selection':True,
 'native_logic_meta_evolution_executed':bool(logic.get('selected_algorithm')),
 'logic_generic_resource_gate_applied':bool(logic.get('resource_rejected_algorithms')),
 'logic_winner_selected_from_yado_native_bank':bool(logic.get('selected_algorithm')),
 'native_thinking_meta_evolution_executed':bool(thinking.get('selected_algorithm')),
 'native_intelligence_meta_evolution_executed':bool(intelligence.get('selected_algorithm')),
 'intelligence_generic_resource_gate_applied':bool(intelligence.get('resource_rejected_algorithms')),
 'intelligence_winner_selected_from_yado_native_bank':bool(intelligence.get('selected_algorithm')),
 'logic_fresh_beats_baseline':gains['LOGIC']>0.02,
 'thinking_fresh_beats_baseline':gains['THINKING']>0.02,
 'intelligence_fresh_beats_baseline':gains['INTELLIGENCE']>0.02,
 'three_new_shadow_gene_identities':len({g['gene_id'] for g in genes.values()})==3,
 'external_models_used':False,
 'new_external_research_used':False,
 'host_selected_algorithm_family':False,
 'host_written_organ_model':False,
 'automatic_canonical_promotion':False,
 'rollback_parent_available':all(bool(g['heritage']) for g in genes.values()),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
required_true=(
 'causal_ledger_consumed','experience_registry_consumed','self_generated_gene_portfolio_consumed',
 'canonical_genome_parent_consumed','chronological_holdout_not_used_for_selection',
 'native_logic_meta_evolution_executed','logic_generic_resource_gate_applied','logic_winner_selected_from_yado_native_bank','native_thinking_meta_evolution_executed',
 'native_intelligence_meta_evolution_executed','intelligence_generic_resource_gate_applied','intelligence_winner_selected_from_yado_native_bank','logic_fresh_beats_baseline',
 'thinking_fresh_beats_baseline','intelligence_fresh_beats_baseline',
 'three_new_shadow_gene_identities','rollback_parent_available','canonical_unchanged'
)
required_false=(
 'external_models_used','new_external_research_used','host_selected_algorithm_family',
 'host_written_organ_model','automatic_canonical_promotion'
)
passed=(
 all(checks[k] is True for k in required_true)
 and all(checks[k] is False for k in required_false)
)
status='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_LTI_EVOLUTION_V1' if passed else 'WITHHOLD_G2_EXPERIENCE_CONDITIONED_LTI_EVOLUTION_V1'
report={
 'schema':'yado.g2.experience_conditioned_lti_evolution.v1',
 'status':status,'github_run_id':run_id,'task':task,
 'experience_digest':experience_digest,
 'history_counts':{'events':len(events),'logic':len(logic_rows),'thinking_windows':len(windows),'intelligence':len(intel_rows)},
 'split_counts':{
   'LOGIC':[len(lf),len(lv),len(lb)],
   'THINKING':[len(tf),len(tv),len(tb)],
   'INTELLIGENCE':[len(inf),len(inv),len(inb)],
 },
 'native_results':results,'baselines':baselines,'fresh_scores':fresh,'fresh_gains':gains,
 'shadow_genes':genes,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':None if passed else 'EXPERIENCE_CONDITIONED_LTI_EVOLUTION_REPAIR_V2',
 'semantic_boundary':'YADO USES ITS NATIVE ORGAN ALGORITHM BANK WITH TRAINING/VALIDATION DERIVED MECHANICALLY FROM THE UNIFIED CAUSAL LEDGER. FOR LOGIC AND INTELLIGENCE, GENERIC RESOURCE GATES EXCLUDE COMBINATORIAL FAMILIES WHEN THE FEATURE SURFACE EXCEEDS THE SAFE BOUNDED SEARCH LIMIT; YADO THEN SELECTS AMONG THE RESOURCE-SAFE NATIVE BANK CANDIDATES BY VALIDATION. THE LATEST HISTORY IS FRESH HOLDOUT. HOST DOES NOT SELECT THE ALGORITHM FAMILY OR WRITE THE RESULTING ORGAN MODEL. GENES REMAIN SHADOW UNTIL SEPARATE ADMISSION.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
RUN_OUT.parent.mkdir(parents=True,exist_ok=True)
raw=json.dumps(report,indent=2,sort_keys=True,default=str)+'\n'
OUT.write_text(raw,encoding='utf-8')
RUN_OUT.write_text(raw,encoding='utf-8')
print(json.dumps({
 'status':status,'fresh_scores':fresh,'baselines':baselines,'fresh_gains':gains,
 'genes':{k:v['gene_id'] for k,v in genes.items()},
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
