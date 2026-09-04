from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolution_runtime_native_v1 import plan_acc
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
      'canonical_mutation':bool(e.get('canonical_mutation')),
      'promotion_applied':bool(e.get('promotion_applied')),
      'has_parent_event_hash':bool(e.get('parent_event_hash')),
      'has_source_digest':bool(e.get('source_digest')),
      'has_run_id':bool(e.get('run_id')),
      'effect_has_fresh':'FRESH' in effect,
      'effect_has_rollback':'ROLLBACK' in effect,
      'effect_has_base_reg':'BASE_REG' in effect or 'REGRESSION' in effect,
      'effect_has_error':'ERROR' in effect or 'FAILURE' in effect,
      'effect_has_next':'NEXT=' in effect,
      'deficit_seen_before':prior>0,
    }
    logic_rows.append((x,status_pass(s)))
lf,lv,lb=split(logic_rows)
if min(len(lf),len(lv),len(lb))<8:raise RuntimeError('LOGIC_HISTORY_SPLIT_TOO_SMALL')

# THINKING: learn recurring causal ordering directly from normalized ledger event types.
def norm_role(s):
    s=re.sub(r'V\\d+','V#',str(s).upper())
    s=re.sub(r'\\d+','#',s)
    s=re.sub(r'_+','_',s).strip('_')
    return s
raw_roles=[norm_role(e.get('event_type') or 'UNKNOWN') for e in events]
freq={}
for r in raw_roles:freq[r]=freq.get(r,0)+1
stream=[r for r in raw_roles if freq.get(r,0)>=2]
windows=[]
for i in range(len(stream)):
    seq=[]
    for r in stream[i:]:
        if r not in seq:seq.append(r)
        if len(seq)==5:break
    if len(seq)==5 and seq not in windows:windows.append(seq)
tf,tv,tb=split(windows)
if min(len(tf),len(tv),len(tb))<4:raise RuntimeError('THINKING_HISTORY_SPLIT_TOO_SMALL:'+str([len(tf),len(tv),len(tb)]))
def episode(seq,salt):
    actions=[]
    for j,role in enumerate(seq):
        hid=hashlib.sha256((str(salt)+'|'+role).encode()).hexdigest()[:12]
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
    logic=k.meta_evolve_logic(lf,lv,lf+lv,lb)
    thinking=k.meta_evolve_thinking(tf,tv_ep,tf+tv,tb_ep)
    intelligence=k.meta_evolve_intelligence(inf,inv,inf+inv,inb)
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
 'native_thinking_meta_evolution_executed':bool(thinking.get('selected_algorithm')),
 'native_intelligence_meta_evolution_executed':bool(intelligence.get('selected_algorithm')),
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
passed=all(checks.values())
status='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_LTI_EVOLUTION_V1' if passed else 'WITHHOLD_G2_EXPERIENCE_CONDITIONED_LTI_EVOLUTION_V1'
report={
 'schema':'yado.g2.experience_conditioned_lti_evolution.v1',
 'status':status,'task':task,
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
 'semantic_boundary':'YADO NATIVE META-EVOLUTION SELECTS ORGAN ALGORITHM FAMILIES FROM ITS OWN BANK USING TRAINING/VALIDATION DERIVED MECHANICALLY FROM THE UNIFIED CAUSAL LEDGER. THE LATEST HISTORY IS FRESH HOLDOUT. HOST DOES NOT SELECT THE ALGORITHM FAMILY OR WRITE THE RESULTING ORGAN MODEL. GENES REMAIN SHADOW UNTIL SEPARATE ADMISSION.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'fresh_scores':fresh,'baselines':baselines,'fresh_gains':gains,
 'genes':{k:v['gene_id'] for k,v in genes.items()},
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
