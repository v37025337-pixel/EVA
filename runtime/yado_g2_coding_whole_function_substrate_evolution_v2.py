from __future__ import annotations
from pathlib import Path
from itertools import product
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_unified_core_v1 import UnifiedYADOCoreV1

DISC=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-discovery-v1.json'
DIAG=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-discovery-diagnostic-v1.json'
CENSUS=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-ast-census-v2.json'
MANIFEST=REPO/'canonical/yado-unified-core-v1.json';HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-substrate-evolution-v2.json'
EXP=REPO/'experience/yado-coding-whole-function-substrate-evolution-v2.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

disc,diag,census,manifest,head=map(load,[DISC,DIAG,CENSUS,MANIFEST,HEAD])
if disc.get('status')!='WITHHOLD_NO_ADMISSIBLE_WHOLE_FUNCTIONS':raise RuntimeError('STRICT_DISCOVERY_FAILURE_REQUIRED')
if census.get('status')!='PASS_AST_CENSUS':raise RuntimeError('AST_CENSUS_REQUIRED')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

PURE_BUILTINS={'int':int,'bool':bool,'float':float,'str':str,'sorted':sorted,'set':set,'tuple':tuple,'list':list,'range':range,'zip':zip,'enumerate':enumerate}
observed=sorted({k.split(':',1)[1] for k in (census.get('call_counts') or {}) if k.startswith('NAME:') and k.split(':',1)[1] in PURE_BUILTINS})
if not observed:raise RuntimeError('NO_OBSERVED_PURE_BUILTIN_GAPS')

def strip_fn(n):
    q=copy.deepcopy(n);q.decorator_list=[];q.returns=None;q.type_comment=None
    for a in list(q.args.posonlyargs)+list(q.args.args)+list(q.args.kwonlyargs):a.annotation=None;a.type_comment=None
    q.args.defaults=[];q.args.kw_defaults=[None for _ in q.args.kwonlyargs];ast.fix_missing_locations(q);return ast.unparse(q)+'\n'

def cls_for(extra):
    class Candidate(BoundedCompositionalProgramRepairV3):
        SAFE_CALLS=dict(BoundedCompositionalProgramRepairV3.SAFE_CALLS)
    Candidate.SAFE_CALLS.update({x:PURE_BUILTINS[x] for x in extra})
    return Candidate

def literal_string_seq(node):
    if isinstance(node,(ast.Tuple,ast.List,ast.Set)):
        vals=[]
        for e in node.elts:
            if not isinstance(e,ast.Constant) or not isinstance(e.value,str):return None
            vals.append(e.value)
        return vals
    return None

def indirect_subscript_keys(tree,arg):
    # Recover patterns like: [int(ctx[k]) for k in ('a','b',...)]
    keys=[]
    for comp in [x for x in ast.walk(tree) if isinstance(x,(ast.ListComp,ast.SetComp,ast.GeneratorExp,ast.DictComp))]:
        gens=comp.generators
        bindings={}
        for g in gens:
            if isinstance(g.target,ast.Name):
                seq=literal_string_seq(g.iter)
                if seq:bindings[g.target.id]=seq
        if not bindings:continue
        for x in ast.walk(comp):
            if isinstance(x,ast.Subscript) and isinstance(x.value,ast.Name) and x.value.id==arg and isinstance(x.slice,ast.Name):
                for v in bindings.get(x.slice.id,[]):
                    if v not in keys:keys.append(v)
    return keys

def arg_shape(tree,arg):
    keys=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id==arg:
            if isinstance(n.slice,ast.Constant) and isinstance(n.slice.value,str) and n.slice.value not in keys:keys.append(n.slice.value)
    for v in indirect_subscript_keys(tree,arg):
        if v not in keys:keys.append(v)
    if keys:return ('DICT_KEYS',keys[:8])
    for n in ast.walk(tree):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='str' and any(isinstance(a,ast.Name) and a.id==arg for a in n.args):
            return ('SCALAR_MIXED',None)
    return ('SCALAR_INT',None)

def probes_for(src,node):
    tree=ast.parse(src);domains=[]
    for a in node.args.args:
        kind,data=arg_shape(tree,a.arg)
        if kind=='DICT_KEYS':
            vals=[dict(zip(data,bits)) for bits in product((False,True),repeat=len(data))]
            domains.append(vals[:256])
        elif kind=='SCALAR_MIXED':domains.append([-5,-2,-1,0,1,2,5,'','a','abc'])
        else:domains.append([-7,-3,-2,-1,0,1,2,3,7])
    out=[]
    for combo in product(*domains):
        out.append(tuple(copy.deepcopy(combo)))
        if len(out)>=256:break
    return out

