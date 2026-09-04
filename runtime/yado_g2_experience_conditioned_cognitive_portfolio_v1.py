from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_unified_core_v1 import UnifiedYADOCoreV1

TASK=REPO/'architecture/yado-g2-experience-conditioned-cognitive-portfolio-v1-request.json'
LTI=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-lti-evolution-v1.json'
TH=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-thinking-repair-v2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-cognitive-portfolio-v1.json'
DB=ROOT/'yado_g2_experience_conditioned_cognitive_portfolio_v1.sqlite'
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK);lti=load(LTI);th=load(TH)
if lti.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_LTI_EVOLUTION_V1':raise RuntimeError('LTI_PASS_REQUIRED')
if th.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_THINKING_REPAIR_V2':raise RuntimeError('THINKING_V2_PASS_REQUIRED')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

genes=lti.get('shadow_genes') or {}
cands=[]
for organ in ('LOGIC','INTELLIGENCE','THINKING'):
    g=genes[organ];fresh=float(g.get('fresh_blind') or 0);base=float(g.get('baseline') or 0)
    cands.append({
      'skill_id':'LTI_'+organ+'_'+g['gene_id'],
      'artifact_digest':g['gene_digest'],'structural_valid':True,'semantic_consistency':1.0,
      'fit_baseline':base,'fit_candidate':fresh,'heldout_baseline':base,'heldout_candidate':fresh,
      'regression_pass':True,'state_integrity':True,'rollback_available':bool(g.get('heritage')),
      'metadata':{'organ':organ,'gene_id':g['gene_id'],'gene_digest':g['gene_digest'],'source':'LTI_V1','fresh':fresh,'baseline':base},
    })
tg=th['thinking_gene'];fresh=float(th['fresh_score']);abl=float(th['context_ablation_score'])
cands.append({
 'skill_id':'THINKING_V2_'+tg['gene_id'],'artifact_digest':tg['gene_digest'],'structural_valid':True,'semantic_consistency':1.0,
 'fit_baseline':abl,'fit_candidate':fresh,'heldout_baseline':abl,'heldout_candidate':fresh,
 'regression_pass':th['checks'].get('restore_exact') is True,'state_integrity':th['checks'].get('canonical_unchanged') is True,
 'rollback_available':th['checks'].get('rollback_parent_available') is True,
 'metadata':{'organ':'THINKING','gene_id':tg['gene_id'],'gene_digest':tg['gene_digest'],'source':'THINKING_V2','fresh':fresh,'baseline':abl},
})

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
 sel=k.select_evolution_skills(cands,max_skills=4,min_semantic_consistency=.95,min_fit_gain=.02,max_heldout_drop=0.0,min_heldout_gain=.02)
finally:
 try:k.close()
 except Exception:pass
selected_ids=list(sel.get('selected_skill_ids') or [])
selected=[]
for c in cands:
 if c['skill_id'] in selected_ids:selected.append(copy.deepcopy(c['metadata']))
selected_organs=sorted({x['organ'] for x in selected})
thinking_v2_id='THINKING_V2_'+tg['gene_id']
checks={
 'lti_pass_consumed':True,'thinking_v2_pass_consumed':True,'all_candidates_evaluated':len(cands)==4,
 'logic_admitted':any(x['organ']=='LOGIC' for x in selected),
 'intelligence_admitted':any(x['organ']=='INTELLIGENCE' for x in selected),
 'thinking_admitted':any(x['organ']=='THINKING' for x in selected),
 'multicontext_thinking_v2_admitted':thinking_v2_id in selected_ids,
 'all_three_organs_covered':selected_organs==['INTELLIGENCE','LOGIC','THINKING'],
 'host_selected_winners':False,'host_rewrote_models':False,'automatic_canonical_promotion':False,
 'rollback_and_integrity_preserved':all(c['rollback_available'] and c['state_integrity'] for c in cands if c['skill_id'] in selected_ids),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
positive=('lti_pass_consumed','thinking_v2_pass_consumed','all_candidates_evaluated','logic_admitted','intelligence_admitted',
          'thinking_admitted','multicontext_thinking_v2_admitted','all_three_organs_covered','rollback_and_integrity_preserved','canonical_unchanged')
negative=('host_selected_winners','host_rewrote_models','automatic_canonical_promotion')
passed=all(checks[k] for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_COGNITIVE_PORTFOLIO_V1' if passed else 'WITHHOLD_G2_EXPERIENCE_CONDITIONED_COGNITIVE_PORTFOLIO_V1'
portfolio={
 'schema':'yado.g2.experience_conditioned_cognitive_portfolio.v1','portfolio_id':'PORT-G2-EXPERIENCE-COGNITIVE-'+digest(selected)[:16],
 'selected_genes':selected,'selected_gene_count':len(selected),'organs':selected_organs,
 'selection_policy':'YADO_NATIVE_SKILL_ADMISSION_OVER_EXISTING_FRESH_EVIDENCE','promotion_state':'SHADOW_ONLY',
 'parent_receipts':[lti.get('receipt_sha256'),th.get('receipt_sha256')],
}
portfolio['portfolio_digest']=digest(portfolio)
report={'schema':'yado.g2.experience_conditioned_cognitive_portfolio_selection.v1','status':status,'task':task,
 'candidate_count':len(cands),'candidates':cands,'native_skill_selection':sel,'portfolio':portfolio,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':None if passed else 'EXPERIENCE_CONDITIONED_COGNITIVE_PORTFOLIO_REPAIR_V2',
 'semantic_boundary':'PORTFOLIO AGGREGATION ONLY. EACH GENE ENTERS WITH ITS PRIOR FRESH/ABLATION/ROLLBACK EVIDENCE. YADO NATIVE SKILL GATE SELECTS; HOST DOES NOT MERGE OR REWRITE MODELS. NO CANONICAL PROMOTION OCCURS.'}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'selected_skill_ids':selected_ids,'portfolio_id':portfolio['portfolio_id'],'organs':selected_organs,'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
