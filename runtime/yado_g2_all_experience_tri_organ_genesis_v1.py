from __future__ import annotations

from pathlib import Path
from collections import defaultdict, deque
import ast, copy, hashlib, json, os, subprocess, sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_g2_autonomous_gene_portfolio_controller_v1 import YADOAutonomousGenePortfolioControllerV1

OUT=REPO/'candidates/kernel-self-generated/g2-all-experience-tri-organ-genesis-v1.json'
EXP=REPO/'experience/yado-all-experience-tri-organ-genesis-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
V7=REPO/'canonical/yado-g2-global-experience-meta-controller-v7.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'

EXCLUDE={
  'candidates/kernel-self-generated/g2-all-experience-tri-organ-genesis-v1.json',
  'experience/yado-all-experience-tri-organ-genesis-v1.json',
}

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

def rel_truth(edges,start):
    state={start}
    for _ in range(64):
        nxt=state|{b for a,b in edges if a in state}
        if nxt==state:break
        state=nxt
    return tuple(sorted(state,key=lambda x:(str(type(x)),str(x))))

def walk_strings(x):
    if isinstance(x,dict):
        for v in x.values():
            yield from walk_strings(v)
    elif isinstance(x,list):
        for v in x:
            yield from walk_strings(v)
    elif isinstance(x,str):
        yield x

def outcome_class(doc):
    out=str(doc.get('outcome') or '').upper()
    status=str(doc.get('status') or '').upper()
    if out in {'PASS','WITHHOLD','FAIL'}:return out
    if status.startswith('PASS') or 'PASS_' in status:return 'PASS'
    if status.startswith('WITHHOLD') or 'WITHHOLD_' in status:return 'WITHHOLD'
    if status.startswith('FAIL') or 'FAIL_' in status:return 'FAIL'
    return None

def action_class(doc):
    out=outcome_class(doc)
    nxt=doc.get('next_required_capability')
    if out=='PASS':return 'CONTINUE' if nxt else 'COMMIT'
    if out in {'WITHHOLD','FAIL'}:return 'REVISE' if nxt else 'SEEK_EVIDENCE'
    return None

def event_variants(keys):
    if len(keys)<3:return []
    Q='Q';R='R'
    valid=tuple([(Q,k) for k in keys]+[(R,k) for k in reversed(keys)])
    crossed=tuple([(Q,k) for k in keys]+[(R,k) for k in keys])
    # Underflow must be causally identifiable: after the invalid close, the
    # remaining suffix is fully balanced. REJECT stays False; IGNORE would turn True.
    balance_key=keys[-1]
    underflow=tuple([(R,keys[0]),(Q,balance_key),(R,balance_key)])
    unfinished=tuple(list(valid)[:-1])
    wrong='WRONG_'+hashlib.sha256(str(keys).encode()).hexdigest()[:12]
    w=list(valid);w[len(keys)]=(R,wrong)
    rep=keys[0]
    repeated=tuple([(Q,rep)]*len(keys)+[(R,rep)]*len(keys))
    return [
      {'events':valid,'expected':True,'kind':'VALID_NESTED'},
      {'events':crossed,'expected':False,'kind':'CROSSED_CLOSE'},
      {'events':underflow,'expected':False,'kind':'UNDERFLOW'},
      {'events':unfinished,'expected':False,'kind':'UNFINISHED'},
      {'events':tuple(w),'expected':False,'kind':'WRONG_KEY'},
      {'events':repeated,'expected':True,'kind':'REPEATED_KEY_VALID'},
    ]

# ---------------------------------------------------------------------------
# 1. Hash and parse the complete accumulated evidence surface.
# Every JSON artifact contributes to the content-addressed experience digest.
# Only structurally compatible records become executable training/evaluation cases.
# ---------------------------------------------------------------------------
roots=[
  REPO/'experience',
  REPO/'candidates'/'kernel-self-generated',
  REPO/'receipts',
  REPO/'audits',
]
paths=[]
for root in roots:
    if root.exists():
        paths.extend(p for p in root.rglob('*.json') if str(p.relative_to(REPO)) not in EXCLUDE)
if LEDGER not in paths:paths.append(LEDGER)
paths=sorted(set(paths),key=lambda p:str(p.relative_to(REPO)))