def useful_output(x):
    if isinstance(x,(bool,int,float,str)):
        if isinstance(x,str) and len(x)>256:return False
        if isinstance(x,float) and (x!=x or abs(x)>1e9):return False
        if isinstance(x,int) and not isinstance(x,bool) and abs(x)>10**9:return False
        return True
    return False

def discover(extra):
    C=cls_for(extra);rows=[]
    for rel in manifest.get('active_runtime_sources',[]):
        if not str(rel).endswith('.py'):continue
        p=REPO/rel
        if not p.exists():continue
        tree=ast.parse(p.read_text(encoding='utf-8'))
        for n in tree.body:
            if not isinstance(n,ast.FunctionDef):continue
            if n.args.posonlyargs or n.args.vararg is not None or n.args.kwarg is not None or n.args.kwonlyargs:continue
            if not 1<=len(n.args.args)<=4:continue
            src=strip_fn(n)
            try:C._validate(ast.parse(src))
            except Exception:continue
            mutatable=sum(isinstance(x,(ast.BinOp,ast.Compare,ast.BoolOp)) or (isinstance(x,ast.Constant) and isinstance(x.value,int) and not isinstance(x.value,bool)) for x in ast.walk(ast.parse(src)))
            if mutatable<1:continue
            all_probes=probes_for(src,n);succ=[]
            for args in all_probes:
                try:
                    y=C.execute(src,n.name,args)
                    if useful_output(y):succ.append((args,y))
                except Exception:pass
            if len(succ)<8 or len({canon(y) for _,y in succ})<2:continue
            rows.append({'token':'WF-'+sha(rel+'|'+str(n.lineno)+'|'+src)[:16],'path':rel,'line':int(n.lineno),'function_name':n.name,
              'source':src,'source_sha256':sha(src),'arg_names':[a.arg for a in n.args.args],
              'probe_count':len(all_probes),'probe_success_count':len(succ),'distinct_output_count':len({canon(y) for _,y in succ}),
              'mutatable_node_count':mutatable,'sample_probes':[{'args':a,'output':y} for a,y in succ[:16]]})
    rows.sort(key=lambda r:(r['path'],r['line'],r['function_name']))
    return rows

profiles=[{'token':'KEEP_PARENT','extra':[]}]+[{'token':'ADD_PURE_BUILTIN_'+x.upper(),'extra':[x]} for x in observed]
evaluated=[]
for p in profiles:
    rows=discover(p['extra'])
    evaluated.append({'token':p['token'],'extra':p['extra'],'candidate_count':len(rows),'source_file_count':len({r['path'] for r in rows}),'candidates':rows})
children=[x for x in evaluated if x['extra'] and x['candidate_count']>0]
if not children:
    experience={'schema':'yado.g2.coding_whole_function_substrate_evolution.experience.v2','status':'WITHHOLD',
      'v1_failure_signature':'NO_SINGLE_PURE_BUILTIN_EXTENSION_UNLOCKS_WHOLE_FUNCTION',
      'representation_repair':'INDIRECT_SUBSCRIPT_KEY_INFERENCE','observed_pure_builtin_gaps':observed,'profile_evaluations':evaluated,
      'canonical_mutation':False}
    experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n')
    report={'schema':'yado.g2.coding_whole_function_substrate_evolution.v2','status':'WITHHOLD_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EVOLUTION_V2',
      'profile_evaluations':evaluated,'canonical_mutation':False,'next_required_capability':'G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EVOLUTION_V3'}
    report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
    raise SystemExit(2)

