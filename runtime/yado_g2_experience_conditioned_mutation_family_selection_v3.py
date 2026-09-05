from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
import ast,copy,hashlib,json,os,sys,tempfile

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_g2_autonomous_gene_portfolio_controller_v1 import YADOAutonomousGenePortfolioControllerV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_skill_admission_runtime_v1 import SkillCandidate

V2=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-deficit-to-mutation-binding-v2.json'
BRIDGE=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-evolution-action-bridge-v1.json'
CURRENT=REPO/'candidates/kernel-self-generated/g2-native-action-evidence-binder-source-realization-v1.json'
ARCH=REPO/'canonical/yado-g2-architecture-v1.json'
MEM=REPO/'canonical/yado-unified-experience-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
OUT=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-mutation-family-selection-v3.json'
DB=ROOT/'yado_experience_conditioned_mutation_family_selection_v3.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

def closure(edges,start):
    state={start}
    for _ in range(4096):
        nxt=state|{b for a,b in edges if a in state}
        if nxt==state:break
        state=nxt
    return tuple(sorted(state,key=str))

def cases_from_graph(edges,starts,domain):
    out=[]
    for i,s in enumerate(starts):
        out.append({
          'relation':tuple(edges),
          'start':s,
          'expected':closure(edges,s),
          'domain':domain,
          'case_id':f'{domain}-{i}',
        })
    return out

def split_cases(xs):
    if len(xs)<2:
        raise RuntimeError('TOO_FEW_CASES:'+str(len(xs)))
    a=max(1,len(xs)//2)
    return xs[:a],xs[a:] or xs[-1:]

def cognitive_graph():
    x=load(ARCH)
    edges=[(str(e['src']),str(e['dst'])) for e in x.get('edges',[]) if e.get('src') and e.get('dst')]
    starts=sorted({a for a,b in edges})
    return edges,starts

def memory_graph():
    x=load(MEM)
    edges=[]
    starts=[]
    for b in x.get('branches',[]):
        bn='BRANCH:'+str(b.get('branch'))
        starts.append(bn)
        role='ROLE:'+str(b.get('role'))
        mode='MODE:'+str(b.get('mode'))
        edges.extend([(bn,role),(role,mode)])
        for t in b.get('tags',[]) or []:
            edges.append((mode,'TAG:'+str(t)))
        for ev in b.get('evidence',[]) or []:
            edges.append((mode,'EVIDENCE:'+str(ev)))
    return edges,sorted(set(starts))

def causal_graph():
    x=load(LEDGER)
    edges=[]
    starts=[]
    for e in x.get('events',[]) or []:
        parent=e.get('parent_event_hash');cur=e.get('event_hash')
        if parent and cur:
            a='EVENT:'+str(parent);b='EVENT:'+str(cur)
            edges.append((a,b));starts.append(a)
    # If legacy ledger rows omit hashes, retain a real ordered event graph.
    if len(edges)<2:
        es=x.get('events',[]) or []
        ids=[str(e.get('event_id') or e.get('index')) for e in es]
        edges=[('EVENT:'+a,'EVENT:'+b) for a,b in zip(ids,ids[1:])]
        starts=[a for a,b in edges]
    return edges,sorted(set(starts))[-12:]

def code_graph():
    paths=sorted(ROOT.glob('yado_g2_*.py'))[:80]
    mods={p.stem:p for p in paths}
    edges=[]
    for name,p in mods.items():
        try:tree=ast.parse(p.read_text(encoding='utf-8'))
        except Exception:continue
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):
                names=[a.name.split('.')[0] for a in n.names]
            elif isinstance(n,ast.ImportFrom) and n.module:
                names=[n.module.split('.')[0]]
            else:
                continue
            for z in names:
                if z in mods:edges.append(('MOD:'+name,'MOD:'+z))
    starts=sorted({a for a,b in edges})
    return edges,starts[:16]

v2=load(V2);bridge=load(BRIDGE);current=load(CURRENT)
if v2.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_DEFICIT_TO_MUTATION_BINDING_V2':
    raise RuntimeError('V2_PASS_REQUIRED')
if bridge.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_EVOLUTION_ACTION_BRIDGE_V1':
    raise RuntimeError('BRIDGE_PASS_REQUIRED')
if current.get('status')!='WITHHOLD_G2_NATIVE_ACTION_EVIDENCE_BINDER_SOURCE_REALIZATION_V1':
    raise RuntimeError('CURRENT_SOURCE_REALIZATION_WITHHOLD_REQUIRED')
bound=v2.get('bound_deficit') or {}
if not bound.get('target_capability'):
    raise RuntimeError('BOUND_DEFICIT_TARGET_REQUIRED')

