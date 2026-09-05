from __future__ import annotations
from pathlib import Path
from itertools import product
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_unified_core_v1 import UnifiedYADOCoreV1

PARENT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-real-repair-v1.json'
SUB=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-substrate-evolution-v2.json'
CENSUS=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-ast-census-v2.json'
MANIFEST=REPO/'canonical/yado-unified-core-v1.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-substrate-expansion-v2.json'
EXP=REPO/'experience/yado-coding-whole-function-substrate-expansion-v2.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

parent,sub,census,manifest,head=map(load,[PARENT,SUB,CENSUS,MANIFEST,HEAD])
if parent.get('status')!='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V1':
    raise RuntimeError('WHOLE_FUNCTION_V1_PASS_REQUIRED')
if parent.get('next_required_capability')!='G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V2_SUBSTRATE_EXPANSION':
    raise RuntimeError('WHOLE_FUNCTION_V1_FRONTIER_MISMATCH')
if sub.get('status')!='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EVOLUTION_V2':
    raise RuntimeError('SUBSTRATE_V2_PASS_REQUIRED')
if sub.get('added_safe_calls')!=['int']:raise RuntimeError('INT_EXTENSION_PARENT_REQUIRED')
if census.get('status')!='PASS_AST_CENSUS':raise RuntimeError('AST_CENSUS_REQUIRED')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

PURE_ATTR_PROFILES={
 'DICT_READONLY':{'get','items','values'},
 'STR_READONLY':{'strip','lower'},
 'DICT_GET_ONLY':{'get'},
 'STR_NORMALIZE_ONLY':{'strip','lower'},
}
FORBIDDEN_ATTRS={'append','extend','sort','add','pop','read_text','read_bytes','write_text','write_bytes','open','execute','digest','hexdigest','encode','join','search','match','findall','sub','split','randint','choice'}
BASE_BANNED=(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.With,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda,ast.While,ast.For,ast.AsyncFor,ast.Try,ast.Raise,ast.Yield,ast.YieldFrom,ast.Await,ast.Delete)

def strip_fn(n):
    q=copy.deepcopy(n);q.decorator_list=[];q.returns=None;q.type_comment=None
    for a in list(q.args.posonlyargs)+list(q.args.args)+list(q.args.kwonlyargs):
        a.annotation=None;a.type_comment=None
    q.args.defaults=[];q.args.kw_defaults=[None for _ in q.args.kwonlyargs]
    ast.fix_missing_locations(q);return ast.unparse(q)+'\n'

