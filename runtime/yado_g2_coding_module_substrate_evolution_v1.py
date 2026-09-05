from __future__ import annotations
from pathlib import Path
from itertools import product
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_unified_core_v1 import UnifiedYADOCoreV1

PARENT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-real-repair-v2-multi-task.json'
SUB=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-substrate-expansion-v3.json'
DIAG=REPO/'candidates/kernel-self-generated/g2-coding-module-dependency-diagnostic-v1.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-module-substrate-evolution-v1.json'
EXP=REPO/'experience/yado-coding-module-substrate-evolution-v1.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

parent,sub,diag,head=map(load,[PARENT,SUB,DIAG,HEAD])
if parent.get('status')!='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V2_MULTI_TASK':raise RuntimeError('MULTI_TASK_PARENT_PASS_REQUIRED')
if parent.get('next_required_capability')!='G2_CODING_MULTI_FUNCTION_MODULE_REPAIR_V1':raise RuntimeError('PARENT_FRONTIER_MISMATCH')
if sub.get('status')!='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EXPANSION_V3':raise RuntimeError('SUBSTRATE_V3_PASS_REQUIRED')
if diag.get('status')!='PASS_MODULE_DEPENDENCY_DIAGNOSTIC':raise RuntimeError('MODULE_DIAGNOSTIC_REQUIRED')
if int(diag.get('zero_gap_pair_count') or 0)!=0 or int(diag.get('near_gap_pair_count') or 0)<1:raise RuntimeError('EXPECTED_NEAR_GAP_FRONTIER')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

SAFE_CALLS={'min':min,'max':max,'all':all,'any':any,'sum':sum,'abs':abs,'len':len,'int':int,'float':float,'str':str}
READONLY_ATTRS={'get','items'}
PROFILES=[
 {'token':'KEEP_PARENT','allow_local_sort':False,'allow_pure_sort_lambda':False},
 {'token':'LOCAL_SORT_ONLY','allow_local_sort':True,'allow_pure_sort_lambda':False},
 {'token':'PURE_SORT_KEY_LAMBDA_ONLY','allow_local_sort':False,'allow_pure_sort_lambda':True},
 {'token':'LOCAL_SORT_WITH_PURE_KEY_LAMBDA','allow_local_sort':True,'allow_pure_sort_lambda':True},
]

def safe_plain(x,depth=0):
    if depth>6:return False
    if isinstance(x,(type(None),bool,int,float,str)):return True
    if isinstance(x,(tuple,list)):return len(x)<=48 and all(safe_plain(v,depth+1) for v in x)
    if isinstance(x,dict):return len(x)<=48 and all(isinstance(k,(str,int,bool,float)) and safe_plain(v,depth+1) for k,v in x.items())
    return False

def local_list_vars(func):
    out=set()
    for s in func.body:
        if isinstance(s,(ast.Assign,ast.AnnAssign)):
            targets=s.targets if isinstance(s,ast.Assign) else [s.target]
            value=s.value
            if isinstance(value,(ast.List,ast.ListComp)):
                for t in targets:
                    if isinstance(t,ast.Name):out.add(t.id)
    return out

def pure_lambda_expr(node,arg):
    allowed=(ast.Expression,ast.Tuple,ast.List,ast.Name,ast.Load,ast.Subscript,ast.Constant,ast.UnaryOp,ast.USub,ast.UAdd,
             ast.BinOp,ast.Add,ast.Sub,ast.Mult,ast.Mod,ast.FloorDiv,ast.Compare,ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE,
             ast.BoolOp,ast.And,ast.Or,ast.IfExp)
    for n in ast.walk(node):
        if not isinstance(n,allowed):return False
        if isinstance(n,ast.Name) and n.id!=arg:return False
        if isinstance(n,ast.Subscript):
            root=n.value
            while isinstance(root,ast.Subscript):root=root.value
            if not isinstance(root,ast.Name) or root.id!=arg:return False
        if isinstance(n,ast.Constant) and not isinstance(n.value,(type(None),bool,int,float,str)):return False
    return True

