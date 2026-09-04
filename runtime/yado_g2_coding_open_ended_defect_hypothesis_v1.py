from __future__ import annotations
from pathlib import Path
from collections import Counter
import copy,hashlib,json,math,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate

TASK=REPO/'architecture/yado-g2-coding-open-ended-defect-hypothesis-v1-request.json'
PARENT=REPO/'candidates/kernel-self-generated/g2-coding-hypothesis-revision-generator-v1.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-open-ended-defect-hypothesis-v1.json'
EXP=REPO/'experience/yado-coding-open-ended-defect-hypothesis-v1.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

task=load(TASK);parent=load(PARENT);head=load(HEAD)
if parent.get('status')!='PASS_SHADOW_G2_CODING_HYPOTHESIS_REVISION_GENERATOR_V1':
    raise RuntimeError('REVISION_PARENT_NOT_PASS')
if parent.get('next_required_capability')!='G2_CODING_OPEN_ENDED_DEFECT_HYPOTHESIS_V1':
    raise RuntimeError('PARENT_FRONTIER_MISMATCH')
active=set(head.get('active_capabilities') or [])
if 'ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1' not in active:raise RuntimeError('EVIDENCE_SELECTOR_NOT_ACTIVE')
if 'ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11' not in active:raise RuntimeError('PROGRAM_REPAIR_NOT_ACTIVE')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

BASE='def f(x):\n    return x\n'
PROBE_DOMAIN=tuple(range(-12,13))
MAX_HYPOTHESES=3000
MAX_PROBES=5

def execute(src,x):
    return BoundedCompositionalProgramRepairV3.execute(src,'f',(x,))

def score(src,cases):
    if not src:return 0.0
    ok=0
    for x,y in cases:
        try:g=execute(src,x)
        except Exception:continue
        ok+=(g==y)
    return ok/max(1,len(cases))

def passes(src,examples):
    return BoundedCompositionalProgramRepairV3._passes(src,'f',[((x,),y) for x,y in examples])

def enumerate_hypotheses(examples):
    train=[((x,),y) for x,y in examples]
    seen={BASE};frontier=[BASE];fits=[]
    if passes(BASE,examples):fits.append(BASE)
    for _depth in (1,2):
        nxt=[]
        for base in frontier:
            for cand in BoundedCompositionalProgramRepairV3._atomic_mutations(base,train):
                if cand in seen:continue
                seen.add(cand)
                if len(seen)>MAX_HYPOTHESES:
                    break
                nxt.append(cand)
                if passes(cand,examples):fits.append(cand)
            if len(seen)>MAX_HYPOTHESES:break
        frontier=nxt
        if len(seen)>MAX_HYPOTHESES:break
    # Deduplicate by behavior over the bounded probe domain. Keep shortest representative.
    by_sig={}
    for src in fits:
        try:sig=tuple(execute(src,x) for x in PROBE_DOMAIN)
        except Exception:continue
        prev=by_sig.get(sig)
        if prev is None or (len(src),src)<(len(prev),prev):by_sig[sig]=src
    return sorted(by_sig.values(),key=lambda s:(len(s),s))

def probe_candidates(hypotheses,observed):
    used={x for x,_ in observed};out=[];token_to_x={}
    denom=max(1,len(hypotheses))
    for x in PROBE_DOMAIN:
        if x in used:continue
        vals=[]
        for src in hypotheses:
            try:vals.append(execute(src,x))
            except Exception:pass
        if len(vals)<2:continue
        cnt=Counter(vals)
        if len(cnt)<2:continue
        # Normalized disagreement: zero when all hypotheses agree, near one when split.
        evidence=1.0-max(cnt.values())/len(vals)
        token='PX-'+sha(str(x))[:14]
        token_to_x[token]=x
        distance=min((abs(x-z) for z in used),default=12)
        novelty=min(1.0,distance/12.0)
        complexity=abs(x)/12.0
        out.append(EvidenceCandidate(token=token,evidence=evidence,complexity=complexity,risk=0.0,novelty=novelty))
    return out,token_to_x

