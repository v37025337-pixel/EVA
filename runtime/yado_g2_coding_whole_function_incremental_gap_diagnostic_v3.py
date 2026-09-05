from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3

PARENT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-substrate-expansion-v2.json'
SUB=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-substrate-evolution-v2.json'
MANIFEST=REPO/'canonical/yado-unified-core-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-incremental-gap-diagnostic-v3.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

parent,sub,manifest=map(load,[PARENT,SUB,MANIFEST])
if parent.get('status')!='WITHHOLD_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EXPANSION_V2':raise RuntimeError('V2_WITHHOLD_REQUIRED')
if sub.get('status')!='PASS_SHADOW_G2_CODING_WHOLE_FUNCTION_SUBSTRATE_EVOLUTION_V2':raise RuntimeError('INT_PARENT_REQUIRED')
base_tokens={x['token'] for x in sub.get('unlocked_candidates') or []}

PURE_NAMES={'int','bool','float','str','sorted','set','tuple','list','range','zip','enumerate'}
READONLY_METHODS={'get','items','values','strip','lower'}
LOCAL_MUTATORS={'append','extend','sort','add'}
MODULE_PURE_PREFIX={'json.','re.','hashlib.','math.','copy.'}
BASE_BANNED=(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.With,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda,ast.While,ast.For,ast.AsyncFor,ast.Try,ast.Raise,ast.Yield,ast.YieldFrom,ast.Await,ast.Delete)

def strip_fn(n):
 q=copy.deepcopy(n);q.decorator_list=[];q.returns=None;q.type_comment=None
 for a in list(q.args.posonlyargs)+list(q.args.args)+list(q.args.kwonlyargs):a.annotation=None;a.type_comment=None
 q.args.defaults=[];q.args.kw_defaults=[None for _ in q.args.kwonlyargs];ast.fix_missing_locations(q);return ast.unparse(q)+'\n'

def root_name(n):
 while isinstance(n,ast.Attribute):n=n.value
 if isinstance(n,ast.Name):return n.id
 if isinstance(n,ast.Call):return 'CALL'
 if isinstance(n,ast.Subscript):return 'SUBSCRIPT'
 return type(n).__name__

rows=[];profiles={}
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
  mut=sum(isinstance(x,(ast.BinOp,ast.Compare,ast.BoolOp)) or (isinstance(x,ast.Constant) and isinstance(x.value,int) and not isinstance(x.value,bool)) for x in ast.walk(t))
  if mut<1:continue
  other_banned=sorted({type(x).__name__ for x in ast.walk(t) if isinstance(x,BASE_BANNED)})
  pure_names=[];readonly=[];local_mut=[];module_attrs=[];bare_attrs=[];other_calls=[]
  parents={}
  for q in ast.walk(t):
   for c in ast.iter_child_nodes(q):parents[id(c)]=q
  arg_names={a.arg for a in n.args.args}
  for q in ast.walk(t):
   if isinstance(q,ast.Call):
    if isinstance(q.func,ast.Name):
     name=q.func.id
     if name not in BoundedCompositionalProgramRepairV3.SAFE_CALLS:
      if name in PURE_NAMES:pure_names.append(name)
      else:other_calls.append('NAME:'+name)
    elif isinstance(q.func,ast.Attribute):
     attr=q.func.attr;root=root_name(q.func.value)
     label=root+'.'+attr
     if root in arg_names or root in {'CALL','SUBSCRIPT'}:
      if attr in READONLY_METHODS:readonly.append(attr)
      elif attr in LOCAL_MUTATORS:local_mut.append(attr)
      else:other_calls.append('ATTR:'+label)
     else:
      module_attrs.append(label)
    else:other_calls.append('CALL:'+type(q.func).__name__)
   elif isinstance(q,ast.Attribute):
    par=parents.get(id(q))
    if not (isinstance(par,ast.Call) and par.func is q):
     bare_attrs.append(root_name(q.value)+'.'+q.attr)
  gaps={
   'pure_names':sorted(set(pure_names)),
   'readonly_methods':sorted(set(readonly)),
   'local_mutators':sorted(set(local_mut)),
   'module_attrs':sorted(set(module_attrs)),
   'bare_attrs':sorted(set(bare_attrs)),
   'other_calls':sorted(set(other_calls)),
   'other_banned':other_banned,
  }
  key=canon(gaps);profiles[key]=profiles.get(key,0)+1
  rows.append({'path':rel,'line':n.lineno,'function':n.name,'arg_count':len(n.args.args),'mutatable_node_count':mut,'source':src[:2200],'gaps':gaps})

def safe_gap_cost(r):
 g=r['gaps']
 hard=len(g['module_attrs'])+len(g['bare_attrs'])+len(g['other_calls'])+len(g['other_banned'])
 soft=len(g['pure_names'])+len(g['readonly_methods'])
 mut=len(g['local_mutators'])
 return (hard,mut,soft,-r['mutatable_node_count'],r['path'],r['line'])
rows.sort(key=safe_gap_cost)
safe_combo=[r for r in rows if not r['gaps']['module_attrs'] and not r['gaps']['bare_attrs'] and not r['gaps']['other_calls'] and not r['gaps']['other_banned'] and not r['gaps']['local_mutators']]
mutator_only=[r for r in rows if not r['gaps']['module_attrs'] and not r['gaps']['bare_attrs'] and not r['gaps']['other_calls'] and not r['gaps']['other_banned'] and r['gaps']['local_mutators']]
report={
 'schema':'yado.g2.coding_whole_function_incremental_gap_diagnostic.v3','status':'PASS_INCREMENTAL_GAP_DIAGNOSTIC',
 'parent_known_candidate_tokens':sorted(base_tokens),
 'candidate_function_count':len(rows),
 'safe_pure_readonly_combo_count':len(safe_combo),
 'safe_local_mutator_combo_count':len(mutator_only),
 'safe_pure_readonly_combo_functions':safe_combo[:80],
 'safe_local_mutator_combo_functions':mutator_only[:80],
 'ranked_all':rows[:120],
 'profile_counts':dict(sorted(profiles.items(),key=lambda kv:(-kv[1],kv[0]))[:80]),
 'semantic_boundary':'STATIC INCREMENTAL GAP DIAGNOSTIC. V2 TOTAL-COVERAGE METRIC IS NOT USED. NO LANGUAGE CAPABILITY, EXECUTION PERMISSION, REPAIR, OR CANONICAL STATE IS CHANGED.'
}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':report['status'],'candidate_function_count':len(rows),'safe_pure_readonly_combo_count':len(safe_combo),
 'safe_local_mutator_combo_count':len(mutator_only),
 'safe_examples':[{'path':r['path'],'function':r['function'],'gaps':r['gaps'],'mutatable':r['mutatable_node_count']} for r in safe_combo[:20]],
 'mutator_examples':[{'path':r['path'],'function':r['function'],'gaps':r['gaps'],'mutatable':r['mutatable_node_count']} for r in mutator_only[:20]],
 'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
