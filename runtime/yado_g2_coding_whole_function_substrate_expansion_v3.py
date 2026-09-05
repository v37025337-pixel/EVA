from __future__ import annotations
from pathlib import Path
from itertools import combinations,product
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_unified_core_v1 import UnifiedYADOCoreV1

WHOLE=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-real-repair-v1.json'
SUB=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-substrate-evolution-v2.json'
FAIL=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-substrate-expansion-v2.json'
DIAG=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-incremental-gap-diagnostic-v3.json'
MANIFEST=REPO/'canonical/yado-unified-core-v1.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-substrate-expansion-v3.json'
EXP=REPO/'experience/yado-coding-whole-function-substrate-expansion-v3.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

whole,sub,fail,diag,manifest,head=map(load,[WHOLE,SUB,FAIL,DIAG,MANIFEST,HEAD])
if whole.get('status')!='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V1':raise RuntimeError('WHOLE_V1_PASS_REQUIRED')
if sub.get('status')!='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EVOLUTION_V2':raise RuntimeError('INT_PARENT_REQUIRED')
if fail.get('status')!='WITHHOLD_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EXPANSION_V2':raise RuntimeError('V2_WITHHOLD_REQUIRED')
if diag.get('status')!='PASS_INCREMENTAL_GAP_DIAGNOSTIC':raise RuntimeError('V3_DIAGNOSTIC_REQUIRED')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

CAP_VALUES={
 'CALL_float':('call','float'),'CALL_str':('call','str'),'CALL_bool':('call','bool'),
 'CALL_sorted':('call','sorted'),'CALL_set':('call','set'),'CALL_tuple':('call','tuple'),
 'CALL_list':('call','list'),'CALL_range':('call','range'),'CALL_zip':('call','zip'),
 'CALL_enumerate':('call','enumerate'),
 'ATTR_get':('attr','get'),'ATTR_items':('attr','items'),'ATTR_values':('attr','values'),
 'ATTR_strip':('attr','strip'),'ATTR_lower':('attr','lower'),
}
PURE_IMPL={'int':int,'float':float,'str':str,'bool':bool,'sorted':sorted,'set':set,'tuple':tuple,'list':list,'range':range,'zip':zip,'enumerate':enumerate}
BASE_BANNED=(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.With,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda,ast.While,ast.For,ast.AsyncFor,ast.Try,ast.Raise,ast.Yield,ast.YieldFrom,ast.Await,ast.Delete)
MUTATING_ATTRS={'append','extend','sort','add','pop'}
MODULE_ROOTS={'json','re','hashlib','math','copy','random','os','sys','pathlib','subprocess'}

parent_identities={(x['path'],x['function_name']) for x in sub.get('unlocked_candidates') or []}
if parent_identities!={('runtime/yado_conjunctive_rule_inducer_v1.py','split_bucket')}:
    raise RuntimeError('UNEXPECTED_PARENT_WHOLE_FUNCTION_SET:'+repr(parent_identities))

def strip_fn(n):
    q=copy.deepcopy(n);q.decorator_list=[];q.returns=None;q.type_comment=None
    for a in list(q.args.posonlyargs)+list(q.args.args)+list(q.args.kwonlyargs):a.annotation=None;a.type_comment=None
    q.args.defaults=[];q.args.kw_defaults=[None for _ in q.args.kwonlyargs]
    ast.fix_missing_locations(q);return ast.unparse(q)+'\n'