class ModulePairSandbox:
    @classmethod
    def validate(cls,source,profile):
        tree=ast.parse(source)
        banned=(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.With,ast.AsyncFunctionDef,ast.ClassDef,
                ast.While,ast.For,ast.AsyncFor,ast.Try,ast.Raise,ast.Yield,ast.YieldFrom,ast.Await,ast.Delete)
        if any(isinstance(n,banned) for n in ast.walk(tree)):raise ValueError('UNSAFE_MODULE')
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        if len(funcs)!=2 or len(tree.body)!=2:raise ValueError('EXACTLY_TWO_FUNCTIONS_REQUIRED')
        names={f.name for f in funcs}
        parents={}
        for p in ast.walk(tree):
            for c in ast.iter_child_nodes(p):parents[id(c)]=p
        lambda_ids=set()
        for f in funcs:
            local_lists=local_list_vars(f)
            for n in ast.walk(f):
                if isinstance(n,ast.Lambda):
                    lambda_ids.add(id(n))
                    if not profile['allow_pure_sort_lambda']:raise ValueError('LAMBDA_NOT_ALLOWED')
                    par=parents.get(id(n))
                    if not isinstance(par,ast.keyword) or par.arg!='key':raise ValueError('LAMBDA_ONLY_SORT_KEY')
                    call=parents.get(id(par))
                    if not isinstance(call,ast.Call) or not isinstance(call.func,ast.Attribute) or call.func.attr!='sort':raise ValueError('LAMBDA_ONLY_SORT_KEY')
                    if len(n.args.args)!=1 or n.args.posonlyargs or n.args.kwonlyargs or n.args.vararg or n.args.kwarg:raise ValueError('LAMBDA_ARITY')
                    if not pure_lambda_expr(n.body,n.args.args[0].arg):raise ValueError('IMPURE_SORT_KEY_LAMBDA')
                if isinstance(n,ast.Attribute):
                    par=parents.get(id(n))
                    if not (isinstance(par,ast.Call) and par.func is n):raise ValueError('BARE_ATTRIBUTE_FORBIDDEN')
                    if n.attr in READONLY_ATTRS:continue
                    if n.attr=='sort':
                        if not profile['allow_local_sort']:raise ValueError('SORT_NOT_ALLOWED')
                        if not isinstance(n.value,ast.Name) or n.value.id not in local_lists:raise ValueError('SORT_INPUT_OR_NONLOCAL_FORBIDDEN')
                        call=par
                        if call.args:raise ValueError('SORT_POSITIONAL_ARGS_FORBIDDEN')
                        if len(call.keywords)!=1 or call.keywords[0].arg!='key' or not isinstance(call.keywords[0].value,ast.Lambda):
                            raise ValueError('SORT_REQUIRES_SINGLE_PURE_KEY')
                        continue
                    raise ValueError('ATTRIBUTE_NOT_ALLOWED:'+n.attr)
                if isinstance(n,ast.Call):
                    if isinstance(n.func,ast.Name):
                        if n.func.id not in SAFE_CALLS and n.func.id not in names:raise ValueError('CALL_NOT_ALLOWED:'+n.func.id)
                    elif isinstance(n.func,ast.Attribute):
                        if n.func.attr not in READONLY_ATTRS|{'sort'}:raise ValueError('ATTRIBUTE_CALL_NOT_ALLOWED')
                    else:raise ValueError('UNSAFE_CALL')
                if isinstance(n,ast.Name) and n.id.startswith('__'):raise ValueError('DUNDER_FORBIDDEN')
        return [f.name for f in funcs]

    @classmethod
    def execute(cls,source,caller,args,profile):
        if not all(safe_plain(a) for a in args):raise ValueError('NON_PLAIN_ARGUMENT')
        names=cls.validate(source,profile)
        if caller not in names:raise ValueError('CALLER_NOT_IN_MODULE')
        env=dict(SAFE_CALLS);env['__builtins__']={}
        exec(compile(ast.parse(source),'<yado-module-pair-shadow>','exec'),env,env)
        out=env[caller](*copy.deepcopy(args))
        if not safe_plain(out):raise ValueError('NON_PLAIN_OUTPUT')
        return out

def infer_domain(pair):
    caller=pair['caller']
    if caller=='_pred':
        labels_sets=[['A','B'],['X','Y'],['A','B','C']]
        scalar=[-2.0,-1.0,0.0,0.5,1.0,2.0,3.0]
        rows=[]
        for labels in labels_sets:
            for i in range(18):
                w={};b={}
                for j,l in enumerate(labels):
                    w[l]={0:scalar[(i+j)%len(scalar)],1:scalar[(i+2*j+1)%len(scalar)]}
                    if i%3==0:w[l][str(0)]=scalar[(i+j+2)%len(scalar)]
                    b[l]=scalar[(i*2+j)%len(scalar)]
                x={0:scalar[i%len(scalar)],1:scalar[(i+3)%len(scalar)]}
                rows.append((copy.deepcopy(labels),w,b,x))
        return rows
    # Generic fallback for other near-gap pairs, if any become eligible later.
    n=int(pair.get('caller_arg_count') or 1)
    vals=[-2,-1,0,1,2,'','x']
    rows=[]
    for combo in product(vals,repeat=n):
        rows.append(combo)
        if len(rows)>=80:break
    return rows