inventory=[]
docs={}
parse_failures=[]
for p in paths:
    rel=str(p.relative_to(REPO))
    sha=fsha(p)
    try:
        doc=load(p)
        docs[rel]=doc
        inventory.append({
          'path':rel,'sha256':sha,'schema':doc.get('schema'),
          'status':doc.get('status'),'outcome':doc.get('outcome'),
          'action':action_class(doc),
        })
    except Exception as e:
        parse_failures.append({'path':rel,'sha256':sha,'error':type(e).__name__+':'+str(e)})
        inventory.append({'path':rel,'sha256':sha,'schema':None,'status':None,'outcome':None,'action':None})

all_experience_digest=digest(inventory)
structured=[x for x in inventory if x.get('action')]
schemas=defaultdict(int)
actions=defaultdict(int)
for x in inventory:
    if x.get('schema'):schemas[str(x['schema'])]+=1
    if x.get('action'):actions[str(x['action'])]+=1

# Build a reference graph from explicit file references and exact content hashes.
all_paths={x['path'] for x in inventory}
sha_to_path={x['sha256']:x['path'] for x in inventory}
ref_edges=set()
for rel,doc in docs.items():
    for s in walk_strings(doc):
        if s in all_paths and s!=rel:
            ref_edges.add((s,rel))
        elif s in sha_to_path and sha_to_path[s]!=rel:
            ref_edges.add((sha_to_path[s],rel))

ledger=load(LEDGER)
events=sorted(ledger.get('events') or [],key=lambda e:int(e.get('index',0)))
if not events:raise RuntimeError('EMPTY_EVOLUTION_LEDGER')
event_hashes=[str(e['event_hash']) for e in events]
event_ids=[str(e.get('event_id') or e['event_hash']) for e in events]
ledger_edges=[]
for e in events:
    p=e.get('parent_event_hash');h=e.get('event_hash')
    if p and h:ledger_edges.append((str(p),str(h)))

# ---------------------------------------------------------------------------
# 2. Build experience-derived LOGIC tasks.
# The task is transitive causal/evidence closure over real accumulated lineage.
# Selection uses older/hashed partitions; fresh uses recent/unseen identifiers.
# ---------------------------------------------------------------------------
logic_select=[]
logic_fresh=[]

def chain_case(start_index,depth,domain):
    end=min(len(event_hashes),start_index+depth)
    hs=event_hashes[start_index:end]
    if len(hs)<4:return None
    rel=list(zip(hs[:-1],hs[1:]))
    # Add bounded distractor edges from a disjoint slice without changing reachability.
    d0=max(0,start_index-depth-6)
    ds=event_hashes[d0:start_index]
    rel+=list(zip(ds[:-1],ds[1:]))
    return {
      'relation':tuple(rel),'start':hs[0],'expected':rel_truth(rel,hs[0]),
      'domain':domain,'depth':len(hs),
    }

older_limit=max(80,int(len(event_hashes)*0.68))
sel_specs=[(8,7),(23,11),(47,17),(73,23),(101,31),(131,41)]
for st,dep in sel_specs:
    if st+dep<older_limit:
        c=chain_case(st,dep,'LEDGER_CAUSAL_OLD')
        if c:logic_select.append(c)

fresh_start=max(older_limit,len(event_hashes)-90)
fresh_specs=[(fresh_start+i,d) for i,d in zip((0,9,19,31,43,57),(9,13,19,27,35,49))]
for st,dep in fresh_specs:
    if st<len(event_hashes)-3:
        c=chain_case(st,dep,'LEDGER_CAUSAL_FRESH')
        if c:logic_fresh.append(c)

# Add real artifact-reference closure cases when the repository has connected evidence.
ref_edges_sorted=sorted(ref_edges)
if ref_edges_sorted:
    outgoing=defaultdict(list)
    for a,b in ref_edges_sorted:outgoing[a].append(b)
    starts=sorted(outgoing)
    for start in starts:
        full=rel_truth(ref_edges_sorted,start)
        if not (4<=len(full)<=48):continue
        allowed=set(full)
        local=[e for e in ref_edges_sorted if e[0] in allowed and e[1] in allowed]
        case={'relation':tuple(local),'start':start,'expected':rel_truth(local,start),'domain':'ARTIFACT_REFERENCE','depth':len(full)}
        bucket=int(hashlib.sha256(start.encode()).hexdigest()[:8],16)%10
        (logic_select if bucket<=6 else logic_fresh).append(case)
        if len(logic_select)>=14 and len(logic_fresh)>=10:break

