from __future__ import annotations

from pathlib import Path
import hashlib, json, copy, py_compile

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent

TRI=REPO/'experience/yado-all-experience-tri-organ-genesis-v1.json'
TRI_REPORT=REPO/'candidates/kernel-self-generated/g2-all-experience-tri-organ-genesis-v1.json'
DNS=REPO/'candidates/kernel-self-generated/g2-dns-gcp-cross-domain-research-stress-v1.json'
FOUR=REPO/'candidates/kernel-self-generated/g2-four-domain-fresh-stress-v1.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
AUDIT=REPO/'audits/yado-full-kernel-audit-v1-report.json'
SEC=REPO/'audits/yado-security-audit-v1-report.json'
INTEG=REPO/'audits/yado-g2-post-module-full-integrity-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-all-experience-tri-organ-canonical-admission-review-v2.json'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

tri=load(TRI);tr=load(TRI_REPORT);dns=load(DNS);four=load(FOUR)
head=load(HEAD);core=load(CORE);prov=load(PROV);audit=load(AUDIT);sec=load(SEC);integ=load(INTEG)

GENOME='GENOME-G2-ALL-EXPERIENCE-TRI-ORGAN-V1-9e3b058de601792a'
NEW={
 'LOGIC':'GENE-G2-ALL-EXPERIENCE-LOGIC-TYPE-V1-922acdf42b997fa8',
 'THINKING':'GENE-G2-ALL-EXPERIENCE-THINKING-TYPE-V1-d3bbd70403aafcd4',
 'INTELLIGENCE':'GENE-G2-ALL-EXPERIENCE-INTELLIGENCE-TYPE-V1-594261c030db685e',
}
ROLLBACK={
 'LOGIC':'ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2',
 'THINKING':'ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2',
 'INTELLIGENCE':'ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3',
}
V4='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4'
V7='CTRL-G2-GLOBAL-EXPERIENCE-META-CONTROLLER-V7'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'

genes=tri.get('genes') or {}
active=set(head.get('active_capabilities') or [])
sources=set(core.get('active_runtime_sources') or [])

logic_prog=genes['LOGIC']['operator_program']
think_prog=genes['THINKING']['operator_program']
intel=genes['INTELLIGENCE']
portfolio=intel['portfolio']

required_runtime=[
 REPO/'runtime/yado_generic_relational_meta_language_v1.py',
 REPO/'runtime/yado_generic_event_state_meta_language_v1.py',
 REPO/'runtime/yado_g2_autonomous_gene_portfolio_controller_v1.py',
]
compile_results={}
for p in required_runtime:
    try:
        py_compile.compile(str(p),doraise=True)
        compile_results[str(p.relative_to(REPO))]=True
    except Exception:
        compile_results[str(p.relative_to(REPO))]=False

# Aggregate independent evidence without changing any gene or threshold.
dns_logic=float((dns.get('logic') or {}).get('accuracy') or 0)
dns_think=float((dns.get('thinking') or {}).get('accuracy') or 0)
dns_intel=min(float((dns.get('intelligence') or {}).get('relation_best_score') or 0),
              float((dns.get('intelligence') or {}).get('event_best_score') or 0))
four_domains=four.get('domain_results') or {}
four_logic=min(float((x.get('logic') or {}).get('accuracy') or 0) for x in four_domains.values())
four_think=min(float((x.get('thinking') or {}).get('accuracy') or 0) for x in four_domains.values())
four_intel=min(
    min(float((x.get('intelligence') or {}).get('relation_best_score') or 0),
        float((x.get('intelligence') or {}).get('event_best_score') or 0))
    for x in four_domains.values()
)
four_logic_drop=min(float((x.get('logic') or {}).get('causal_drop') or 0) for x in four_domains.values())
four_think_drop=min(float((x.get('thinking') or {}).get('causal_drop') or 0) for x in four_domains.values())