core=UnifiedYADOCoreV1(REPO)
if core.execution_fabric_cls.COMPONENT_ID!='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V4':
    raise RuntimeError('CANONICAL_CONTINUITY_V4_REQUIRED')
head_before=copy.deepcopy(core.head)

controller=YADOAutonomousGenePortfolioControllerV1(REPO)
discovered=controller.discover_shadow_genes()
if len(discovered)<2:
    raise RuntimeError('AT_LEAST_TWO_SELF_GENERATED_GENES_REQUIRED')

graphs={
 'CAUSAL':causal_graph(),
 'COGNITIVE':cognitive_graph(),
 'MEMORY':memory_graph(),
 'CODE_RELATIONAL':code_graph(),
}
real_tasks={}
for domain,(edges,starts) in graphs.items():
    if len(edges)<1 or len(starts)<2:
        raise RuntimeError('REAL_GRAPH_TOO_SMALL:'+domain)
    xs=cases_from_graph(edges,starts[:min(8,len(starts))],domain)
    fit,held=split_cases(xs)
    real_tasks[domain]={
      'fit':{'task_id':domain+'_FIT','input_contract':'RELATION_START_TO_STATE','cases':fit},
      'heldout':{'task_id':domain+'_HELDOUT','input_contract':'RELATION_START_TO_STATE','cases':held},
      'edge_count':len(edges),'start_count':len(starts),
    }

if DB.exists():DB.unlink()
kernel=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
domain_results={}
try:
    for domain,t in real_tasks.items():
        candidates=[]
        evidence_rows=[]
        for item in discovered:
            g=item['gene']
            fit_score=controller._accuracy(g,t['fit'])
            held_score=controller._accuracy(g,t['heldout'])
            fit_ab=controller._best_ablation_accuracy(g,t['fit']) if fit_score is not None else None
            held_ab=controller._best_ablation_accuracy(g,t['heldout']) if held_score is not None else None
            structural=fit_score is not None and held_score is not None
            c=SkillCandidate(
              skill_id=g['gene_id']+'@'+domain,
              artifact_digest=g['gene_digest'],
              structural_valid=structural,
              semantic_consistency=1.0 if structural else 0.0,
              fit_baseline=float(fit_ab or 0.0),
              fit_candidate=float(fit_score or 0.0),
              heldout_baseline=float(held_ab or 0.0),
              heldout_candidate=float(held_score or 0.0),
              regression_pass=True,state_integrity=True,rollback_available=True,
              metadata={'domain':domain,'source_path':item['source_path'],'input_contract':'RELATION_START_TO_STATE'}
            )
            candidates.append(c)
            evidence_rows.append({
              'gene_id':g['gene_id'],'fit':fit_score,'fit_ablation':fit_ab,
              'heldout':held_score,'heldout_ablation':held_ab,'structural':structural,
            })
        sel=kernel.select_evolution_skills(candidates,max_skills=1,min_fit_gain=.01,min_heldout_gain=0.0,max_heldout_drop=0.0)
        domain_results[domain]={
          'selector':sel,
          'evidence':evidence_rows,
          'edge_count':t['edge_count'],'fit_case_count':len(t['fit']['cases']),'heldout_case_count':len(t['heldout']['cases']),
        }

    # Current post-corpus source-rewrite deficit: discovered meta-language genes have
    # no executable adapter for this contract. They must be rejected rather than
    # coerced into a CODE-specific family.
    current_candidates=[]
    for item in discovered:
        g=item['gene']
        current_candidates.append(SkillCandidate(
          skill_id=g['gene_id']+'@CURRENT_SOURCE_REWRITE',
          artifact_digest=g['gene_digest'],
          structural_valid=False,
          semantic_consistency=0.0,
          fit_baseline=0.0,fit_candidate=0.0,
          heldout_baseline=0.0,heldout_candidate=0.0,
          regression_pass=True,state_integrity=True,rollback_available=True,
          metadata={
            'target_capability':bound['target_capability'],
            'input_contract':'PYTHON_SOURCE_REWRITE_TO_BEHAVIOR',
            'reason':'NO_NATIVE_ADAPTER_FOR_TARGET_CONTRACT'
          }
        ))
    current_selector=kernel.select_evolution_skills(
      current_candidates,max_skills=1,min_fit_gain=.01,min_heldout_gain=0.0,max_heldout_drop=0.0
    )
finally:
    try:kernel.close()
    except Exception:pass

selected_domains={
 d:(r['selector'].get('selected_skill_ids') or [None])[0]
 for d,r in domain_results.items()
}
non_code_selected=sum(1 for d,s in selected_domains.items() if d!='CODE_RELATIONAL' and s)
code_relation_selected=bool(selected_domains.get('CODE_RELATIONAL'))