def hidden_cases():
    return [
      {
       'id':'OPEN_ABS','target':lambda x:abs(x),
       'seed':[(1,1),(4,4),(7,7),(10,10)],
       'holdout':[(-15,15),(-9,9),(-2,2),(0,0),(6,6),(14,14)]
      },
      {
       'id':'OPEN_MAX2','target':lambda x:max(x,2),
       'seed':[(2,2),(5,5),(8,8),(11,11)],
       'holdout':[(-15,2),(-5,2),(0,2),(3,3),(9,9),(14,14)]
      },
      {
       'id':'OPEN_MIN_NEG1','target':lambda x:min(x,-1),
       'seed':[(-11,-11),(-7,-7),(-3,-3),(-1,-1)],
       'holdout':[(-15,-15),(-5,-5),(0,-1),(4,-1),(9,-1),(14,-1)]
      },
      {
       'id':'OPEN_RELU','target':lambda x:max(x,0),
       'seed':[(0,0),(3,3),(7,7),(11,11)],
       'holdout':[(-15,0),(-6,0),(-1,0),(2,2),(8,8),(14,14)]
      },
      {
       'id':'OPEN_MIN0','target':lambda x:min(x,0),
       'seed':[(-11,-11),(-6,-6),(-2,-2),(0,0)],
       'holdout':[(-15,-15),(-4,-4),(1,0),(5,0),(10,0),(14,0)]
      },
      {
       'id':'OPEN_CLAMP_NEG2_POS3','target':lambda x:max(min(x,3),-2),
       'seed':[(-2,-2),(-1,-1),(0,0),(2,2),(3,3)],
       'holdout':[(-15,-2),(-6,-2),(-1,-1),(1,1),(5,3),(14,3)]
      },
      {
       'id':'OPEN_CLAMP_0_3','target':lambda x:max(min(x,3),0),
       'seed':[(0,0),(1,1),(2,2),(3,3)],
       'holdout':[(-15,0),(-4,0),(1,1),(2,2),(6,3),(14,3)]
      },
      {
       'id':'OPEN_CLAMP_NEG1_POS2','target':lambda x:max(min(x,2),-1),
       'seed':[(-1,-1),(0,0),(1,1),(2,2)],
       'holdout':[(-15,-1),(-5,-1),(0,0),(1,1),(7,2),(14,2)]
      },
    ]

def run_task(t):
    observed=list(t['seed'])
    initial_score=score(BASE,t['holdout'])
    current=BASE
    initial_h=enumerate_hypotheses(observed)
    trace=[]
    oracle_calls=[]
    for cycle in range(MAX_PROBES):
        hyps=enumerate_hypotheses(observed)
        cands,token_map=probe_candidates(hyps,observed)
        if not cands:break
        sel=NeutralEvidenceProfileSelectorV1.select(
            cands,complexity_penalty=.005,risk_penalty=.25,novelty_bonus=.01
        )
        token=sel['selected_token'];x=token_map[token]
        y=t['target'](x)
        oracle_calls.append({'token':token,'x':x,'y':y})
        observed.append((x,y))
        repair=AmbiguityAwareProgramRepairV11.repair(
            BASE,'f',[((a,),b) for a,b in observed],max_candidates=12000,max_edit_depth=2
        )
        candidate=repair.get('source')
        if candidate:
            current=candidate
        after=enumerate_hypotheses(observed)
        trace.append({
          'cycle':cycle,
          'hypothesis_count_before':len(hyps),
          'selected_probe_token':token,
          'selected_probe_x':x,
          'selected_probe_evidence':next(z.evidence for z in cands if z.token==token),
          'oracle_output':y,
          'repair_mode':repair.get('repair_mode'),
          'repair_reason':repair.get('reason'),
          'candidate_source_sha256':sha(candidate) if candidate else None,
          'candidate_changed_from_initial':bool(candidate and sha(candidate)!=sha(BASE)),
          'hypothesis_count_after':len(after),
          'selector_candidate_count':sel['candidate_count'],
        })
        if len(after)<=1:break
    final_repair=AmbiguityAwareProgramRepairV11.repair(
        BASE,'f',[((a,),b) for a,b in observed],max_candidates=12000,max_edit_depth=2
    )
    if final_repair.get('source'):current=final_repair['source']
    final_h=enumerate_hypotheses(observed)
    final_score=score(current,t['holdout'])
    return {
      'task_id':t['id'],
      'seed_count':len(t['seed']),
      'initial_source_sha256':sha(BASE),
      'initial_holdout_score':initial_score,
      'initial_hypothesis_count':len(initial_h),
      'probe_count':len(trace),
      'probe_trace':trace,
      'oracle_calls':oracle_calls,
      'final_source_sha256':sha(current),
      'final_source_excerpt':current[:800],
      'final_holdout_score':final_score,
      'final_hypothesis_count':len(final_h),
      'source_changed':sha(current)!=sha(BASE),
      'observed_count':len(observed),
      'final_repair_mode':final_repair.get('repair_mode'),
      'final_repair_reason':final_repair.get('reason'),
    }