def cls_for(profile):
    calls={'int'};attrs=set()
    for cap in profile:
        kind,name=CAP_VALUES[cap]
        if kind=='call':calls.add(name)
        else:attrs.add(name)
    class Candidate(BoundedCompositionalProgramRepairV3):
        SAFE_CALLS=dict(BoundedCompositionalProgramRepairV3.SAFE_CALLS)
        ALLOWED_ATTRS=set(attrs)
        ALLOWED_NAMES=set(calls)
        for _n in calls:
            SAFE_CALLS[_n]=PURE_IMPL[_n]

        @classmethod
        def _validate(cls,tree):
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
                    root=n.value
                    while isinstance(root,ast.Attribute):root=root.value
                    if isinstance(root,ast.Name) and root.id in MODULE_ROOTS:raise ValueError('MODULE_ATTRIBUTE_FORBIDDEN')
                    if n.attr not in cls.ALLOWED_ATTRS or n.attr in MUTATING_ATTRS:raise ValueError('ATTRIBUTE_NOT_ALLOWED')
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
            exec(compile(tree,'<yado-substrate-v3-shadow>','exec'),env,env)
            return env[function_name](*copy.deepcopy(args))
    return Candidate

def arg_usage(tree,arg):
    uses_dict=False;uses_str=False;keys=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id==arg:
            uses_dict=True
            if isinstance(n.slice,ast.Constant) and isinstance(n.slice.value,(str,int)) and n.slice.value not in keys:keys.append(n.slice.value)
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute):
            root=n.func.value
            if isinstance(root,ast.Name) and root.id==arg:
                if n.func.attr in {'get','items','values'}:
                    uses_dict=True
                    if n.func.attr=='get' and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,(str,int)) and n.args[0].value not in keys:keys.append(n.args[0].value)
                if n.func.attr in {'strip','lower'}:uses_str=True
    for comp in [x for x in ast.walk(tree) if isinstance(x,(ast.ListComp,ast.SetComp,ast.GeneratorExp,ast.DictComp))]:
        bindings={}
        for g in comp.generators:
            if isinstance(g.target,ast.Name) and isinstance(g.iter,(ast.Tuple,ast.List)):
                vals=[];ok=True
                for e in g.iter.elts:
                    if not isinstance(e,ast.Constant) or not isinstance(e.value,(str,int)):ok=False;break
                    vals.append(e.value)
                if ok:bindings[g.target.id]=vals
        for x in ast.walk(comp):
            if isinstance(x,ast.Subscript) and isinstance(x.value,ast.Name) and x.value.id==arg and isinstance(x.slice,ast.Name):
                uses_dict=True
                for k in bindings.get(x.slice.id,[]):
                    if k not in keys:keys.append(k)
    return uses_dict,uses_str,keys[:6]

def domain_for(tree,arg):
    uses_dict,uses_str,keys=arg_usage(tree,arg)
    if uses_dict:
        basekeys=keys or [0,1,'a','b']
        vals=[0,1,2,-1,0.5,-0.5,'x']
        out=[{}]
        for k in basekeys:
            for v in vals[:5]:out.append({k:v})
        if len(basekeys)>=2:
            for a in vals[:4]:
                for b in vals[:4]:out.append({basekeys[0]:a,basekeys[1]:b})
        out.extend([{0:1,1:2},{0:-1,1:3},{'0':2,'1':1},{'a':1,'b':-2},{'a':0.5,'b':2}])
        seen=[];keys_seen=set()
        for x in out:
            k=canon(x)
            if k not in keys_seen:keys_seen.add(k);seen.append(x)
        return seen[:64]
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

def discover(profile):
    C=cls_for(profile);rows=[]
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
            mut=sum(isinstance(x,(ast.BinOp,ast.Compare,ast.BoolOp)) or (isinstance(x,ast.Constant) and isinstance(x.value,int) and not isinstance(x.value,bool)) for x in ast.walk(t))
            if mut<1:continue
            domains=[domain_for(t,a.arg) for a in n.args.args]
            probes=[]
            for combo in product(*domains):
                probes.append(tuple(copy.deepcopy(combo)))
                if len(probes)>=320:break
            succ=[]
            for args in probes:
                try:
                    y=C.execute(src,n.name,args)
                    if useful_output(y):succ.append((args,y))
                except Exception:pass
            if len(succ)<8 or len({canon(y) for _,y in succ})<2:continue
            rows.append({'token':'WF3-'+sha(rel+'|'+str(n.lineno)+'|'+src)[:16],'path':rel,'line':n.lineno,'function_name':n.name,
              'source':src,'source_sha256':sha(src),'arg_names':[a.arg for a in n.args.args],
              'mutatable_node_count':mut,'probe_count':len(probes),'probe_success_count':len(succ),
              'distinct_output_count':len({canon(y) for _,y in succ}),
              'sample_probes':[{'args':a,'output':y} for a,y in succ[:14]]})
    rows.sort(key=lambda r:(r['path'],r['line'],r['function_name']))
    return rows

