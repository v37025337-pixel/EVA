from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3
M=REPO/'canonical/yado-unified-core-v1.json';OUT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-ast-census-v2.json'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def strip_fn(n):
 q=copy.deepcopy(n);q.decorator_list=[];q.returns=None;q.type_comment=None
 for a in list(q.args.posonlyargs)+list(q.args.args)+list(q.args.kwonlyargs):a.annotation=None;a.type_comment=None
 q.args.defaults=[];q.args.kw_defaults=[None for _ in q.args.kwonlyargs];ast.fix_missing_locations(q);return ast.unparse(q)+'\n'
BANNED=(ast.Import,ast.ImportFrom,ast.Attribute,ast.Global,ast.Nonlocal,ast.With,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda,ast.While,ast.For,ast.AsyncFor,ast.Try,ast.Raise,ast.Yield,ast.YieldFrom,ast.Await,ast.Delete)
m=load(M);sources=[x for x in m.get('active_runtime_sources',[]) if x.endswith('.py')]
rows=[];agg={};callagg={}
for rel in sources:
 p=REPO/rel
 if not p.exists():continue
 tree=ast.parse(p.read_text(encoding='utf-8'))
 for n in tree.body:
  if not isinstance(n,ast.FunctionDef):continue
  src=strip_fn(n);t=ast.parse(src)
  banned=sorted({type(x).__name__ for x in ast.walk(t) if isinstance(x,BANNED)})
  calls=[]
  for x in ast.walk(t):
   if isinstance(x,ast.Call):
    if isinstance(x.func,ast.Name):
     calls.append('NAME:'+x.func.id)
    elif isinstance(x.func,ast.Attribute):
     root=x.func.value.id if isinstance(x.func.value,ast.Name) else type(x.func.value).__name__
     calls.append('ATTR:'+str(root)+'.'+x.func.attr)
    else:calls.append('OTHER:'+type(x.func).__name__)
  unsupported_names=sorted({c for c in calls if c.startswith('NAME:') and c.split(':',1)[1] not in BoundedCompositionalProgramRepairV3.SAFE_CALLS})
  attrs=sorted({c for c in calls if c.startswith('ATTR:')})
  for b in banned:agg[b]=agg.get(b,0)+1
  for c in unsupported_names+attrs:callagg[c]=callagg.get(c,0)+1
  rows.append({'path':rel,'line':n.lineno,'function':n.name,'arg_count':len(n.args.args)+len(n.args.posonlyargs),
   'banned_nodes':banned,'unsupported_name_calls':unsupported_names,'attribute_calls':attrs,
   'statement_count':len(n.body),'source':src[:1800]})
rows.sort(key=lambda r:(len(r['banned_nodes'])+len(r['unsupported_name_calls'])+len(r['attribute_calls']),r['arg_count'],r['path'],r['line']))
minimal=[r for r in rows if len(r['banned_nodes'])<=1 and len(r['unsupported_name_calls'])<=1 and len(r['attribute_calls'])<=2][:40]
profiles={}
for r in rows:
 key=tuple(r['banned_nodes'])
 profiles[str(key)]=profiles.get(str(key),0)+1
report={'schema':'yado.g2.coding_whole_function_ast_census.v2','status':'PASS_AST_CENSUS',
 'active_source_count':len(sources),'top_level_function_count':len(rows),
 'banned_node_counts':dict(sorted(agg.items(),key=lambda kv:(-kv[1],kv[0]))),
 'call_counts':dict(sorted(callagg.items(),key=lambda kv:(-kv[1],kv[0]))[:80]),
 'banned_profiles':dict(sorted(profiles.items(),key=lambda kv:(-kv[1],kv[0]))),
 'minimal_extension_candidates':minimal,
 'semantic_boundary':'STATIC AST CENSUS ONLY. IT DOES NOT AUTHORIZE ANY NEW AST NODE, CALL, EXECUTION, REPAIR, OR CANONICAL CHANGE.'}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':report['status'],'top_level_function_count':len(rows),'banned_node_counts':report['banned_node_counts'],
 'top_call_counts':list(report['call_counts'].items())[:30],
 'minimal_extension_candidates':[{'path':r['path'],'function':r['function'],'args':r['arg_count'],'banned':r['banned_nodes'],'name_calls':r['unsupported_name_calls'],'attrs':r['attribute_calls']} for r in minimal[:25]],
 'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
