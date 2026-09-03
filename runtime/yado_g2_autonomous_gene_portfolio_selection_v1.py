from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_g2_autonomous_gene_portfolio_controller_v1 import YADOAutonomousGenePortfolioControllerV1

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()

def rel_truth(edges,start):
    state={start}
    for _ in range(512):
        nxt=state|{b for a,b in edges if a in state}
        if nxt==state: break
        state=nxt
    return tuple(sorted(state,key=lambda x:(str(type(x)),str(x))))

def rel_case(rng,n,domain,cycle=False):
    token=f'{rng.randrange(10**14):014d}'
    nodes=[f'{domain}_{token}_{i}' for i in range(n)]
    edges=[(nodes[i],nodes[i+1]) for i in range(n-1)]
    for idx in sorted({max(1,n//5),max(1,2*n//5),max(1,3*n//5),max(1,4*n//5)}):
        edges.append((nodes[min(idx,n-2)],f'{domain}_{token}_B{idx}'))
    for j in range(4):
        edges.append((f'{domain}_{token}_D{j}A',f'{domain}_{token}_D{j}B'))
    if cycle and n>=8: edges.append((nodes[-1],nodes[3]))
    rng.shuffle(edges)
    return {'relation':tuple(edges),'start':nodes[0],'expected':rel_truth(edges,nodes[0]),'domain':domain,'depth':n}

OPEN='Q'; CLOSE='R'
def valid_nested(keys):
    return tuple([(OPEN,k) for k in keys]+[(CLOSE,k) for k in reversed(keys)])
def invalid_cross(keys):
    return tuple([(OPEN,k) for k in keys]+[(CLOSE,k) for k in keys])

def evt_cases(rng,domain,depths):
    rows=[]
    for d in depths:
        keys=[f'{domain}_{rng.randrange(10**14):014d}_{i%max(2,d//5)}' for i in range(d)]
        rows.append({'events':valid_nested(keys),'expected':True,'domain':domain,'depth':d,'kind':'VALID'})
        rows.append({'events':invalid_cross(keys),'expected':False,'domain':domain,'depth':d,'kind':'CROSS'})
        rows.append({'events':tuple([(CLOSE,keys[0])]+list(valid_nested(keys[:max(2,d//2)]))),'expected':False,'domain':domain,'depth':d,'kind':'UNDERFLOW'})
        rows.append({'events':tuple(list(valid_nested(keys))[:-1]),'expected':False,'domain':domain,'depth':d,'kind':'UNFINISHED'})
        wrong=f'{domain}_WRONG_{rng.randrange(10**14):014d}'
        ev=list(valid_nested(keys)); ev[len(keys)]=(CLOSE,wrong)
        rows.append({'events':tuple(ev),'expected':False,'domain':domain,'depth':d,'kind':'WRONG_KEY'})
        k=f'{domain}_REP_{rng.randrange(10**14):014d}'
        rows.append({'events':tuple([(OPEN,k)]*d+[(CLOSE,k)]*d),'expected':True,'domain':domain,'depth':d,'kind':'REPEATED_KEY'})
    rng.shuffle(rows); return rows

seed=int(os.getenv('GITHUB_RUN_ID','260903')) ^ 0xA07C011
rng=random.Random(seed)

selection_tasks=[
  {
    'task_id':'FRESH_TASK_ALPHA',
    'input_contract':'RELATION_START_TO_STATE',
    'cases':[rel_case(rng,n,'ALPHA_REL',cycle=(n%2==1)) for n in [37,39,41,43,45,47]],
  },
  {
    'task_id':'FRESH_TASK_BETA',
    'input_contract':'EVENT_SEQUENCE_TO_BOOLEAN',
    'cases':evt_cases(rng,'BETA_EVT',[43,47,51,55]),
  },
]

followup_tasks=[
  {
    'task_id':'FOLLOWUP_ALPHA',
    'input_contract':'RELATION_START_TO_STATE',
    'cases':[rel_case(rng,n,'OMEGA_REL',cycle=(n%2==0)) for n in [49,51,53,55,57,59]],
  },
  {
    'task_id':'FOLLOWUP_BETA',
    'input_contract':'EVENT_SEQUENCE_TO_BOOLEAN',
    'cases':evt_cases(rng,'OMEGA_EVT',[57,61,65,69]),
  },
]

core=UnifiedYADOCoreV1(REPO)
canonical_before=core.head.get('canonical_head_digest')
controller=YADOAutonomousGenePortfolioControllerV1(REPO)
discovered=controller.discover_shadow_genes()
portfolio=controller.select_portfolio(selection_tasks)
h1=controller.inherit_portfolio(portfolio,'H1')
h2=controller.inherit_portfolio(h1,'H2')

selection_eval={t['task_id']:controller.evaluate_portfolio(portfolio,t) for t in selection_tasks}
followup_eval={t['task_id']:controller.evaluate_portfolio(h2,t) for t in followup_tasks}

# Causal necessity at portfolio level: removing the winner for a task must damage that task.
removal={}
for tid,w in portfolio.get('selected_by_task',{}).items():
    reduced=copy.deepcopy(portfolio)
    reduced['selected_genes']=[x for x in reduced['selected_genes'] if x['gene'].get('gene_digest')!=w.get('gene_digest')]
    task=next(t for t in selection_tasks if t['task_id']==tid)
    removal[tid]=controller.evaluate_portfolio(reduced,task)['best_score']

controller_source=(ROOT/'yado_g2_autonomous_gene_portfolio_controller_v1.py').read_text(encoding='utf-8')
tree=ast.parse(controller_source)
no_synthesis_calls=not any(
    isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='synthesize'
    for n in ast.walk(tree)
)
no_explicit_gene_ids='GENE-SELF-SYNTHESIZED-' not in controller_source

selected_ids=sorted(x['gene']['gene_id'] for x in portfolio.get('selected_genes',[]))
discovered_ids=sorted(x['gene']['gene_id'] for x in discovered)

checks={
  'at_least_two_novel_genes_discovered':len(discovered)>=2,
  'controller_has_no_explicit_gene_ids':no_explicit_gene_ids,
  'controller_makes_no_synthesis_calls':no_synthesis_calls,
  'two_task_winners_selected':len(portfolio.get('selected_by_task',{}))==2,
  'portfolio_contains_two_or_more_selected_genes':portfolio.get('selected_gene_count',0)>=2,
  'selection_tasks_exact':all(v['best_score']==1.0 for v in selection_eval.values()),
  'portfolio_level_removal_causes_drop':all(v<1.0 for v in removal.values()),
  'h1_exact_portfolio_inheritance':all(
      a['gene']['gene_digest']==b['gene']['gene_digest']
      for a,b in zip(portfolio['selected_genes'],h1['selected_genes'])
    ) and len(portfolio['selected_genes'])==len(h1['selected_genes']),
  'h2_exact_portfolio_inheritance':all(
      a['gene']['gene_digest']==b['gene']['gene_digest']
      for a,b in zip(h1['selected_genes'],h2['selected_genes'])
    ) and len(h1['selected_genes'])==len(h2['selected_genes']),
  'followup_tasks_exact_without_resynthesis':all(v['best_score']==1.0 for v in followup_eval.values()) and no_synthesis_calls,
  'automatic_canonical_promotion_false':portfolio.get('automatic_canonical_promotion') is False,
  'formal_generation_unchanged':core.head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
  'frontier_unchanged':core.head.get('current_frontier')=='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1',
  'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_AUTONOMOUS_GENE_PORTFOLIO_SELECTION_V1' if all(checks.values()) else 'WITHHOLD_G2_AUTONOMOUS_GENE_PORTFOLIO_SELECTION_V1'

report={
  'schema':'yado.g2.autonomous_gene_portfolio_selection.v1',
  'status':status,
  'controller':YADOAutonomousGenePortfolioControllerV1.component(),
  'discovered_gene_ids':discovered_ids,
  'selected_gene_ids':selected_ids,
  'selection_tasks':[{k:v for k,v in t.items() if k!='cases'}|{'case_count':len(t['cases'])} for t in selection_tasks],
  'followup_tasks':[{k:v for k,v in t.items() if k!='cases'}|{'case_count':len(t['cases'])} for t in followup_tasks],
  'portfolio':portfolio,
  'h1':h1,'h2':h2,
  'selection_eval':selection_eval,
  'followup_eval':followup_eval,
  'winner_removal_scores':removal,
  'checks':checks,
  'canonical_head_digest_before':canonical_before,
  'canonical_mutation':False,'architecture_mutation':False,
  'generation_transition':False,'g3_genesis_performed':False,
  'semantic_boundary':'BOUNDED SHADOW TEST OF CONTROLLER-DRIVEN GENE DISCOVERY, FRESH FITNESS SELECTION, PORTFOLIO CONSTRUCTION, AND TWO-STEP INHERITANCE WITHOUT GENE-ID-SPECIFIC RULES OR RE-SYNTHESIS. THIS DOES NOT PROVE OPEN-ENDED AUTONOMY OR AUTHORIZE CANONICAL PROMOTION.'
}
report['receipt_sha256']=digest(report)
out=REPO/'candidates/kernel-self-generated/g2-autonomous-gene-portfolio-selection-v1.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

print(json.dumps({
  'status':status,
  'discovered_gene_ids':discovered_ids,
  'selected_gene_ids':selected_ids,
  'selection_eval':selection_eval,
  'followup_eval':followup_eval,
  'winner_removal_scores':removal,
  'checks':checks,
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))

if status!='PASS_SHADOW_G2_AUTONOMOUS_GENE_PORTFOLIO_SELECTION_V1':
    raise SystemExit(2)
