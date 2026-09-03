from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_generic_event_state_meta_language_v1 import GenericEventStateMetaLanguageV1

SOURCE=REPO/'candidates/kernel-self-generated/g2-second-blind-novel-mechanism-invention-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()

OPEN='Q'; CLOSE='R'

def valid_nested(keys):
    ev=[]
    for k in keys: ev.append((OPEN,k))
    for k in reversed(keys): ev.append((CLOSE,k))
    return tuple(ev)

def invalid_cross(keys):
    ev=[]
    for k in keys: ev.append((OPEN,k))
    for k in keys: ev.append((CLOSE,k))
    return tuple(ev)

def make_examples(rng,domain,depths):
    rows=[]
    for depth in depths:
        keys=[f'{domain}_{rng.randrange(10**12):012d}_{i%max(2,depth//4)}' for i in range(depth)]
        rows.append({'events':valid_nested(keys),'expected':True,'domain':domain,'depth':depth,'kind':'VALID'})
        rows.append({'events':invalid_cross(keys),'expected':False,'domain':domain,'depth':depth,'kind':'CROSS'})
        rows.append({'events':tuple([(CLOSE,keys[0])]+list(valid_nested(keys[:max(2,depth//2)]))),'expected':False,'domain':domain,'depth':depth,'kind':'UNDERFLOW'})
        rows.append({'events':tuple(list(valid_nested(keys))[:-1]),'expected':False,'domain':domain,'depth':depth,'kind':'UNFINISHED'})
        wrong=f'{domain}_WRONG_{rng.randrange(10**12):012d}'
        ev=list(valid_nested(keys)); ev[len(keys)]=(CLOSE,wrong)
        rows.append({'events':tuple(ev),'expected':False,'domain':domain,'depth':depth,'kind':'WRONG_KEY'})
        k=f'{domain}_REP_{rng.randrange(10**12):012d}'
        rep=tuple([(OPEN,k)]*depth+[(CLOSE,k)]*depth)
        rows.append({'events':rep,'expected':True,'domain':domain,'depth':depth,'kind':'REPEATED_KEY'})
    rng.shuffle(rows)
    return rows

def accuracy(program,cases):
    if not program: return 0.0
    ok=0
    for x in cases:
        try: got=GenericEventStateMetaLanguageV1.execute(program,x['events'])
        except Exception: got=None
        ok += (got is bool(x['expected']))
    return ok/len(cases)

def inherit_gene(source_gene,label,parent_digest):
    gene=copy.deepcopy(source_gene)
    wrapper={
      'schema':'yado.g2.shadow_inherited_event_state_gene_genome.v1',
      'shadow_generation':label,
      'lineage_parent_genome_digest':parent_digest,
      'inherited_gene':gene,
      'inherited_gene_id':gene.get('gene_id'),
      'inherited_gene_digest':gene.get('gene_digest'),
      'inheritance_mode':'EXACT_SHADOW_GENE_COPY',
      'promotion_state':'SHADOW_ONLY',
    }
    wrapper['genome_digest']=digest(wrapper)
    return wrapper

if not SOURCE.exists():
    raise RuntimeError('SECOND_BLIND_NOVEL_MECHANISM_EVIDENCE_MISSING')
source=json.loads(SOURCE.read_text(encoding='utf-8'))
if source.get('status')!='PASS_SHADOW_G2_SECOND_BLIND_NOVEL_MECHANISM_INVENTION_V1':
    raise RuntimeError('SECOND_BLIND_EVIDENCE_NOT_PASS')

gene=copy.deepcopy(source.get('invented',{}).get('gene',{}))
if gene.get('novel_gene') is not True or gene.get('promotion_state')!='SHADOW_ONLY':
    raise RuntimeError('SECOND_GENE_NOT_VALID_SHADOW_NOVEL_GENE')
program=copy.deepcopy(gene.get('operator_program',{}))
if not program:
    raise RuntimeError('SECOND_GENE_PROGRAM_MISSING')

core=UnifiedYADOCoreV1(REPO)
active=set(core.head.get('active_capabilities',[]))
canonical_before=core.head.get('canonical_head_digest')

seed=int(os.getenv('GITHUB_RUN_ID','260903')) ^ 0x2E17E2
rng=random.Random(seed)

h1=[]
for dom,depths in [
    ('SESSIONFLOW',[19,21]),('LEASEFLOW',[23]),('BRACKETFLOW',[25]),
    ('SCOPECHAIN',[27]),('RESOURCECHAIN',[29])
]:
    h1.extend(make_examples(rng,dom,depths))

h2=[]
for dom,depths in [
    ('TRANSACTION2',[31]),('LOCKTREE',[33]),('CALLTREE',[35]),
    ('OWNERSHIP2',[37]),('NESTFLOW',[39]),('EVENTSTACK',[41])
]:
    h2.extend(make_examples(rng,dom,depths))

h1_genome=inherit_gene(gene,'H1',source.get('receipt_sha256'))
h2_genome=inherit_gene(h1_genome['inherited_gene'],'H2',h1_genome['genome_digest'])

h1_score=accuracy(h1_genome['inherited_gene']['operator_program'],h1)
h2_score=accuracy(h2_genome['inherited_gene']['operator_program'],h2)

ablations=[]
for a in GenericEventStateMetaLanguageV1.ablations(program):
    s1=accuracy(a['program'],h1); s2=accuracy(a['program'],h2)
    ablations.append({'field':a['ablated_field'],'value':a['ablated_value'],'h1_accuracy':s1,'h2_accuracy':s2,'program_digest':a['program']['program_digest']})
best_ablation=max([max(x['h1_accuracy'],x['h2_accuracy']) for x in ablations],default=0.0)

count_program={'open_code':OPEN,'close_code':CLOSE,'state_mode':'COUNT','close_policy':'ANY','underflow_policy':'REJECT','mismatch_policy':'REJECT','final_policy':'EMPTY_AND_VALID'}
set_program={'open_code':OPEN,'close_code':CLOSE,'state_mode':'SET','close_policy':'REMOVE_KEY','underflow_policy':'REJECT','mismatch_policy':'REJECT','final_policy':'EMPTY_AND_VALID'}
baselines={
  'COUNT':{'h1':accuracy(count_program,h1),'h2':accuracy(count_program,h2)},
  'SET':{'h1':accuracy(set_program,h1),'h2':accuracy(set_program,h2)},
}

self_tree=ast.parse(Path(__file__).read_text(encoding='utf-8'))
no_resynthesis_call=not any(
    isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='synthesize'
    for n in ast.walk(self_tree)
)

checks={
  'source_second_blind_pass':source.get('status')=='PASS_SHADOW_G2_SECOND_BLIND_NOVEL_MECHANISM_INVENTION_V1',
  'source_gene_shadow_only':gene.get('promotion_state')=='SHADOW_ONLY',
  'source_gene_not_canonical_active':gene.get('gene_id') not in active,
  'h1_exact_gene_digest_inherited':h1_genome.get('inherited_gene_digest')==gene.get('gene_digest') and h1_genome['inherited_gene'].get('gene_digest')==gene.get('gene_digest'),
  'h2_exact_gene_digest_inherited':h2_genome.get('inherited_gene_digest')==gene.get('gene_digest') and h2_genome['inherited_gene'].get('gene_digest')==gene.get('gene_digest'),
  'h2_parent_is_h1':h2_genome.get('lineage_parent_genome_digest')==h1_genome.get('genome_digest'),
  'h1_fresh_exact':h1_score==1.0,
  'h2_fresh_exact':h2_score==1.0,
  'fresh_depth_exceeds_invention_transfer':min(x['depth'] for x in h1)>18 and min(x['depth'] for x in h2)>30,
  'fresh_domains_new':set(x['domain'] for x in h1+h2).isdisjoint(set(source.get('blind_deficit',{}).get('transfer_domains',[]))),
  'structural_ablation_causes_drop':best_ablation<1.0,
  'count_and_set_baselines_fail':all(v['h1']<1.0 and v['h2']<1.0 for v in baselines.values()),
  'no_operator_resynthesis_call':no_resynthesis_call,
  'gene_survives_additional_shadow_generation':h2_score==1.0 and h2_genome['inherited_gene'].get('gene_digest')==gene.get('gene_digest'),
  'formal_generation_unchanged':core.head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
  'frontier_unchanged':core.head.get('current_frontier')=='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1',
  'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_SECOND_NOVEL_GENE_INHERITANCE_V1' if all(checks.values()) else 'WITHHOLD_G2_SECOND_NOVEL_GENE_INHERITANCE_V1'

report={
  'schema':'yado.g2.second_novel_gene_inheritance.v1',
  'status':status,
  'source_gene_id':gene.get('gene_id'),
  'source_gene_digest':gene.get('gene_digest'),
  'source_second_blind_receipt_sha256':source.get('receipt_sha256'),
  'inheritance_lineage':[h1_genome,h2_genome],
  'fitness':{
    'h1_fresh_accuracy':h1_score,
    'h2_fresh_accuracy':h2_score,
    'best_structural_ablation_accuracy':best_ablation,
    'baselines':baselines,
  },
  'fresh_cases':{
    'h1_case_count':len(h1),'h2_case_count':len(h2),
    'h1_depth_range':[min(x['depth'] for x in h1),max(x['depth'] for x in h1)],
    'h2_depth_range':[min(x['depth'] for x in h2),max(x['depth'] for x in h2)],
    'h1_domains':sorted({x['domain'] for x in h1}),
    'h2_domains':sorted({x['domain'] for x in h2}),
  },
  'ablations':ablations,
  'checks':checks,
  'canonical_head_digest_before':canonical_before,
  'canonical_mutation':False,
  'architecture_mutation':False,
  'generation_transition':False,
  'g3_genesis_performed':False,
  'semantic_boundary':'BOUNDED SHADOW INHERITANCE TEST FOR THE SECOND, EVENT-STATE SELF-SYNTHESIZED GENE. THE EXACT GENE IS COPIED THROUGH H1 AND H2 WITHOUT RE-SYNTHESIS AND MUST RETAIN FRESH CAUSAL PERFORMANCE. THIS DOES NOT PROMOTE THE GENE OR PROVE OPEN-ENDED SELF-EVOLUTION.'
}
report['receipt_sha256']=digest(report)

out=REPO/'candidates/kernel-self-generated/g2-second-novel-gene-inheritance-v1.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

print(json.dumps({
  'status':status,
  'source_gene_id':gene.get('gene_id'),
  'h1_fresh_accuracy':h1_score,
  'h2_fresh_accuracy':h2_score,
  'best_structural_ablation_accuracy':best_ablation,
  'baselines':baselines,
  'checks':checks,
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))

if status!='PASS_SHADOW_G2_SECOND_NOVEL_GENE_INHERITANCE_V1':
    raise SystemExit(2)