# Keep deterministic bounded sets.
logic_select=logic_select[:14]
logic_fresh=logic_fresh[:10]
if len(logic_select)<5 or len(logic_fresh)<4:
    raise RuntimeError('INSUFFICIENT_EXPERIENCE_DERIVED_LOGIC_CASES:'+str((len(logic_select),len(logic_fresh))))

# ---------------------------------------------------------------------------
# 3. Build experience-derived THINKING tasks.
# Real causal event IDs become nested goal/subgoal stack keys. Fresh uses the latest
# lineage segment, so the event identifiers were not present in the older selection set.
# ---------------------------------------------------------------------------
thinking_select=[]
thinking_fresh=[]
for start,depth in [(5,4),(20,5),(40,6),(65,7),(90,8),(118,9),(146,10),(174,11)]:
    if start+depth<older_limit:
        keys=event_ids[start:start+depth]
        thinking_select.extend(event_variants(keys))

for start,depth in [
    (max(fresh_start,older_limit),12),
    (max(fresh_start+14,older_limit),14),
    (max(fresh_start+31,older_limit),16),
    (max(fresh_start+49,older_limit),18),
]:
    if start+depth<=len(event_ids):
        keys=event_ids[start:start+depth]
        thinking_fresh.extend(event_variants(keys))

if len(thinking_select)<24 or len(thinking_fresh)<12:
    raise RuntimeError('INSUFFICIENT_EXPERIENCE_DERIVED_THINKING_CASES:'+str((len(thinking_select),len(thinking_fresh))))

# ---------------------------------------------------------------------------
# 4. Let YADO discover its own previously self-synthesized genes and select a
# portfolio on the experience-derived tasks. No gene IDs are named here.
# ---------------------------------------------------------------------------
controller=YADOAutonomousGenePortfolioControllerV1(REPO)
discovered=controller.discover_shadow_genes()
selection_tasks=[
  {'task_id':'ALL_EXPERIENCE_LOGIC_SELECTION','input_contract':'RELATION_START_TO_STATE','cases':logic_select},
  {'task_id':'ALL_EXPERIENCE_THINKING_SELECTION','input_contract':'EVENT_SEQUENCE_TO_BOOLEAN','cases':thinking_select},
]
fresh_tasks=[
  {'task_id':'ALL_EXPERIENCE_LOGIC_FRESH','input_contract':'RELATION_START_TO_STATE','cases':logic_fresh},
  {'task_id':'ALL_EXPERIENCE_THINKING_FRESH','input_contract':'EVENT_SEQUENCE_TO_BOOLEAN','cases':thinking_fresh},
]
portfolio=controller.select_portfolio(selection_tasks)

fresh_eval={
 'LOGIC':controller.evaluate_portfolio(portfolio,fresh_tasks[0]),
 'THINKING':controller.evaluate_portfolio(portfolio,fresh_tasks[1]),
}