# The admission mode is deliberately additive: parents stay active and remain the rollback path.
proposed_components={
 'LOGIC':{
   'component_id':'ALG-G2-ALL-EXPERIENCE-RELATIONAL-CAUSAL-LOGIC-V1',
   'gene_id':NEW['LOGIC'],
   'mechanism_type':genes['LOGIC']['mechanism_type'],
   'rollback_parent':ROLLBACK['LOGIC'],
   'operator_program_digest':logic_prog['program_digest'],
 },
 'THINKING':{
   'component_id':'ALG-G2-ALL-EXPERIENCE-CAUSAL-EVENT-THINKING-V1',
   'gene_id':NEW['THINKING'],
   'mechanism_type':genes['THINKING']['mechanism_type'],
   'rollback_parent':ROLLBACK['THINKING'],
   'operator_program_digest':think_prog['program_digest'],
 },
 'INTELLIGENCE':{
   'component_id':'ALG-G2-ALL-EXPERIENCE-CAUSAL-GENE-PORTFOLIO-INTELLIGENCE-V1',
   'gene_id':NEW['INTELLIGENCE'],
   'mechanism_type':genes['INTELLIGENCE']['mechanism_type'],
   'rollback_parent':ROLLBACK['INTELLIGENCE'],
   'portfolio_digest':portfolio['portfolio_digest'],
 }
}

checks={
 'tri_genesis_pass':tr.get('status')=='PASS_SHADOW_G2_ALL_EXPERIENCE_TRI_ORGAN_GENESIS_V1',
 'tri_experience_trained_shadow':tri.get('status')=='TRAINED_SHADOW',
 'genome_exact':(tri.get('genome') or {}).get('genome_id')==GENOME,
 'three_gene_ids_exact':all((genes.get(k) or {}).get('gene_id')==v for k,v in NEW.items()),
 'all_new_genes_shadow_only':all((genes.get(k) or {}).get('promotion_state')=='SHADOW_ONLY' for k in NEW),
 'primitive_logic_self_synthesized':genes['LOGIC'].get('primitive_gene_self_synthesized') is True,
 'primitive_thinking_self_synthesized':genes['THINKING'].get('primitive_gene_self_synthesized') is True,
 'intelligence_portfolio_selected_two':int(portfolio.get('selected_gene_count') or 0)>=2,
 'intelligence_no_explicit_gene_rules':genes['INTELLIGENCE'].get('controller_gene_id_specific_rules') is False,
 'intelligence_no_resynthesis_during_selection':genes['INTELLIGENCE'].get('controller_resynthesis_during_selection') is False,
 'dns_gcp_pass':dns.get('status')=='PASS_SHADOW_G2_DNS_GCP_CROSS_DOMAIN_RESEARCH_STRESS_V1',
 'dns_gcp_logic_exact':dns_logic==1.0,
 'dns_gcp_thinking_exact':dns_think==1.0,
 'dns_gcp_intelligence_exact':dns_intel==1.0,
 'four_domain_pass':four.get('status')=='PASS_SHADOW_G2_FOUR_DOMAIN_FRESH_STRESS_V1',
 'four_domains_exactly_four':len(four_domains)==4,
 'four_domain_logic_floor_1':four_logic==1.0,
 'four_domain_thinking_floor_1':four_think==1.0,
 'four_domain_intelligence_floor_1':four_intel==1.0,
 'four_domain_logic_causal_floor_ge_0_20':four_logic_drop>=.20,
 'four_domain_thinking_causal_floor_ge_0_10':four_think_drop>=.10,
 'frozen_program_digests_unchanged':four.get('program_digests_before')==four.get('program_digests_after'),
 'no_reselection_across_four_domains':four.get('checks',{}).get('no_gene_reselection') is True,
 'no_resynthesis_across_four_domains':four.get('checks',{}).get('no_resynthesis') is True,
 'rollback_logic_parent_active':ROLLBACK['LOGIC'] in active,
 'rollback_thinking_parent_active':ROLLBACK['THINKING'] in active,
 'rollback_intelligence_parent_active':ROLLBACK['INTELLIGENCE'] in active,
 'v4_active':V4 in active,
 'v7_active':V7 in active,
 'new_components_not_already_active':all(x['component_id'] not in active for x in proposed_components.values()),
 'required_runtime_compiles':all(compile_results.values()),
 'canonical_full_audit_pass':audit.get('status')=='PASS' and not audit.get('findings'),
 'canonical_security_pass':sec.get('status')=='PASS' and int(sec.get('high_confidence_secret_hits') or 0)==0 and int(sec.get('dependency_vulnerability_count') or 0)==0,
 'post_module_integrity_pass':integ.get('status')=='PASS_G2_POST_MODULE_FULL_INTEGRITY_V1',
 'canonical_generation_g2':head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
 'frontier_preserved':head.get('current_frontier')==FRONT and core.get('current_frontier')==FRONT,
 'g3_not_started':head.get('g3_genesis_performed') is False and core.get('g3_genesis_performed') is False,
 'review_does_not_mutate_canonical':True,
}