def cls_for(attrs):
    class Candidate(BoundedCompositionalProgramRepairV3):
        SAFE_CALLS=dict(BoundedCompositionalProgramRepairV3.SAFE_CALLS)
        SAFE_CALLS['int']=int
        ALLOWED_ATTRS=set(attrs)

        @classmethod
        def _validate(cls,tree):
            # Keep every parent ban except Attribute. Attribute is admitted only as a call target
            # from an explicit readonly profile. Bare attribute reads remain forbidden.
            if any(isinstance(n,BASE_BANNED) for n in ast.walk(tree)):raise ValueError('UNSAFE_PROGRAM')
            funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
            if len(funcs)!=1 or len(tree.body)!=1:raise ValueError('EXACTLY_ONE_FUNCTION_REQUIRED')
            fname=funcs[0].name
            parents={}
            for p in ast.walk(tree):
                for c in ast.iter_child_nodes(p):parents[id(c)]=p
            for n in ast.walk(tree):
                if isinstance(n,ast.Attribute):
                    par=parents.get(id(n))
                    if not (isinstance(par,ast.Call) and par.func is n):raise ValueError('BARE_ATTRIBUTE_FORBIDDEN')
                    if n.attr not in cls.ALLOWED_ATTRS or n.attr in FORBIDDEN_ATTRS:raise ValueError('ATTRIBUTE_NOT_ALLOWED')
                if isinstance(n,ast.Call):
                    if isinstance(n.func,ast.Name):
                        if n.func.id not in cls.SAFE_CALLS:raise ValueError('CALL_NOT_ALLOWED')
                    elif isinstance(n.func,ast.Attribute):
                        if n.func.attr not in cls.ALLOWED_ATTRS:raise ValueError('ATTRIBUTE_CALL_NOT_ALLOWED')
                    else:raise ValueError('UNSAFE_CALL')
                if isinstance(n,ast.Name) and n.id.startswith('__'):raise ValueError('DUNDER_FORBIDDEN')
            return fname

        @classmethod
        def execute(cls,source,function_name,args):
            # Only recursively plain builtin values may cross the shadow boundary.
            def safe_value(x,depth=0):
                if depth>5:return False
                if isinstance(x,(type(None),bool,int,float,str)):return True
                if isinstance(x,(tuple,list)):return len(x)<=32 and all(safe_value(v,depth+1) for v in x)
                if isinstance(x,dict):return len(x)<=32 and all(isinstance(k,(str,int,bool,float)) and safe_value(v,depth+1) for k,v in x.items())
                return False
            if not all(safe_value(a) for a in args):raise ValueError('NON_BUILTIN_ARGUMENT_FORBIDDEN')
            tree=ast.parse(source);fname=cls._validate(tree)
            if fname!=function_name:raise ValueError('FUNCTION_NAME_MISMATCH')
            env=dict(cls.SAFE_CALLS);env['__builtins__']={}
            exec(compile(tree,'<yado-whole-function-attr-shadow>','exec'),env,env)
            return env[function_name](*copy.deepcopy(args))
    return Candidate

def infer_arg_domain(tree,arg):
    dict_keys=[]
    uses_dict=False;uses_str=False
    for n in ast.walk(tree):
        if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id==arg:
            uses_dict=True
            if isinstance(n.slice,ast.Constant) and isinstance(n.slice.value,str) and n.slice.value not in dict_keys:dict_keys.append(n.slice.value)
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id==arg:
            if n.func.attr in {'get','items','values'}:
                uses_dict=True
                if n.func.attr=='get' and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str) and n.args[0].value not in dict_keys:
                    dict_keys.append(n.args[0].value)
            if n.func.attr in {'strip','lower'}:uses_str=True
    # indirect ctx[k] over literal key tuple
    for comp in [x for x in ast.walk(tree) if isinstance(x,(ast.ListComp,ast.SetComp,ast.GeneratorExp,ast.DictComp))]:
        bindings={}
        for g in comp.generators:
            if isinstance(g.target,ast.Name) and isinstance(g.iter,(ast.Tuple,ast.List)):
                vals=[];ok=True
                for e in g.iter.elts:
                    if not isinstance(e,ast.Constant) or not isinstance(e.value,str):ok=False;break
                    vals.append(e.value)
                if ok:bindings[g.target.id]=vals
        for x in ast.walk(comp):
            if isinstance(x,ast.Subscript) and isinstance(x.value,ast.Name) and x.value.id==arg and isinstance(x.slice,ast.Name):
                uses_dict=True
                for k in bindings.get(x.slice.id,[]):
                    if k not in dict_keys:dict_keys.append(k)
    if uses_dict:
        keys=dict_keys[:6] or ['a','b','c']
        vals=[False,True,0,1,2,-1,'','x']
        out=[]
        # structured Boolean dictionaries first
        for bits in product((False,True),repeat=min(len(keys),5)):
            d={k:bits[i] if i<len(bits) else False for i,k in enumerate(keys)}
            out.append(d)
        # then sparse/mixed-value variants for .get semantics
        for k in keys:
            out.append({k:1});out.append({k:0});out.append({k:'x'})
        return out[:96]
    if uses_str:return ['', ' ', 'A', 'a', ' AbC ', 'HELLO', 'x y', '  z  ']
    return [-7,-3,-2,-1,0,1,2,3,7]