sel_logic=(portfolio.get('selected_by_task') or {}).get('ALL_EXPERIENCE_LOGIC_SELECTION')
sel_think=(portfolio.get('selected_by_task') or {}).get('ALL_EXPERIENCE_THINKING_SELECTION')
if not sel_logic or not sel_think:
    diagnostic={
      'schema':'yado.g2.all_experience_tri_organ_genesis.selection_diagnostic.v1',
      'status':'WITHHOLD_G2_ALL_EXPERIENCE_TRI_ORGAN_SELECTION_DIAGNOSTIC_V1',
      'all_experience_digest':all_experience_digest,
      'all_experience_inventory_count':len(inventory),
      'parse_failure_count':len(parse_failures),
      'structured_outcome_count':len(structured),
      'artifact_reference_edge_count':len(ref_edges),
      'ledger_event_count':len(events),
      'logic_selection_case_count':len(logic_select),
      'logic_fresh_case_count':len(logic_fresh),
      'thinking_selection_case_count':len(thinking_select),
      'thinking_fresh_case_count':len(thinking_fresh),
      'discovered_shadow_genes':[{
        'gene_id':x['gene'].get('gene_id'),
        'gene_digest':x['gene'].get('gene_digest'),
        'meta_language_component':x['gene'].get('meta_language_component'),
        'source_path':x.get('source_path'),
      } for x in discovered],
      'selection_portfolio':portfolio,
      'logic_selected':sel_logic,
      'thinking_selected':sel_think,
      'failure_reason':'YADO_PORTFOLIO_DID_NOT_SELECT_BOTH_ORGAN_TYPES',
      'canonical_mutation':False,
      'automatic_canonical_promotion':False,
      'next_required_capability':'ALL_EXPERIENCE_TRI_ORGAN_FAILED_SELECTION_CAUSAL_DIAGNOSIS_V2',
      'semantic_boundary':'DIAGNOSTIC ONLY. THRESHOLDS AND SELECTION ALGORITHMS ARE UNCHANGED. THE SCORE MATRIX IS PERSISTED SO THE FAILING ORGAN CAN BE DISTINGUISHED FROM A TRANSPORT FAILURE.'
    }
    diagnostic['receipt_sha256']=digest(diagnostic)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(diagnostic,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
    EXP.parent.mkdir(parents=True,exist_ok=True)
    EXP.write_text(json.dumps({
      'schema':'yado.g2.all_experience_tri_organ_genesis.experience_diagnostic.v1',
      'status':'WITHHOLD_SELECTION_DIAGNOSTIC',
      'all_experience_digest':all_experience_digest,
      'inventory_count':len(inventory),
      'structured_outcome_count':len(structured),
      'action_counts':dict(sorted(actions.items())),
      'schema_count':len(schemas),
      'artifact_reference_edge_count':len(ref_edges),
      'ledger_event_count':len(events),
      'portfolio':portfolio,
      'canonical_mutation':False,
    },indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
    print(json.dumps(diagnostic,indent=2,sort_keys=True,default=str))
    raise SystemExit(2)

by_digest={x['gene']['gene_digest']:x for x in portfolio.get('selected_genes',[])}
logic_item=by_digest[sel_logic['gene_digest']]
think_item=by_digest[sel_think['gene_digest']]
logic_gene0=logic_item['gene']
think_gene0=think_item['gene']

logic_fresh_ab=controller._best_ablation_accuracy(logic_gene0,fresh_tasks[0])
think_fresh_ab=controller._best_ablation_accuracy(think_gene0,fresh_tasks[1])
logic_fresh_score=float(fresh_eval['LOGIC']['best_score'])
think_fresh_score=float(fresh_eval['THINKING']['best_score'])

# Causal portfolio ablation: removing the selected mechanism must damage its fresh domain.
removal={}
for organ,sel,task in [
  ('LOGIC',sel_logic,fresh_tasks[0]),
  ('THINKING',sel_think,fresh_tasks[1]),
]:
    reduced=copy.deepcopy(portfolio)
    reduced['selected_genes']=[x for x in reduced.get('selected_genes',[]) if x['gene'].get('gene_digest')!=sel['gene_digest']]
    removal[organ]=controller.evaluate_portfolio(reduced,task)['best_score']

# ---------------------------------------------------------------------------
# 5. Birth three new organ-type bindings.
# LOGIC and THINKING bind self-synthesized executable genes to accumulated-experience
# semantics. INTELLIGENCE is a new portfolio-level mechanism that selects causal genes
# across contracts and is gated by the already admitted V7 accumulated-experience
# meta-controller. No canonical replacement occurs in this run.
# ---------------------------------------------------------------------------
head=load(HEAD)
v7=load(V7)
core=UnifiedYADOCoreV1(REPO)
head_before=core.head.get('canonical_head_digest')

def bind_gene(organ,base,mechanism,fresh_score,ablation_score,selection):
    g={
      'schema':'yado.g2.all_experience_organ_type_gene.v1',
      'organ':organ,
      'mechanism_type':mechanism,
      'underlying_self_synthesized_gene_id':base['gene_id'],
      'underlying_self_synthesized_gene_digest':base['gene_digest'],
      'underlying_meta_language_component':base['meta_language_component'],
      'operator_program':copy.deepcopy(base['operator_program']),
      'heritage':sorted(set(list(base.get('heritage') or [])+[base['gene_id']])),
      'all_experience_digest':all_experience_digest,
      'selection_portfolio_digest':portfolio['portfolio_digest'],
      'selection_score':float(selection['score']),
      'fresh_score':float(fresh_score),
      'fresh_best_structural_ablation':float(ablation_score if ablation_score is not None else 1.0),
      'fresh_causal_drop':float(fresh_score-(ablation_score if ablation_score is not None else fresh_score)),
      'novel_type':True,
      'primitive_gene_self_synthesized':base.get('novel_gene') is True,
      'promotion_state':'SHADOW_ONLY',
      'automatic_canonical_promotion':False,
    }
    g['gene_id']='GENE-G2-ALL-EXPERIENCE-'+organ+'-TYPE-V1-'+digest(g)[:16]
    g['gene_digest']=digest(g)
    return g

logic_gene=bind_gene(
  'LOGIC',logic_gene0,'RELATIONAL_CAUSAL_CLOSURE_LOGIC',
  logic_fresh_score,logic_fresh_ab,sel_logic,
)
thinking_gene=bind_gene(
  'THINKING',think_gene0,'CAUSAL_EVENT_STATE_STACK_THINKING',
  think_fresh_score,think_fresh_ab,sel_think,
)

controller_source=(ROOT/'yado_g2_autonomous_gene_portfolio_controller_v1.py').read_text(encoding='utf-8')
tree=ast.parse(controller_source)
controller_has_explicit_gene_ids='GENE-SELF-SYNTHESIZED-' in controller_source
controller_makes_synthesis_calls=any(
    isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='synthesize'
    for n in ast.walk(tree)
)

intelligence_gene={
  'schema':'yado.g2.all_experience_organ_type_gene.v1',
  'organ':'INTELLIGENCE',
  'mechanism_type':'EXPERIENCE_CONDITIONED_CAUSAL_GENE_PORTFOLIO_INTELLIGENCE',
  'controller_id':YADOAutonomousGenePortfolioControllerV1.COMPONENT_ID,
  'all_experience_digest':all_experience_digest,
  'portfolio':copy.deepcopy(portfolio),
  'v7_meta_controller':{
    'component_id':v7.get('component_id'),
    'genome_id':v7.get('genome_id'),
    'genome_digest':v7.get('genome_digest'),
    'status':v7.get('status'),
    'automatic_canonical_promotion':v7.get('automatic_canonical_promotion'),
  },
  'fresh_contract_scores':{
    'RELATION_START_TO_STATE':logic_fresh_score,
    'EVENT_SEQUENCE_TO_BOOLEAN':think_fresh_score,
  },
  'winner_removal_scores':copy.deepcopy(removal),
  'routing_basis':'TASK_CONTRACT_PLUS_FRESH_EXACT_AND_CAUSAL_ABLATION',
  'selected_gene_count':portfolio.get('selected_gene_count',0),
  'selected_gene_ids':[x['gene']['gene_id'] for x in portfolio.get('selected_genes',[])],
  'controller_gene_id_specific_rules':controller_has_explicit_gene_ids,
  'controller_resynthesis_during_selection':controller_makes_synthesis_calls,
  'novel_type':True,
  'primitive_gene_self_synthesized':False,
  'promotion_state':'SHADOW_ONLY',
  'automatic_canonical_promotion':False,
}
intelligence_gene['gene_id']='GENE-G2-ALL-EXPERIENCE-INTELLIGENCE-TYPE-V1-'+digest(intelligence_gene)[:16]
intelligence_gene['gene_digest']=digest(intelligence_gene)

genes={'LOGIC':logic_gene,'THINKING':thinking_gene,'INTELLIGENCE':intelligence_gene}
genome={
  'schema':'yado.g2.all_experience_tri_organ_genome.v1',
  'generation':'G2_SHADOW',
  'all_experience_digest':all_experience_digest,
  'organs':{k:v['gene_id'] for k,v in genes.items()},
  'organ_gene_digests':{k:v['gene_digest'] for k,v in genes.items()},
  'rollback_parents':{
    'LOGIC':'ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2',
    'THINKING':'ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2',
    'INTELLIGENCE':'ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3',
  },
  'v4_rollback_parent':'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4',
  'promotion_state':'SHADOW_ONLY',
  'automatic_canonical_promotion':False,
  'g3_genesis_performed':False,
}
genome['genome_id']='GENOME-G2-ALL-EXPERIENCE-TRI-ORGAN-V1-'+digest(genome)[:16]
genome['genome_digest']=digest(genome)

active=set(head.get('active_capabilities') or [])
parent_ids=set(genome['rollback_parents'].values())
selected_underlying={logic_gene0['gene_id'],think_gene0['gene_id']}

checks={
  'all_experience_files_hashed':len(inventory)==len(paths),
  'all_experience_parse_failures_zero':len(parse_failures)==0,
  'all_experience_inventory_ge_200':len(inventory)>=200,
  'structured_outcomes_ge_100':len(structured)>=100,
  'ledger_all_events_consumed':len(events)==int(ledger.get('event_count',len(events))),
  'artifact_reference_graph_present':len(ref_edges)>0,
  'logic_selection_cases_ge_5':len(logic_select)>=5,
  'logic_fresh_cases_ge_4':len(logic_fresh)>=4,
  'thinking_selection_cases_ge_24':len(thinking_select)>=24,
  'thinking_fresh_cases_ge_12':len(thinking_fresh)>=12,
  'at_least_two_self_synthesized_genes_discovered':len(discovered)>=2,
  'portfolio_selected_two_organ_mechanisms':sel_logic is not None and sel_think is not None,
  'selected_underlying_genes_distinct':logic_gene0['gene_digest']!=think_gene0['gene_digest'],
  'selected_underlying_genes_self_synthesized':logic_gene0.get('novel_gene') is True and think_gene0.get('novel_gene') is True,
  'selected_underlying_genes_shadow_only':logic_gene0.get('promotion_state')=='SHADOW_ONLY' and think_gene0.get('promotion_state')=='SHADOW_ONLY',
  'logic_new_type_not_canonical_parent':logic_gene0['gene_id'] not in parent_ids and logic_gene0['gene_id'] not in active,
  'thinking_new_type_not_canonical_parent':think_gene0['gene_id'] not in parent_ids and think_gene0['gene_id'] not in active,
  'logic_fresh_exact':logic_fresh_score==1.0,
  'thinking_fresh_exact':think_fresh_score==1.0,
  'logic_structural_ablation_drop_ge_0_20':logic_gene['fresh_causal_drop']>=.20,
  'thinking_structural_ablation_drop_ge_0_10':thinking_gene['fresh_causal_drop']>=.10,
  'logic_winner_removal_causes_drop':removal['LOGIC']<1.0,
  'thinking_winner_removal_causes_drop':removal['THINKING']<1.0,
  'intelligence_selected_gene_count_ge_2':intelligence_gene['selected_gene_count']>=2,
  'intelligence_fresh_both_contracts_exact':min(intelligence_gene['fresh_contract_scores'].values())==1.0,
  'intelligence_portfolio_removal_causal':all(v<1.0 for v in removal.values()),
  'intelligence_controller_has_no_explicit_gene_ids':controller_has_explicit_gene_ids is False,
  'intelligence_controller_does_not_resynthesize_during_selection':controller_makes_synthesis_calls is False,
  'v7_meta_controller_canonical_active':v7.get('status')=='CANONICAL_ACTIVE' and v7.get('component_id') in active,
  'v4_remains_active':'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4' in active,
  'all_three_organ_type_ids_new':len({x['gene_id'] for x in genes.values()})==3 and all(x['gene_id'] not in active for x in genes.values()),
  'automatic_canonical_promotion_false':all(x['automatic_canonical_promotion'] is False for x in genes.values()) and genome['automatic_canonical_promotion'] is False,
  'canonical_unchanged':core.head.get('canonical_head_digest')==head_before,
  'formal_generation_unchanged':head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
  'g3_not_started':head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_ALL_EXPERIENCE_TRI_ORGAN_GENESIS_V1' if all(checks.values()) else 'WITHHOLD_G2_ALL_EXPERIENCE_TRI_ORGAN_GENESIS_V1'

experience={
  'schema':'yado.g2.all_experience_tri_organ_genesis.experience.v1',
  'status':'TRAINED_SHADOW' if status.startswith('PASS') else 'WITHHOLD',
  'all_experience_digest':all_experience_digest,
  'inventory_count':len(inventory),
  'parse_failure_count':len(parse_failures),
  'structured_outcome_count':len(structured),
  'action_counts':dict(sorted(actions.items())),
  'schema_count':len(schemas),
  'top_schemas':sorted([{'schema':k,'count':v} for k,v in schemas.items()],key=lambda x:(-x['count'],x['schema']))[:40],
  'artifact_reference_edge_count':len(ref_edges),
  'ledger_event_count':len(events),
  'logic_selection_case_count':len(logic_select),
  'logic_fresh_case_count':len(logic_fresh),
  'thinking_selection_case_count':len(thinking_select),
  'thinking_fresh_case_count':len(thinking_fresh),
  'discovered_shadow_gene_ids':[x['gene']['gene_id'] for x in discovered],
  'portfolio':copy.deepcopy(portfolio),
  'fresh_eval':copy.deepcopy(fresh_eval),
  'winner_removal_scores':copy.deepcopy(removal),
  'genes':copy.deepcopy(genes),
  'genome':copy.deepcopy(genome),
  'checks':copy.deepcopy(checks),
  'semantic_boundary':'EVERY ACCUMULATED JSON EVIDENCE ARTIFACT IS CONTENT-HASHED INTO THE EXPERIENCE DIGEST. ONLY STRUCTURALLY COMPATIBLE CAUSAL/OUTCOME EVIDENCE BECOMES EXECUTABLE TRAINING OR FRESH CASES. LOGIC AND THINKING ARE NEW G2 ORGAN-TYPE BINDINGS OVER YADO SELF-SYNTHESIZED SHADOW GENES; INTELLIGENCE IS A NEW PORTFOLIO-LEVEL TYPE BUILT BY YADO GENE DISCOVERY/SELECTION PLUS THE ADMITTED V7 META-CONTROLLER. THIS IS SHADOW EVIDENCE, NOT A CLAIM OF GENERAL INTELLIGENCE OR SUBJECTIVE CONSCIOUSNESS.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True)
EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
  'schema':'yado.g2.all_experience_tri_organ_genesis.v1',
  'status':status,
  'all_experience_digest':all_experience_digest,
  'all_experience_inventory_count':len(inventory),
  'parse_failure_count':len(parse_failures),
  'structured_outcome_count':len(structured),
  'artifact_reference_edge_count':len(ref_edges),
  'ledger_event_count':len(events),
  'logic':{
    'gene_id':logic_gene['gene_id'],'mechanism_type':logic_gene['mechanism_type'],
    'underlying_self_synthesized_gene_id':logic_gene0['gene_id'],
    'selection_case_count':len(logic_select),'fresh_case_count':len(logic_fresh),
    'fresh_score':logic_fresh_score,'best_structural_ablation_accuracy':logic_fresh_ab,
    'causal_drop':logic_gene['fresh_causal_drop'],
  },
  'thinking':{
    'gene_id':thinking_gene['gene_id'],'mechanism_type':thinking_gene['mechanism_type'],
    'underlying_self_synthesized_gene_id':think_gene0['gene_id'],
    'selection_case_count':len(thinking_select),'fresh_case_count':len(thinking_fresh),
    'fresh_score':think_fresh_score,'best_structural_ablation_accuracy':think_fresh_ab,
    'causal_drop':thinking_gene['fresh_causal_drop'],
  },
  'intelligence':{
    'gene_id':intelligence_gene['gene_id'],'mechanism_type':intelligence_gene['mechanism_type'],
    'controller_id':intelligence_gene['controller_id'],
    'selected_gene_ids':intelligence_gene['selected_gene_ids'],
    'fresh_contract_scores':intelligence_gene['fresh_contract_scores'],
    'winner_removal_scores':intelligence_gene['winner_removal_scores'],
    'v7_meta_controller':intelligence_gene['v7_meta_controller'],
  },
  'genome_id':genome['genome_id'],
  'genome_digest':genome['genome_digest'],
  'checks':checks,
  'canonical_mutation':False,'architecture_mutation':False,
  'generation_transition':False,'g3_genesis_performed':False,
  'automatic_canonical_promotion':False,
  'next_required_capability':'ALL_EXPERIENCE_TRI_ORGAN_CROSS_DOMAIN_STRESS_AND_CANONICAL_ADMISSION_V2' if status.startswith('PASS') else 'ALL_EXPERIENCE_TRI_ORGAN_GENESIS_REPAIR_V2',
  'semantic_boundary':experience['semantic_boundary'],
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

print(json.dumps({
  'status':status,
  'all_experience_inventory_count':len(inventory),
  'structured_outcome_count':len(structured),
  'artifact_reference_edge_count':len(ref_edges),
  'ledger_event_count':len(events),
  'logic':report['logic'],
  'thinking':report['thinking'],
  'intelligence':report['intelligence'],
  'genome_id':genome['genome_id'],
  'checks':checks,
  'next_required_capability':report['next_required_capability'],
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))

if status!='PASS_SHADOW_G2_ALL_EXPERIENCE_TRI_ORGAN_GENESIS_V1':
    raise SystemExit(2)