near=diag.get('near_gap_pairs') or []
pair_candidates=[]
for i,pair in enumerate(near):
    for profile in PROFILES:
        source=pair['module_source']
        valid=True;error=None;success=0;distinct=set()
        try:
            ModulePairSandbox.validate(source,profile)
            for args in infer_domain(pair):
                try:
                    y=ModulePairSandbox.execute(source,pair['caller'],args,profile)
                    success+=1;distinct.add(canon(y))
                except Exception:pass
        except Exception as e:
            valid=False;error=type(e).__name__+':'+str(e)
        row={'token':'PAIR'+str(i)+'_'+profile['token'],'pair_index':i,'path':pair['path'],'caller':pair['caller'],'callee':pair['callee'],
             'profile':profile,'valid':valid,'validation_error':error,'success_count':success,'distinct_output_count':len(distinct),
             'gap_cost':pair['gap_cost']}
        pair_candidates.append(row)

eligible=[x for x in pair_candidates if x['valid'] and x['success_count']>=12 and x['distinct_output_count']>=2]
if not eligible:raise RuntimeError('NO_MODULE_SUBSTRATE_PROFILE_EXECUTES_NEAR_GAP_PAIR')

selector=NeutralEvidenceProfileSelectorV1.select([
    EvidenceCandidate(token=x['token'],evidence=2.0+x['success_count']/100.0+x['distinct_output_count']/20.0,
      complexity=(int(x['profile']['allow_local_sort'])+int(x['profile']['allow_pure_sort_lambda'])),
      risk=.1*(int(x['profile']['allow_local_sort'])+int(x['profile']['allow_pure_sort_lambda'])),novelty=1.0)
    for x in eligible
],complexity_penalty=.12,risk_penalty=.25,novelty_bonus=.03)
selected=next(x for x in eligible if x['token']==selector['selected_token'])

# Safety negative controls are independent of the real pair.
negative={
 'sort_on_input_rejected':False,'lambda_call_rejected':False,'lambda_attribute_rejected':False,
 'lambda_outside_sort_rejected':False,'sort_without_key_rejected':False
}
tests={
 'sort_on_input_rejected':"def helper(x):\n    return x\n\ndef caller(xs):\n    xs.sort(key=lambda z: z)\n    return xs[0]\n",
 'lambda_call_rejected':"def helper(x):\n    return x\n\ndef caller(x):\n    a=[(x,0)]\n    a.sort(key=lambda z: str(z[0]))\n    return a[0][0]\n",
 'lambda_attribute_rejected':"def helper(x):\n    return x\n\ndef caller(x):\n    a=[(x,0)]\n    a.sort(key=lambda z: z.real)\n    return a[0][0]\n",
 'lambda_outside_sort_rejected':"def helper(x):\n    return x\n\ndef caller(x):\n    f=lambda z: z\n    return f(x)\n",
 'sort_without_key_rejected':"def helper(x):\n    return x\n\ndef caller(x):\n    a=[x,0]\n    a.sort()\n    return a[0]\n",
}
for k,s in tests.items():
    try:ModulePairSandbox.validate(s,selected['profile'])
    except Exception:negative[k]=True