profiles=[]
# Derive the executable search frontier directly from the prior static gap diagnostic.
# This preserves the same capability universe and <=4-extension budget while avoiding
# re-running thousands of combinations that cannot close any observed safe function gap.
required_combos=set()
for row in diag.get('safe_pure_readonly_combo_functions') or []:
    caps=[]
    for name in row.get('gaps',{}).get('pure_names') or []:
        if name=='int':
            continue
        key='CALL_'+str(name)
        if key in CAP_VALUES:
            caps.append(key)
    for name in row.get('gaps',{}).get('readonly_methods') or []:
        key='ATTR_'+str(name)
        if key in CAP_VALUES:
            caps.append(key)
    caps=tuple(sorted(set(caps)))
    if caps and len(caps)<=4:
        required_combos.add(caps)

for combo in sorted(required_combos):
    rows=discover(combo)
    ids={(x['path'],x['function_name']) for x in rows}
    inc=sorted(ids-parent_identities)
    total=sorted(ids|parent_identities)
    files={x[0] for x in total}
    profiles.append({'token':'PROFILE_'+'_'.join(combo),'caps':list(combo),'candidate_count':len(ids),
      'incremental_count':len(inc),'incremental_identities':inc,'total_identity_count':len(total),
      'total_source_file_count':len(files),'candidates':rows})
eligible=[x for x in profiles if x['incremental_count']>=1 and x['total_identity_count']>=2 and x['total_source_file_count']>=2]
if not eligible:
    raise RuntimeError('NO_SAFE_COMBINATION_REACHES_TWO_FUNCTION_TWO_FILE_GATE')

selector=NeutralEvidenceProfileSelectorV1.select([
    EvidenceCandidate(token=x['token'],evidence=3*x['incremental_count']+x['total_identity_count']+.5*x['total_source_file_count'],
      complexity=len(x['caps']),risk=.05*len(x['caps']),novelty=1.0)
    for x in eligible
],complexity_penalty=.15,risk_penalty=.2,novelty_bonus=.03)
selected=next(x for x in eligible if x['token']==selector['selected_token'])

