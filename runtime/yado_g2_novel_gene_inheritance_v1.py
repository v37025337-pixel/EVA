from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1

SOURCE=REPO/'candidates/kernel-self-generated/g2-blind-novel-mechanism-invention-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()

def truth(relation,start):
    state={start}
    for _ in range(256):
        nxt=state|{b for a,b in relation if a in state}
        if nxt==state: break
        state=nxt
    return tuple(sorted(state,key=lambda x:(str(type(x)),str(x))))

def case(rng,n,domain,cycle=False):
    token=''.join(rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(7))
    nodes=[f'{domain}_{token}_{i}' for i in range(n)]
    edges=[(nodes[i],nodes[i+1]) for i in range(n-1)]
    # Reachable side branches at several depths.
    for idx in sorted({max(1,n//4),max(1,n//2),max(1,(3*n)//4)}):
        b=f'{domain}_{token}_B{idx}'
        edges.append((nodes[min(idx,n-2)],b))
    # Disconnected decoys prevent domain/length shortcuts.
    for j in range(3):
        d0=f'{domain}_{token}_D{j}A'; d1=f'{domain}_{token}_D{j}B'
        edges.append((d0,d1))
    if cycle and n>=6:
        edges.append((nodes[-1],nodes[2]))
    rng.shuffle(edges)
    return {'relation':tuple(edges),'start':nodes[0],'expected':truth(edges,nodes[0]),'domain':domain,'node_count':n}

def accuracy(program,cases):
    if not program: return 0.0
    ok=0
    for x in cases:
        try:
            got=GenericRelationalMetaLanguageV1.execute(program,x['relation'],x['start'])
        except Exception:
            got=None
        ok += (got==x['expected'])
    return ok/len(cases)

def inherited_genome(source_gene,label,parent_genome_digest):
    # Generic inheritance only: the executable gene is copied byte-for-byte as data.
    gene=copy.deepcopy(source_gene)
    wrapper={
      'schema':'yado.g2.shadow_inherited_novel_gene_genome.v1',
      'shadow_generation':label,
      'lineage_parent_genome_digest':parent_genome_digest,
      'inherited_gene':gene,
      'inherited_gene_id':gene.get('gene_id'),
      'inherited_gene_digest':gene.get('gene_digest'),
      'inheritance_mode':'EXACT_SHADOW_GENE_COPY',
      'promotion_state':'SHADOW_ONLY',
    }
    wrapper['genome_digest']=digest(wrapper)
    return wrapper

if not SOURCE.exists():
    raise RuntimeError('BLIND_NOVEL_MECHANISM_EVIDENCE_MISSING')
source=json.loads(SOURCE.read_text(encoding='utf-8'))
if source.get('status')!='PASS_SHADOW_G2_BLIND_NOVEL_MECHANISM_INVENTION_V1':
    raise RuntimeError('SOURCE_BLIND_EVIDENCE_NOT_PASS')
gene=copy.deepcopy(source.get('invented',{}).get('gene',{}))
if gene.get('novel_gene') is not True or gene.get('promotion_state')!='SHADOW_ONLY':
    raise RuntimeError('SOURCE_GENE_NOT_VALID_SHADOW_NOVEL_GENE')
program=copy.deepcopy(gene.get('operator_program',{}))
if not program:
    raise RuntimeError('SOURCE_GENE_PROGRAM_MISSING')

core=UnifiedYADOCoreV1(REPO)
canonical_before=core.head.get('canonical_head_digest')
active=set(core.head.get('active_capabilities',[]))

# Entirely fresh inheritance-only cases. No training examples from the invention run are reused.
seed=int(os.getenv('GITHUB_RUN_ID','260903')) ^ 0x1A17E21
rng=random.Random(seed)
h1_specs=[('SUPPLYCHAIN',13),('OWNERSHIP',14),('EVENTFLOW',15),('ROUTING',16),('DEPENDENCY2',17),('CAUSAL2',18)]
h2_specs=[('PROVENANCE',19),('GENEALOGY2',20),('PIPELINE2',21),('AUTHZFLOW',22),('WORKGRAPH',23),('STATEFLOW',24)]
h1_cases=[case(rng,n,d,cycle=(n%2==0)) for d,n in h1_specs]
h2_cases=[case(rng,n,d,cycle=(n%2==1)) for d,n in h2_specs]

# H1 inherits the exact invented gene; H2 inherits the exact same gene from H1.
h1=inherited_genome(gene,'H1',source.get('receipt_sha256'))
h2=inherited_genome(h1['inherited_gene'],'H2',h1['genome_digest'])

h1_score=accuracy(h1['inherited_gene']['operator_program'],h1_cases)
h2_score=accuracy(h2['inherited_gene']['operator_program'],h2_cases)

# Causal controls: structural ablations and bounded shallow alternatives must not match the inherited gene.
ablations=[]
for a in GenericRelationalMetaLanguageV1.ablations(program):
    s1=accuracy(a['program'],h1_cases); s2=accuracy(a['program'],h2_cases)
    ablations.append({'field':a['ablated_field'],'value':a['ablated_value'],'h1_accuracy':s1,'h2_accuracy':s2,'program_digest':a['program']['program_digest']})
best_ablation=max([max(x['h1_accuracy'],x['h2_accuracy']) for x in ablations],default=0.0)
shallow=[]
for mode in ('ONCE','TWICE','THRICE'):
    p={'seed':'START','direction':'FORWARD','merge':'UNION','iteration':mode,'output':'STATE'}
    shallow.append({'iteration':mode,'h1_accuracy':accuracy(p,h1_cases),'h2_accuracy':accuracy(p,h2_cases)})

# Static harness check: inheritance test must not call the synthesis routine again.
self_text=Path(__file__).read_text(encoding='utf-8')
no_resynthesis_call='.synthesize(' not in self_text

checks={
  'source_blind_pass':source.get('status')=='PASS_SHADOW_G2_BLIND_NOVEL_MECHANISM_INVENTION_V1',
  'source_gene_shadow_only':gene.get('promotion_state')=='SHADOW_ONLY',
  'source_gene_not_canonical_active':gene.get('gene_id') not in active,
  'h1_exact_gene_digest_inherited':h1.get('inherited_gene_digest')==gene.get('gene_digest') and h1['inherited_gene'].get('gene_digest')==gene.get('gene_digest'),
  'h2_exact_gene_digest_inherited':h2.get('inherited_gene_digest')==gene.get('gene_digest') and h2['inherited_gene'].get('gene_digest')==gene.get('gene_digest'),
  'h2_parent_is_h1':h2.get('lineage_parent_genome_digest')==h1.get('genome_digest'),
  'h1_fresh_exact':h1_score==1.0,
  'h2_fresh_exact':h2_score==1.0,
  'fresh_depth_exceeds_original_holdout':min(x['node_count'] for x in h1_cases)>12 and min(x['node_count'] for x in h2_cases)>18,
  'fresh_domains_new':set(x['domain'] for x in h1_cases+h2_cases).isdisjoint(set(source.get('blind_deficit',{}).get('transfer_domains',[]))),
  'structural_ablation_causes_drop':best_ablation<1.0,
  'shallow_alternatives_fail':all(x['h1_accuracy']<1.0 and x['h2_accuracy']<1.0 for x in shallow),
  'no_operator_resynthesis_call':no_resynthesis_call,
  'gene_survives_additional_shadow_generation':h2_score==1.0 and h2['inherited_gene'].get('gene_digest')==gene.get('gene_digest'),
  'formal_generation_unchanged':core.head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
  'frontier_unchanged':core.head.get('current_frontier')=='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1',
  'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_NOVEL_GENE_INHERITANCE_V1' if all(checks.values()) else 'WITHHOLD_G2_NOVEL_GENE_INHERITANCE_V1'
report={
  'schema':'yado.g2.novel_gene_inheritance.v1',
  'status':status,
  'source_gene_id':gene.get('gene_id'),
  'source_gene_digest':gene.get('gene_digest'),
  'source_blind_receipt_sha256':source.get('receipt_sha256'),
  'inheritance_lineage':[h1,h2],
  'fitness':{
    'h1_fresh_accuracy':h1_score,
    'h2_fresh_accuracy':h2_score,
    'best_structural_ablation_accuracy':best_ablation,
    'shallow_baselines':shallow,
  },
  'fresh_cases':{
    'h1_case_count':len(h1_cases),'h2_case_count':len(h2_cases),
    'h1_node_range':[min(x['node_count'] for x in h1_cases),max(x['node_count'] for x in h1_cases)],
    'h2_node_range':[min(x['node_count'] for x in h2_cases),max(x['node_count'] for x in h2_cases)],
    'h1_domains':[x['domain'] for x in h1_cases],
    'h2_domains':[x['domain'] for x in h2_cases],
  },
  'ablations':ablations,
  'checks':checks,
  'canonical_head_digest_before':canonical_before,
  'canonical_mutation':False,
  'architecture_mutation':False,
  'generation_transition':False,
  'g3_genesis_performed':False,
  'semantic_boundary':'BOUNDED SHADOW INHERITANCE TEST. A PREVIOUSLY SELF-SYNTHESIZED NOVEL GENE IS COPIED WITHOUT RE-SYNTHESIS THROUGH H1 AND H2 AND MUST RETAIN CAUSAL FRESH PERFORMANCE. THIS DOES NOT PROMOTE THE GENE OR PROVE OPEN-ENDED SELF-EVOLUTION.'
}
report['receipt_sha256']=digest(report)
out=REPO/'candidates/kernel-self-generated/g2-novel-gene-inheritance-v1.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
  'status':status,
  'source_gene_id':gene.get('gene_id'),
  'h1_fresh_accuracy':h1_score,
  'h2_fresh_accuracy':h2_score,
  'best_structural_ablation_accuracy':best_ablation,
  'checks':checks,
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if status!='PASS_SHADOW_G2_NOVEL_GENE_INHERITANCE_V1':
    raise SystemExit(2)