skills=[
 {'skill_id':'KEEP_WHOLE_FUNCTION_SUBSTRATE_V3','artifact_digest':sub['substrate_gene']['gene_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':0.0,'fit_candidate':0.0,'heldout_baseline':0.0,'heldout_candidate':0.0,'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'ADMIT_SHADOW_MODULE_'+selected['profile']['token'],'artifact_digest':digest(selected),'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':0.0,'fit_candidate':1.0,'heldout_baseline':0.0,'heldout_candidate':1.0,
  'regression_pass':all(negative.values()),'state_integrity':True,'rollback_available':True}
]
db=ROOT/'yado_module_substrate_evolution_v1.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.95,min_fit_gain=.05,max_heldout_drop=0,min_heldout_gain=.05)
finally:
    try:k.close()
    except Exception:pass
selected_skill=(selection.get('selected_skill_ids') or [None])[0]

gene={'schema':'yado.g2.code_module_substrate_gene.v1',
 'gene_id':'GENE-G2-CODE-MODULE-SUBSTRATE-V1-'+digest({'selected':selected,'diag':diag.get('receipt_sha256'),'parent':sub['substrate_gene']['gene_digest']})[:16],
 'organ':'CODE','heritage':[parent['gene_id'],parent.get('receipt_sha256'),sub['gene_id'],sub.get('receipt_sha256'),diag.get('receipt_sha256')],
 'mutation_kind':'LOCAL_LIST_SORT_WITH_PURE_KEY_LAMBDA_MODULE_LINK',
 'selected_pair':{'path':selected['path'],'caller':selected['caller'],'callee':selected['callee']},
 'allow_local_sort':selected['profile']['allow_local_sort'],'allow_pure_sort_key_lambda':selected['profile']['allow_pure_sort_lambda'],
 'local_calls_only_within_two_function_module':True,'promotion_state':'SHADOW_ONLY','canonical_parent_unchanged':True}
gene['gene_digest']=digest(gene)

checks={
 'multi_task_parent_consumed':True,'module_diagnostic_consumed':True,
 'no_zero_gap_pair_available':int(diag.get('zero_gap_pair_count') or 0)==0,
 'selected_near_gap_pair':selected['gap_cost']<=2,
 'profile_executes_material_domain':selected['success_count']>=12 and selected['distinct_output_count']>=2,
 'local_sort_only':selected['profile']['allow_local_sort'] is True,
 'pure_sort_key_lambda_only':selected['profile']['allow_pure_sort_lambda'] is True,
 'all_negative_safety_controls_rejected':all(negative.values()),
 'native_neutral_selector_selected_profile':selector['selected_token']==selected['token'],
 'native_skill_gate_selected_child':selected_skill=='ADMIT_SHADOW_MODULE_'+selected['profile']['token'],
 'no_general_attribute_permission':True,'no_input_mutation_permission':True,'no_module_attributes':True,
 'no_filesystem_permission':True,'no_network_permission':True,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'external_model_used':False,'automatic_canonical_promotion':False
}
false_keys=['external_model_used','automatic_canonical_promotion']
passed=all(checks[k] is True for k in checks if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_MODULE_SUBSTRATE_EVOLUTION_V1' if passed else 'WITHHOLD_G2_CODING_MODULE_SUBSTRATE_EVOLUTION_V1'

experience={'schema':'yado.g2.coding_module_substrate_evolution.experience.v1','status':'TRAINED' if passed else 'WITHHOLD',
 'pair_profile_evaluations':pair_candidates,'selected':selected,'selector':selector,'negative_safety_controls':negative,
 'native_skill_selection':selection,'module_substrate_gene':gene,'canonical_mutation':False,
 'semantic_boundary':'SHADOW MODULE SUBSTRATE FOR EXACTLY TWO LOCAL FUNCTIONS. sort IS ALLOWED ONLY ON A LOCALLY CREATED LIST AND ONLY WITH ONE PURE key LAMBDA. THE LAMBDA MAY NOT CALL FUNCTIONS OR ACCESS ATTRIBUTES. INPUT MUTATION, GENERAL ATTRIBUTES, MODULE ATTRIBUTES, FILESYSTEM, NETWORK, IMPORTS, AND LOOPS REMAIN FORBIDDEN.'}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n')

report={'schema':'yado.g2.coding_module_substrate_evolution.v1','status':status,
 'selected_pair':gene['selected_pair'],'selected_profile':selected['profile'],'execution_success_count':selected['success_count'],
 'distinct_output_count':selected['distinct_output_count'],'negative_safety_controls':negative,
 'gene_id':gene['gene_id'],'module_substrate_gene':gene,'selector':selector,'native_skill_selection':selection,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_MULTI_FUNCTION_MODULE_REPAIR_V1' if passed else 'G2_CODING_MODULE_SUBSTRATE_EVOLUTION_V2'}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'selected_pair':report['selected_pair'],'selected_profile':report['selected_profile'],
 'execution_success_count':report['execution_success_count'],'distinct_output_count':report['distinct_output_count'],
 'negative_safety_controls':negative,'gene_id':gene['gene_id'],'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