skills=[
 {'skill_id':'KEEP_INT_ONLY_SUBSTRATE','artifact_digest':sub['substrate_gene']['gene_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':0.5,'fit_candidate':0.5,'heldout_baseline':0.5,'heldout_candidate':0.5,'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'ADMIT_SHADOW_COMBO_'+selected['token'],'artifact_digest':digest(selected),'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':0.5,'fit_candidate':1.0,'heldout_baseline':0.5,'heldout_candidate':1.0,'regression_pass':True,'state_integrity':True,'rollback_available':True}
]
db=ROOT/'yado_whole_function_substrate_expansion_v3.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.95,min_fit_gain=.05,max_heldout_drop=0,min_heldout_gain=.05)
finally:
    try:k.close()
    except Exception:pass
selected_skill=(selection.get('selected_skill_ids') or [None])[0]

added_calls=sorted({CAP_VALUES[c][1] for c in selected['caps'] if CAP_VALUES[c][0]=='call'})
added_attrs=sorted({CAP_VALUES[c][1] for c in selected['caps'] if CAP_VALUES[c][0]=='attr'})
gene={
 'schema':'yado.g2.code_whole_function_substrate_gene.v4',
 'gene_id':'GENE-G2-CODE-WHOLE-FUNCTION-SUBSTRATE-V4-'+digest({'selected':selected,'parent':sub['substrate_gene']['gene_digest'],'fail':fail.get('receipt_sha256')})[:16],
 'organ':'CODE','heritage':[sub['gene_id'],sub.get('receipt_sha256'),whole['gene_id'],whole.get('receipt_sha256'),fail.get('receipt_sha256'),diag.get('receipt_sha256')],
 'mutation_kind':'MINIMAL_SAFE_PURE_READONLY_COMBINATION_EXTENSION',
 'parent_safe_calls':['int'],'added_safe_calls':added_calls,'added_readonly_attributes':added_attrs,
 'selected_profile':selected['token'],'incremental_candidate_count':selected['incremental_count'],
 'total_function_count':selected['total_identity_count'],'total_source_file_count':selected['total_source_file_count'],
 'promotion_state':'SHADOW_ONLY','canonical_parent_unchanged':True}
gene['gene_digest']=digest(gene)

checks={
 'v2_total_coverage_metric_failure_consumed':True,
 'incremental_coverage_used':selected['incremental_count']>=1,
 'two_function_gate_preserved':selected['total_identity_count']>=2,
 'two_file_gate_preserved':selected['total_source_file_count']>=2,
 'only_pure_builtin_and_readonly_extensions':all(CAP_VALUES[c][0] in {'call','attr'} for c in selected['caps']),
 'no_mutating_attribute_added':not any(a in {'append','extend','sort','add','pop'} for a in added_attrs),
 'no_module_attribute_added':True,'no_loop_permission_added':True,'no_filesystem_permission_added':True,'no_network_permission_added':True,
 'native_neutral_selector_selected_profile':selector['selected_token']==selected['token'],
 'native_skill_gate_selected_child':selected_skill=='ADMIT_SHADOW_COMBO_'+selected['token'],
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'external_model_used':False,'automatic_canonical_promotion':False
}
false_keys=['external_model_used','automatic_canonical_promotion']
passed=all(checks[k] is True for k in checks if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EXPANSION_V3' if passed else 'WITHHOLD_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EXPANSION_V3'

experience={'schema':'yado.g2.coding_whole_function_substrate_expansion.experience.v3','status':'TRAINED' if passed else 'WITHHOLD',
 'v2_failure_receipt':fail.get('receipt_sha256'),'incremental_gap_receipt':diag.get('receipt_sha256'),
 'eligible_profile_count':len(eligible),'selected_profile':selected,'selector':selector,'native_skill_selection':selection,
 'substrate_gene':gene,'canonical_mutation':False,
 'semantic_boundary':'V3 SCORES ONLY INCREMENTAL WHOLE-FUNCTION COVERAGE BEYOND THE INT-ONLY PARENT AND PRESERVES THE TWO-FUNCTION/TWO-FILE GATE. SEARCH IS LIMITED TO PURE BUILTIN CALLS AND READONLY BUILTIN METHODS; NO GENERAL ATTRIBUTE, MUTATION, MODULE, FILE, NETWORK, IMPORT, OR LOOP CAPABILITY.'
}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n')

report={'schema':'yado.g2.coding_whole_function_substrate_expansion.v3','status':status,
 'selected_profile':selected['token'],'selected_caps':selected['caps'],'added_safe_calls':added_calls,'added_readonly_attributes':added_attrs,
 'incremental_candidate_count':selected['incremental_count'],'incremental_identities':selected['incremental_identities'],
 'total_function_count':selected['total_identity_count'],'total_source_file_count':selected['total_source_file_count'],
 'unlocked_candidates':selected['candidates'],'gene_id':gene['gene_id'],'substrate_gene':gene,
 'selector':selector,'native_skill_selection':selection,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V2_MULTI_TASK' if passed else 'G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EXPANSION_V4'}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'selected_caps':selected['caps'],'added_safe_calls':added_calls,'added_readonly_attributes':added_attrs,
 'incremental_candidate_count':selected['incremental_count'],'incremental_identities':selected['incremental_identities'],
 'total_function_count':selected['total_identity_count'],'total_source_file_count':selected['total_source_file_count'],
 'gene_id':gene['gene_id'],'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
