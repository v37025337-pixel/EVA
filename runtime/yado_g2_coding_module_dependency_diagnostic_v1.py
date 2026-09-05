from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

PARENT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-real-repair-v2-multi-task.json'
SUB=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-substrate-expansion-v3.json'
MANIFEST=REPO/'canonical/yado-unified-core-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-module-dependency-diagnostic-v1.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

parent,sub,manifest=map(load,[PARENT,SUB,MANIFEST])
if parent.get('status')!='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V2_MULTI_TASK':raise RuntimeError('MULTI_TASK_PARENT_PASS_REQUIRED')
if parent.get('next_required_capability')!='G2_CODING_MULTI_FUNCTION_MODULE_REPAIR_V1':raise RuntimeError('PARENT_FRONTIER_MISMATCH')
if sub.get('status')!='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EXPANSION_V3':raise RuntimeError('SUBSTRATE_V3_REQUIRED')

BASE_SAFE_NAMES={'min','max','all','any','sum','abs','len','int','float','str'}
BASE_SAFE_ATTRS={'get','items'}
BASE_BANNED=(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.With,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda,ast.While,ast.For,ast.AsyncFor,ast.Try,ast.Raise,ast.Yield,ast.YieldFrom,ast.Await,ast.Delete)
LOCAL_MUTATORS={'append','extend','sort','add','pop'}

def strip_fn(n):
    q=copy.deepcopy(n);q.decorator_list=[];q.returns=None;q.type_comment=None
    for a in list(q.args.posonlyargs)+list(q.args.args)+list(q.args.kwonlyargs):a.annotation=None;a.type_comment=None
    q.args.defaults=[];q.args.kw_defaults=[None for _ in q.args.kwonlyargs]
    ast.fix_missing_locations(q);return ast.unparse(q)+'\n'

rows=[]
for rel in manifest.get('active_runtime_sources',[]):
    if not str(rel).endswith('.py'):continue
    p=REPO/rel
    if not p.exists():continue
    src=p.read_text(encoding='utf-8');tree=ast.parse(src)
    funcs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    if len(funcs)<2:continue
    for caller_name,caller in funcs.items():
        local_calls=sorted({n.func.id for n in ast.walk(caller) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in funcs and n.func.id!=caller_name})
        for callee_name in local_calls:
            callee=funcs[callee_name]
            if caller.args.vararg or caller.args.kwarg or caller.args.kwonlyargs or caller.args.posonlyargs:continue
            if callee.args.vararg or callee.args.kwarg or callee.args.kwonlyargs or callee.args.posonlyargs:continue
            if not 1<=len(caller.args.args)<=5 or not 1<=len(callee.args.args)<=5:continue
            module_src=strip_fn(callee)+'\n'+strip_fn(caller)
            mt=ast.parse(module_src)
            gaps={'unsafe_nodes':[],'missing_names':[],'missing_attrs':[],'local_mutators':[],'bare_attrs':[],'other_calls':[]}
            parents={}
            for q in ast.walk(mt):
                for c in ast.iter_child_nodes(q):parents[id(c)]=q
            for q in ast.walk(mt):
                if isinstance(q,BASE_BANNED):gaps['unsafe_nodes'].append(type(q).__name__)
                if isinstance(q,ast.Call):
                    if isinstance(q.func,ast.Name):
                        nm=q.func.id
                        if nm in {caller_name,callee_name}:pass
                        elif nm not in BASE_SAFE_NAMES:gaps['missing_names'].append(nm)
                    elif isinstance(q.func,ast.Attribute):
                        if q.func.attr in LOCAL_MUTATORS:gaps['local_mutators'].append(q.func.attr)
                        elif q.func.attr not in BASE_SAFE_ATTRS:gaps['missing_attrs'].append(q.func.attr)
                    else:gaps['other_calls'].append(type(q.func).__name__)
                elif isinstance(q,ast.Attribute):
                    par=parents.get(id(q))
                    if not (isinstance(par,ast.Call) and par.func is q):gaps['bare_attrs'].append(q.attr)
            gaps={k:sorted(set(v)) for k,v in gaps.items()}
            mut=sum(isinstance(x,(ast.BinOp,ast.Compare,ast.BoolOp)) or (isinstance(x,ast.Constant) and isinstance(x.value,int) and not isinstance(x.value,bool)) for x in ast.walk(mt))
            if mut<1:continue
            cost=sum(len(v) for v in gaps.values())
            rows.append({'path':rel,'caller':caller_name,'callee':callee_name,'caller_arg_count':len(caller.args.args),'callee_arg_count':len(callee.args.args),
              'mutatable_node_count':mut,'gap_cost':cost,'gaps':gaps,'module_source':module_src[:4200]})

rows.sort(key=lambda r:(r['gap_cost'],len(r['gaps']['unsafe_nodes']),len(r['gaps']['local_mutators']),-r['mutatable_node_count'],r['path'],r['caller'],r['callee']))
zero=[r for r in rows if r['gap_cost']==0]
near=[r for r in rows if r['gap_cost']<=2]
report={'schema':'yado.g2.coding_module_dependency_diagnostic.v1','status':'PASS_MODULE_DEPENDENCY_DIAGNOSTIC',
 'pair_count':len(rows),'zero_gap_pair_count':len(zero),'near_gap_pair_count':len(near),
 'zero_gap_pairs':zero[:40],'near_gap_pairs':near[:80],'ranked_pairs':rows[:120],
 'semantic_boundary':'STATIC REAL TOP-LEVEL CALLER-CALLEE DIAGNOSTIC UNDER THE CURRENT SHADOW SUBSTRATE. LOCAL CALLS ARE TREATED AS THE ONLY PROVISIONAL MODULE LINK; NO EXECUTION, REPAIR, NEW PERMISSION, OR CANONICAL MUTATION OCCURS.'}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':report['status'],'pair_count':len(rows),'zero_gap_pair_count':len(zero),'near_gap_pair_count':len(near),
 'top_pairs':[{'path':r['path'],'caller':r['caller'],'callee':r['callee'],'gap_cost':r['gap_cost'],'gaps':r['gaps'],'mutatable':r['mutatable_node_count']} for r in rows[:25]],
 'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