status='PASS_REVIEW_G2_ALL_EXPERIENCE_TRI_ORGAN_CANONICAL_ADMISSION_V2' if all(checks.values()) else 'WITHHOLD_REVIEW_G2_ALL_EXPERIENCE_TRI_ORGAN_CANONICAL_ADMISSION_V2'

plan={
 'admission_mode':'ADDITIVE_WITH_ROLLBACK_PARENTS',
 'replace_existing_organs':False,
 'proposed_components':proposed_components,
 'preserve_active_components':[ROLLBACK['LOGIC'],ROLLBACK['THINKING'],ROLLBACK['INTELLIGENCE'],V4,V7],
 'required_binding_surfaces':[
   'canonical tri-organ component artifact',
   'unified core runtime binding',
   'unified module kernel registry and dispatch',
   'architecture planes',
   'algorithm provenance registry',
   'runtime integrity manifest',
   'module dependency graph edges',
   'evolution ledger admission event',
 ],
 'post_binding_gates':[
   'canonical invariant guard',
   'compile all active runtime sources',
   'top-level 13 regression tests',
   'unified module fresh gate',
   'post-module full integrity',
   'security audit',
   'full kernel audit',
 ],
 'rollback_rule':'IF ANY POST_BINDING GATE FAILS, DO NOT UPDATE MAIN; RESTORE THREE PARENT ORGANS AS SOLE ACTIVE ORGAN EXECUTION PATH.',
 'main_update_policy':'NO MAIN UPDATE IN REVIEW STEP'
}

report={
 'schema':'yado.g2.all_experience_tri_organ.canonical_admission_review.v2',
 'status':status,
 'reviewed_genome_id':GENOME,
 'reviewed_gene_ids':NEW,
 'evidence':{
   'tri_genesis_receipt_sha256':tr.get('receipt_sha256'),
   'dns_gcp_receipt_sha256':dns.get('receipt_sha256'),
   'four_domain_receipt_sha256':four.get('receipt_sha256'),
   'four_domain_experience_digest':four.get('experience_digest'),
   'current_full_audit_status':audit.get('status'),
   'current_security_status':sec.get('status'),
   'current_post_module_integrity_status':integ.get('status'),
 },
 'cross_domain_floor':{
   'dns_gcp':{'logic':dns_logic,'thinking':dns_think,'intelligence':dns_intel},
   'four_domain':{'logic':four_logic,'thinking':four_think,'intelligence':four_intel,
                  'logic_causal_drop':four_logic_drop,'thinking_causal_drop':four_think_drop}
 },
 'required_runtime_compile':compile_results,
 'checks':checks,
 'admission_plan':plan,
 'canonical_mutation':False,
 'architecture_mutation':False,
 'automatic_canonical_promotion':False,
 'generation_transition':False,
 'g3_genesis_performed':False,
 'next_required_capability':'TRI_ORGAN_ADDITIVE_CANONICAL_BINDING_V2' if status.startswith('PASS') else 'TRI_ORGAN_CANONICAL_ADMISSION_REVIEW_REPAIR_V3',
 'semantic_boundary':'THIS STEP REVIEWS EVIDENCE AND CONSTRUCTS A FAIL-CLOSED ADDITIVE ADMISSION PLAN ONLY. IT DOES NOT ACTIVATE THE SHADOW ORGANS, REPLACE THE CURRENT ORGAN PARENTS, MUTATE MAIN, CLAIM GENERAL INTELLIGENCE, OR CLAIM SUBJECTIVE CONSCIOUSNESS.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True,default=str))
if status!='PASS_REVIEW_G2_ALL_EXPERIENCE_TRI_ORGAN_CANONICAL_ADMISSION_V2':
    raise SystemExit(2)