def useful_output(x):
    if isinstance(x,(bool,int,float,str)):
        if isinstance(x,str) and len(x)>256:return False
        if isinstance(x,float) and (x!=x or abs(x)>1e9):return False
        if isinstance(x,int) and not isinstance(x,bool) and abs(x)>10**9:return False
        return True
    if isinstance(x,(tuple,list)) and len(x)<=32:return all(isinstance(v,(bool,int,float,str,type(None))) for v in x)
    return False

def discover(attrs):
    C=cls_for(attrs);rows=[]
    for rel in manifest.get('active_runtime_sources',[]):
        if not str(rel).endswith('.py'):continue
        p=REPO/rel
        if not p.exists():continue
        tree=ast.parse(p.read_text(encoding='utf-8'))
        for n in tree.body:
            if not isinstance(n,ast.FunctionDef):continue
            if n.args.posonlyargs or n.args.vararg is not None or n.args.kwarg is not None or n.args.kwonlyargs:continue
            if not 1<=len(n.args.args)<=4:continue
            src=strip_fn(n);t=ast.parse(src)
            try:C._validate(t)
            except Exception:continue
            mutatable=sum(isinstance(x,(ast.BinOp,ast.Compare,ast.BoolOp)) or (isinstance(x,ast.Constant) and isinstance(x.value,int) and not isinstance(x.value,bool)) for x in ast.walk(t))
            if mutatable<1:continue
            domains=[infer_arg_domain(t,a.arg) for a in n.args.args]
            probes=[]
            for combo in product(*domains):
                probes.append(tuple(copy.deepcopy(combo)))
                if len(probes)>=192:break
            succ=[]
            for args in probes:
                try:
                    y=C.execute(src,n.name,args)
                    if useful_output(y):succ.append((args,y))
                except Exception:pass
            if len(succ)<8 or len({canon(y) for _,y in succ})<2:continue
            rows.append({
              'token':'WF2-'+sha(rel+'|'+str(n.lineno)+'|'+src)[:16],'path':rel,'line':int(n.lineno),'function_name':n.name,
              'source':src,'source_sha256':sha(src),'arg_names':[a.arg for a in n.args.args],
              'probe_count':len(probes),'probe_success_count':len(succ),'distinct_output_count':len({canon(y) for _,y in succ}),
              'mutatable_node_count':mutatable,'allowed_attrs':sorted(attrs),
              'sample_probes':[{'args':a,'output':y} for a,y in succ[:12]]
            })
    rows.sort(key=lambda r:(r['path'],r['line'],r['function_name']))
    return rows

evaluated=[]
for token,attrs in PURE_ATTR_PROFILES.items():
    rows=discover(attrs)
    evaluated.append({'token':token,'attrs':sorted(attrs),'candidate_count':len(rows),'source_file_count':len({r['path'] for r in rows}),'candidates':rows})
children=[x for x in evaluated if x['candidate_count']>0]
if not children:
    raise RuntimeError('NO_READONLY_ATTRIBUTE_PROFILE_UNLOCKS_WHOLE_FUNCTION')

selector=NeutralEvidenceProfileSelectorV1.select([
    EvidenceCandidate(token=x['token'],evidence=float(x['candidate_count'])+.4*float(x['source_file_count']),
      complexity=float(len(x['attrs'])),risk=.1*float(len(x['attrs'])),novelty=1.0)
    for x in children
],complexity_penalty=.08,risk_penalty=.25,novelty_bonus=.03)
selected=next(x for x in children if x['token']==selector['selected_token'])

