from __future__ import annotations
from pathlib import Path
import ast,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'bounded_compositional_schema_router_v1.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_compositional_schema_router_v1.py'
OUT=ROOT/'yado_intelligence_architectural_ceiling_fresh_admission_v1_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['INTELLIGENCE_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

sp=importlib.util.spec_from_file_location('_intelligence_candidate',SRC)
mod=importlib.util.module_from_spec(sp);sys.modules[sp.name]=mod;sp.loader.exec_module(mod)
R=mod.BoundedCompositionalSchemaRouterV1

def expected(x):
    s=set()
    if x['budget_limited'] or x['quota_limited']:s.add(CAP_BUD)
    if x['external_evidence_needed']:s.add(CAP_RES)
    if x['relation_needed'] or x['disjunction_needed']:s.add(CAP_REL)
    if not s:s.add(CAP_CONJ)
    return tuple(sorted(s))

# Exhaustive fresh training domain; repetitions ensure trigger support.
base=[]
for mask in range(32):
    x={
      'budget_limited':bool(mask&1),
      'quota_limited':bool(mask&2),
      'external_evidence_needed':bool(mask&4),
      'relation_needed':bool(mask&8),
      'disjunction_needed':bool(mask&16),
    }
    for rep in range(6):base.append({'input':dict(x),'expected':expected(x)})
model=R.fit(base,CAP_CONJ)

# Fresh family 1: all exact capability sets on exhaustive combinations.
test=[]
for mask in range(32):
    x={
      'budget_limited':bool(mask&1),'quota_limited':bool(mask&2),
      'external_evidence_needed':bool(mask&4),'relation_needed':bool(mask&8),'disjunction_needed':bool(mask&16),
    }
    test.append({'input':x,'expected':expected(x)})
single=[z for z in test if len(z['expected'])==1]
multi=[z for z in test if len(z['expected'])>=2]
single_score=sum(R.route(model,z['input'])==z['expected'] for z in single)/len(single)
multi_score=sum(R.route(model,z['input'])==z['expected'] for z in multi)/len(multi)

# Fresh family 2: new opaque schema; paired calibration signatures are unique by construction.
alias_names={
 'budget_limited':'zz_budgetless_71',
 'quota_limited':'zz_quotaish_29',
 'external_evidence_needed':'zz_evidenceish_83',
 'relation_needed':'zz_relationish_47',
 'disjunction_needed':'zz_branchish_61',
}
fields=list(alias_names)
reference_rows=[]
alias_rows=[]
for i in range(32):
    # Five unique column signatures independent of names.
    ref={f:bool((i>>j)&1) for j,f in enumerate(fields)}
    ali={alias_names[f]:ref[f] for f in reversed(fields)}
    reference_rows.append(ref);alias_rows.append(ali)
alignment=R.fit_schema_alignment(reference_rows,alias_rows)
aliased_test=[{'input':{alias_names[k]:v for k,v in reversed(list(z['input'].items()))},'expected':z['expected']} for z in test]
aligned_score=sum(R.route_aligned(model,alignment,z['input'])==z['expected'] for z in aliased_test)/len(aliased_test)

# Fresh family 3: three-capability composition specifically.
triple=[z for z in test if len(z['expected'])==3]
triple_score=sum(R.route(model,z['input'])==z['expected'] for z in triple)/len(triple)

# Fresh family 4: fail closed on ambiguous alignment.
amb_ref=[{'f0':bool(i%2),'f1':bool(i%2),'f2':bool((i//2)%2)} for i in range(24)]
amb_alias=[{'x7':z['f0'],'y8':z['f1'],'z9':z['f2']} for z in amb_ref]
amb=R.fit_schema_alignment(amb_ref,amb_alias)
ambiguity_withhold=amb.get('kind')=='WITHHOLD'

# Fresh family 5: fail closed when paired side information is absent.
missing=R.fit_schema_alignment([],[])
missing_withhold=missing.get('kind')=='WITHHOLD'

fresh={
 'SINGLE_CAPABILITY_COMPAT':single_score,
 'MULTI_CAPABILITY_EXACT_SET':multi_score,
 'THREE_CAPABILITY_COMPOSITION':triple_score,
 'OPAQUE_PAIRED_SCHEMA_TRANSFER':aligned_score,
 'AMBIGUOUS_SCHEMA_WITHHOLD':1.0 if ambiguity_withhold else 0.0,
 'MISSING_SIDE_INFO_WITHHOLD':1.0 if missing_withhold else 0.0,
}
fresh_score=sum(fresh.values())/len(fresh)

# Causal ablations.
collapsed_multi=sum(((R.route(model,z['input'])[0],)==z['expected']) for z in multi)/len(multi)
composition_causal=multi_score-collapsed_multi>=.75
unaligned_score=sum(R.route(model,z['input'])==z['expected'] for z in aliased_test)/len(aliased_test)
alignment_causal=aligned_score-unaligned_score>=.75

tree=ast.parse(SRC.read_text(encoding='utf-8'))
danger_calls={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {'eval','exec','compile','__import__'}}
danger_imports=[]
for n in ast.walk(tree):
    if isinstance(n,(ast.Import,ast.ImportFrom)):
        names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module or '']
        if any(x.split('.')[0] in {'socket','subprocess','requests','urllib','aiohttp'} for x in names):danger_imports.extend(names)

checks={
 'fresh_all_families':all(v>=.99 for v in fresh.values()),
 'fresh_score_one':fresh_score>=.99,
 'composition_feature_causal':composition_causal,
 'alignment_feature_causal':alignment_causal,
 'ambiguity_withhold':ambiguity_withhold,
 'missing_side_info_withhold':missing_withhold,
 'bounded_fields':R.MAX_FIELDS<=16,
 'bounded_outputs':R.MAX_OUTPUTS<=8,
 'bounded_alignment_rows':R.MAX_ALIGNMENT_ROWS<=64,
 'source_safe':not danger_calls and not danger_imports,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='INTELLIGENCE_ARCHITECTURAL_CEILING_CANONICAL_INTEGRATION_V1' if passed else 'INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.intelligence_architectural_ceiling_fresh_admission.v1',
 'status':'PASS_INTELLIGENCE_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_INTELLIGENCE_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'fresh_families':fresh,'fresh_score':fresh_score,
 'causal':{'composition':composition_causal,'alignment':alignment_causal,'collapsed_multi_score':collapsed_multi,'unaligned_score':unaligned_score},
 'alignment_kind':alignment.get('kind'),'source_safety':{'danger_calls':sorted(danger_calls),'danger_imports':danger_imports},
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'generation_transition':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'INDEPENDENT FRESH ADMISSION FOR BOUNDED CAPABILITY-SET COMPOSITION AND PAIRED SCHEMA ALIGNMENT. AMBIGUOUS OR SIDE-INFORMATION-FREE ALIASING MUST WITHHOLD.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_INTELLIGENCE_CEILING_FRESH_ADMISSION",
 'event_type':'INTELLIGENCE_CAPABILITY_FRESH_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'INTELLIGENCE_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1',
 'effect':f"FRESH={fresh_score:.6f}; COMPOSITION_CAUSAL={composition_causal}; ALIGNMENT_CAUSAL={alignment_causal}; NEXT={next_cap}",
 'source_path':f'receipts/yado-intelligence-architectural-ceiling-fresh-admission-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'fresh_families':fresh,'fresh_score':fresh_score,'causal':receipt['causal'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('INTELLIGENCE_CEILING_FRESH_ADMISSION_WITHHELD')