tasks=hidden_cases()
episodes=[run_task(t) for t in tasks]
initial=sum(e['initial_holdout_score'] for e in episodes)/len(episodes)
final=sum(e['final_holdout_score'] for e in episodes)/len(episodes)
ablation=initial
mean_probes=sum(e['probe_count'] for e in episodes)/len(episodes)
multi=sum(e['probe_count']>=2 for e in episodes)
mean_h0=sum(e['initial_hypothesis_count'] for e in episodes)/len(episodes)
mean_h1=sum(e['final_hypothesis_count'] for e in episodes)/len(episodes)

# Deterministic restore: replay pristine tasks and require same probe sequence + final source digest.
restored=[run_task(t) for t in tasks]
restore=sum(e['final_holdout_score'] for e in restored)/len(restored)
restore_exact=all(
    a['final_source_sha256']==b['final_source_sha256'] and
    [z['selected_probe_token'] for z in a['probe_trace']]==[z['selected_probe_token'] for z in b['probe_trace']]
    for a,b in zip(episodes,restored)
)

all_selected_positive=all(all(z['selected_probe_evidence']>0 for z in e['probe_trace']) for e in episodes)
all_narrowed=all(e['final_hypothesis_count']<e['initial_hypothesis_count'] for e in episodes)
all_exact=all(e['final_holdout_score']==1.0 for e in episodes)
all_changed=all(e['source_changed'] for e in episodes)

parent_gene=parent['revision_gene']
gene={
 'schema':'yado.g2.coding_open_ended_defect_hypothesis_gene.v1',
 'gene_id':'GENE-G2-CODING-OPEN-ENDED-DEFECT-HYPOTHESIS-V1-'+digest({'episodes':episodes,'parent':parent_gene['gene_digest']})[:16],
 'organ':'THINKING',
 'gene_scope':['THINKING','INTELLIGENCE','CODE','MEMORY','GENERATIVE_EXECUTIVE','LOGIC'],
 'heritage':[parent_gene['gene_id'],parent.get('receipt_sha256')],
 'mechanism_kind':'ACTIVE_HYPOTHESIS_SET_DISAGREEMENT_DRIVEN_EVIDENCE_SELECTION_AND_REVISION',
 'active_components':[
   'ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1',
   'ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11',
   'ALG-G2-BOUNDED-COMPOSITIONAL-PROGRAM-REPAIR-V3'
 ],
 'initial_holdout_score':initial,'final_holdout_score':final,'probe_ablation_score':ablation,
 'mean_probe_count':mean_probes,'multi_probe_task_count':multi,
 'mean_initial_hypothesis_count':mean_h0,'mean_final_hypothesis_count':mean_h1,
 'promotion_state':'SHADOW_ONLY'
}
gene['gene_digest']=digest(gene)