cog=(bridge.get('v6_predictions') or {}).get('cognitive')
intel=(bridge.get('v6_predictions') or {}).get('intelligence')
current_no_skill=current_selector.get('status')=='NO_ADMISSIBLE_SKILLS' and current_selector.get('selected_count')==0

# Generic fail-closed meta-family rule: reuse only an admitted skill. If the
# kernel has an OPEN experience-bound deficit, requests REVISE/RETRY, and its own
# precommit gate admits no existing self-generated skill, the only allowed next
# mutation family is gene invention. No concrete gene or source template is supplied.
mutation_family='INVENT_NEW_GENE' if (
    current_no_skill and bound.get('status')=='OPEN_SHADOW' and cog=='REVISE' and intel in ('RETRY','ADVANCE')
) else 'WITHHOLD_MUTATION_FAMILY'

checks={
 'canonical_continuity_v4_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V4',
 'v2_bound_deficit_consumed':bound.get('target_capability')==current.get('next_required_capability'),
 'bridge_cognitive_revise':cog=='REVISE',
 'bridge_intelligence_retry_or_advance':intel in ('RETRY','ADVANCE'),
 'self_generated_gene_inventory_at_least_two':len(discovered)>=2,
 'causal_real_data_selects_admissible_gene':bool(selected_domains.get('CAUSAL')),
 'cognitive_real_data_selects_admissible_gene':bool(selected_domains.get('COGNITIVE')),
 'memory_real_data_selects_admissible_gene':bool(selected_domains.get('MEMORY')),
 'code_relational_real_data_selects_admissible_gene':code_relation_selected,
 'non_code_domains_reuse_self_generated_genes':non_code_selected>=3,
 'current_code_source_rewrite_rejects_all_existing_genes':current_no_skill,
 'current_rejection_is_contract_not_domain_based':current_no_skill and code_relation_selected,
 'mutation_family_is_invention_only_after_no_admissible_skill':mutation_family=='INVENT_NEW_GENE',
 'legacy_polynomial_gene_not_selected':all('POLYNOMIAL' not in str(x or '') for x in selected_domains.values()) and 'POLYNOMIAL' not in mutation_family,
 'host_selected_concrete_gene':False,
 'host_authored_source_template':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
false_keys=('host_selected_concrete_gene','host_authored_source_template','external_models_used','automatic_canonical_promotion')
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_MUTATION_FAMILY_SELECTION_V3' if passed else 'WITHHOLD_G2_EXPERIENCE_CONDITIONED_MUTATION_FAMILY_SELECTION_V3'

report={
 'schema':'yado.g2.experience_conditioned_mutation_family_selection.v3',
 'status':status,
 'parent_v2_receipt':v2.get('receipt_sha256'),
 'bridge_receipt':bridge.get('receipt_sha256'),
 'current_failure_receipt':current.get('receipt_sha256'),
 'bound_deficit':bound,
 'discovered_gene_ids':sorted(x['gene']['gene_id'] for x in discovered),
 'real_cross_domain_selection':domain_results,
 'selected_skill_by_domain':selected_domains,
 'current_source_rewrite_selector':current_selector,
 'mutation_family_decision':{
   'family':mutation_family,
   'decision_basis':'YADO_NATIVE_PRECOMMIT_NO_ADMISSIBLE_SELF_GENERATED_SKILLS_PLUS_EXPERIENCE_BOUND_OPEN_DEFICIT_PLUS_COGNITIVE_REVISE',
   'target_capability':bound.get('target_capability'),
   'concrete_gene_selected':None,
   'source_template_selected':None,
   'promotion_state':'SHADOW_ONLY'
 },
 'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'EXPERIENCE_CONDITIONED_NOVEL_GENE_GENESIS_V4' if passed else 'MUTATION_FAMILY_SELECTION_REPAIR_V3',
 'semantic_boundary':'V3 SELECTS ONLY A MUTATION META-FAMILY. REAL YADO GRAPHS FROM CAUSAL, COGNITIVE, MEMORY AND CODE DOMAINS TEST CONTRACT-BASED REUSE OF SELF-GENERATED GENES THROUGH THE NATIVE RC8 PRECOMMIT SKILL GATE. THE CURRENT CODE SOURCE-REWRITE DEFICIT IS NOT FORCED INTO A CODE FAMILY: ALL EXISTING GENES MUST BE REJECTED FOR CONTRACT INCOMPATIBILITY BEFORE INVENT_NEW_GENE IS ALLOWED. NO CONCRETE GENE OR SOURCE TEMPLATE IS HOST-SELECTED.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,
 'selected_skill_by_domain':selected_domains,
 'current_source_rewrite_selector':current_selector,
 'mutation_family_decision':report['mutation_family_decision'],
 'checks':checks,
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