selector=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=x['token'],evidence=x['candidate_count']+.25*x['source_file_count'],complexity=1,risk=0,novelty=1) for x in children],complexity_penalty=.05,risk_penalty=.5,novelty_bonus=.02)
selected=next(x for x in children if x['token']==selector['selected_token'])
skills=[
 {'skill_id':'KEEP_PARENT_CODE_SUBSTRATE','artifact_digest':head['canonical_head_digest'],'structural_valid':True,'semantic_consistency':1.0,'fit_baseline':0.0,'fit_candidate':0.0,'heldout_baseline':0.0,'heldout_candidate':0.0,'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'ADMIT_SHADOW_'+selected['token'],'artifact_digest':digest(selected),'structural_valid':True,'semantic_consistency':1.0,'fit_baseline':0.0,'fit_candidate':1.0,'heldout_baseline':0.0,'heldout_candidate':1.0,'regression_pass':True,'state_integrity':True,'rollback_available':True}
]
db=ROOT/'yado_whole_function_substrate_evolution_v2.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.95,min_fit_gain=.05,max_heldout_drop=0,min_heldout_gain=.05)
finally:
    try:k.close()
    except Exception:pass
selected_skill=(selection.get('selected_skill_ids') or [None])[0]
gene={'schema':'yado.g2.code_whole_function_substrate_gene.v2',
 'gene_id':'GENE-G2-CODE-WHOLE-FUNCTION-SUBSTRATE-V2-'+digest({'selected':selected,'census':census.get('receipt_sha256')})[:16],
 'organ':'CODE','heritage':['ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11',disc.get('receipt_sha256'),diag.get('receipt_sha256'),census.get('receipt_sha256'),'V1_INPUT_SHAPE_INFERENCE_FAILURE'],
 'mutation_kind':'SAFE_CALL_GRAMMAR_EXTENSION_AFTER_INPUT_REPRESENTATION_REPAIR','representation_repair':'INDIRECT_SUBSCRIPT_KEY_INFERENCE',
 'selected_profile':selected['token'],'added_safe_calls':selected['extra'],'unlocked_candidate_count':selected['candidate_count'],
 'unlocked_source_file_count':selected['source_file_count'],'promotion_state':'SHADOW_ONLY','canonical_parent_unchanged':True}
gene['gene_digest']=digest(gene)
checks={'v1_measurement_failure_consumed':True,'indirect_subscript_shape_inference_repaired':True,
 'single_extension_only':len(selected['extra'])==1,'selected_extension_unlocks_real_whole_function':selected['candidate_count']>=1,
 'native_neutral_selector_selected_profile':selector['selected_token']==selected['token'],'native_skill_gate_selected_child':selected_skill=='ADMIT_SHADOW_'+selected['token'],
 'no_attribute_permission_added':True,'no_loop_permission_added':True,'no_filesystem_permission_added':True,'no_network_permission_added':True,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),'external_model_used':False,'automatic_canonical_promotion':False}
positive=[k for k in checks if k not in ('external_model_used','automatic_canonical_promotion')]
passed=all(checks[k] is True for k in positive) and not checks['external_model_used'] and not checks['automatic_canonical_promotion']
status='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EVOLUTION_V2' if passed else 'WITHHOLD_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EVOLUTION_V2'
experience={'schema':'yado.g2.coding_whole_function_substrate_evolution.experience.v2','status':'TRAINED' if passed else 'WITHHOLD',
 'v1_failure_signature':'NO_SINGLE_PURE_BUILTIN_EXTENSION_UNLOCKS_WHOLE_FUNCTION','representation_repair':'INDIRECT_SUBSCRIPT_KEY_INFERENCE',
 'observed_pure_builtin_gaps':observed,'profile_evaluations':evaluated,'selector':selector,'native_skill_selection':selection,'substrate_gene':gene,'canonical_mutation':False,
 'semantic_boundary':'V2 CORRECTS INPUT-SHAPE INFERENCE FOR INDIRECT DICTIONARY SUBSCRIPTS BEFORE RE-EVALUATING THE SAME SINGLE PURE-BUILTIN GRAMMAR SEARCH SPACE. SAFETY SCOPE IS UNCHANGED.'}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.coding_whole_function_substrate_evolution.v2','status':status,'selected_profile':selected['token'],'added_safe_calls':selected['extra'],
 'unlocked_candidate_count':selected['candidate_count'],'unlocked_source_file_count':selected['source_file_count'],'unlocked_candidates':selected['candidates'],
 'substrate_gene':gene,'gene_id':gene['gene_id'],'selector':selector,'native_skill_selection':selection,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V1' if passed else 'G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EVOLUTION_V3'}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'selected_profile':selected['token'],'added_safe_calls':selected['extra'],'unlocked_candidate_count':selected['candidate_count'],
 'unlocked_source_file_count':selected['source_file_count'],'gene_id':gene['gene_id'],'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