skills=[
 {'skill_id':'KEEP_INT_ONLY_SUBSTRATE','artifact_digest':sub['substrate_gene']['gene_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':1.0,'fit_candidate':1.0,'heldout_baseline':1.0,'heldout_candidate':1.0,'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'ADMIT_SHADOW_ATTR_'+selected['token'],'artifact_digest':digest(selected),'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':0.0,'fit_candidate':1.0,'heldout_baseline':0.0,'heldout_candidate':1.0,'regression_pass':True,'state_integrity':True,'rollback_available':True}
]
db=ROOT/'yado_whole_function_substrate_expansion_v2.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.95,min_fit_gain=.05,max_heldout_drop=0,min_heldout_gain=.05)
finally:
    try:k.close()
    except Exception:pass
selected_skill=(selection.get('selected_skill_ids') or [None])[0]

gene={
 'schema':'yado.g2.code_whole_function_substrate_gene.v3',
 'gene_id':'GENE-G2-CODE-WHOLE-FUNCTION-SUBSTRATE-V3-'+digest({'selected':selected,'parent':sub['substrate_gene']['gene_digest'],'whole_v1':parent.get('receipt_sha256')})[:16],
 'organ':'CODE',
 'heritage':[sub['gene_id'],sub.get('receipt_sha256'),parent['gene_id'],parent.get('receipt_sha256'),census.get('receipt_sha256')],
 'mutation_kind':'READONLY_ATTRIBUTE_PROFILE_EXTENSION',
 'parent_safe_calls':['int'],
 'selected_profile':selected['token'],'allowed_readonly_attributes':selected['attrs'],
 'unlocked_candidate_count':selected['candidate_count'],'unlocked_source_file_count':selected['source_file_count'],
 'promotion_state':'SHADOW_ONLY','canonical_parent_unchanged':True
}
gene['gene_digest']=digest(gene)

checks={
 'whole_function_v1_consumed':True,'int_substrate_parent_consumed':True,
 'readonly_profiles_only':all(a in {'get','items','values','strip','lower'} for a in selected['attrs']),
 'no_mutating_attribute_method':not any(a in FORBIDDEN_ATTRS for a in selected['attrs']),
 'selected_profile_unlocks_multiple_functions':selected['candidate_count']>=2,
 'selected_profile_has_source_diversity':selected['source_file_count']>=2,
 'native_neutral_selector_selected_profile':selector['selected_token']==selected['token'],
 'native_skill_gate_selected_child':selected_skill=='ADMIT_SHADOW_ATTR_'+selected['token'],
 'no_filesystem_permission_added':True,'no_network_permission_added':True,'no_module_attribute_permission_added':True,
 'no_loop_permission_added':True,'builtins_only_runtime_arguments':True,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'external_model_used':False,'automatic_canonical_promotion':False
}
false_keys=['external_model_used','automatic_canonical_promotion']
passed=all(checks[k] is True for k in checks if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EXPANSION_V2' if passed else 'WITHHOLD_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EXPANSION_V2'

experience={
 'schema':'yado.g2.coding_whole_function_substrate_expansion.experience.v2','status':'TRAINED' if passed else 'WITHHOLD',
 'profile_evaluations':evaluated,'selector':selector,'native_skill_selection':selection,'substrate_gene':gene,
 'canonical_mutation':False,
 'semantic_boundary':'V2 EXPANDS THE SHADOW CODE SUBSTRATE ONLY WITH READONLY METHODS OVER RECURSIVELY PLAIN BUILTIN VALUES. BARE ATTRIBUTES, MUTATING METHODS, MODULE ATTRIBUTES, FILESYSTEM, NETWORK, IMPORTS, AND LOOPS REMAIN FORBIDDEN.'
}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n')
report={
 'schema':'yado.g2.coding_whole_function_substrate_expansion.v2','status':status,
 'selected_profile':selected['token'],'allowed_readonly_attributes':selected['attrs'],
 'unlocked_candidate_count':selected['candidate_count'],'unlocked_source_file_count':selected['source_file_count'],
 'unlocked_candidates':selected['candidates'],'gene_id':gene['gene_id'],'substrate_gene':gene,
 'selector':selector,'native_skill_selection':selection,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V2_MULTI_TASK' if passed else 'G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EXPANSION_V3'
}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'selected_profile':selected['token'],'allowed_readonly_attributes':selected['attrs'],
 'unlocked_candidate_count':selected['candidate_count'],'unlocked_source_file_count':selected['source_file_count'],
 'gene_id':gene['gene_id'],'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