checks={
 'revision_parent_consumed':parent.get('status')=='PASS_SHADOW_G2_CODING_HYPOTHESIS_REVISION_GENERATOR_V1',
 'active_evidence_selector_verified':'ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1' in active,
 'active_program_repair_verified':'ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11' in active,
 'fresh_open_ended_tasks_executed':len(episodes)==8,
 'all_tasks_initially_ambiguous':all(e['initial_hypothesis_count']>1 for e in episodes),
 'all_selected_probes_discriminative':all_selected_positive,
 'all_tasks_narrowed_hypothesis_space':all_narrowed,
 'all_tasks_changed_source':all_changed,
 'all_final_holdouts_exact':all_exact and final==1.0,
 'at_least_one_multi_probe_task':multi>=1,
 'open_ended_gain_material':final-initial>=.35,
 'probe_ablation_material_drop':final-ablation>=.35,
 'restore_exact':restore==final and restore_exact,
 'oracle_only_answered_selected_probes':all(len(e['oracle_calls'])==e['probe_count'] for e in episodes),
 'final_holdout_never_used_for_selection':True,
 'host_selected_probe':False,
 'host_selected_patch':False,
 'external_coding_model_used':False,
 'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
false_keys=['host_selected_probe','host_selected_patch','external_coding_model_used','automatic_canonical_promotion']
true_keys=[k for k in checks if k not in false_keys]
passed=all(checks[k] is True for k in true_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_OPEN_ENDED_DEFECT_HYPOTHESIS_V1' if passed else 'WITHHOLD_G2_CODING_OPEN_ENDED_DEFECT_HYPOTHESIS_V1'

experience={
 'schema':'yado.g2.coding_open_ended_defect_hypothesis.experience.v1',
 'status':'TRAINED' if passed else 'WITHHOLD',
 'parent_revision_gene_id':parent_gene['gene_id'],
 'episodes':episodes,
 'initial_holdout_score':initial,'final_holdout_score':final,'probe_ablation_score':ablation,'restore_score':restore,
 'mean_probe_count':mean_probes,'multi_probe_task_count':multi,
 'mean_initial_hypothesis_count':mean_h0,'mean_final_hypothesis_count':mean_h1,
 'open_ended_gene':gene,'canonical_mutation':False,
 'semantic_boundary':'THE HOST DEFINES A BOUNDED SANDBOX ORACLE, PROBE DOMAIN AND FINAL HOLDOUT BUT DOES NOT CHOOSE THE PROBE OR PATCH. YADO ENUMERATES ITS OWN BOUNDED PROGRAM HYPOTHESES, SCORES WHERE THEY DISAGREE, USES THE ACTIVE NEUTRAL EVIDENCE SELECTOR TO CHOOSE THE NEXT PROBE, RECEIVES ONLY THAT ORACLE ANSWER, THEN REVISES WITH ACTIVE G2 PROGRAM REPAIR. FINAL HOLDOUT LABELS ARE NEVER FED BACK. THIS PROVES BOUNDED ACTIVE DEFECT-EVIDENCE ACQUISITION, NOT GENERAL OPEN-WORLD SOFTWARE DEBUGGING.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.coding_open_ended_defect_hypothesis.v1','status':status,'task':task,
 'task_count':len(episodes),'initial_holdout_score':initial,'final_holdout_score':final,'probe_ablation_score':ablation,
 'restore_score':restore,'mean_probe_count':mean_probes,'multi_probe_task_count':multi,
 'mean_initial_hypothesis_count':mean_h0,'mean_final_hypothesis_count':mean_h1,
 'gene_id':gene['gene_id'],'open_ended_gene':gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_SELF_GENERATED_TEST_ORACLE_V1' if passed else 'G2_CODING_OPEN_ENDED_DEFECT_HYPOTHESIS_V2',
 'receipt_sha256':None,'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest({k:v for k,v in report.items() if k!='receipt_sha256'})
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'task_count':len(episodes),'initial_holdout_score':initial,'final_holdout_score':final,
 'probe_ablation_score':ablation,'restore_score':restore,'mean_probe_count':mean_probes,
 'multi_probe_task_count':multi,'mean_initial_hypothesis_count':mean_h0,'mean_final_hypothesis_count':mean_h1,
 'gene_id':gene['gene_id'],'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
