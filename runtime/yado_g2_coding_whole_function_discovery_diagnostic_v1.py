from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3
MANIFEST=REPO/'canonical/yado-unified-core-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-discovery-diagnostic-v1.json'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def strip_fn(node):
    q=copy.deepcopy(node);q.decorator_list=[];q.returns=None;q.type_comment=None
    for a in list(q.args.posonlyargs)+list(q.args.args)+list(q.args.kwonlyargs):
        a.annotation=None;a.type_comment=None
    q.args.defaults=[];q.args.kw_defaults=[None for _ in q.args.kwonlyargs]
    ast.fix_missing_locations(q);return ast.unparse(q)+'\n'
m=load(MANIFEST);sources=[x for x in m.get('active_runtime_sources',[]) if x.endswith('.py')]
stats={'top_level_functions':0,'methods':0,'arg_counts':{},'validator_pass':0,'validator_fail':0,'validator_fail_types':{},
       'one_to_four_arg_validator_pass':0,'integer_probe_any_success':0,'integer_probe_8_success':0,'integer_probe_2_outputs':0}
examples=[]
vals=[-3,-1,0,1,2,4]
for rel in sources:
    p=REPO/rel
    if not p.exists():continue
    tree=ast.parse(p.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node,ast.FunctionDef):
            stats['top_level_functions']+=1
            n=len(node.args.args)+len(node.args.posonlyargs)
            stats['arg_counts'][str(n)]=stats['arg_counts'].get(str(n),0)+1
            src=strip_fn(node)
            try:BoundedCompositionalProgramRepairV3._validate(ast.parse(src));ok=True
            except Exception as e:
                ok=False;stats['validator_fail']+=1
                k=type(e).__name__+':'+str(e)
                stats['validator_fail_types'][k]=stats['validator_fail_types'].get(k,0)+1
            if ok:
                stats['validator_pass']+=1
                if 1<=n<=4 and node.args.vararg is None and node.args.kwarg is None and not node.args.kwonlyargs:
                    stats['one_to_four_arg_validator_pass']+=1
                    probes=[]
                    base=[0]*n
                    candidates=[]
                    for v in vals:
                        candidates.append(tuple([v]*n))
                        for pos in range(n):
                            a=list(base);a[pos]=v;candidates.append(tuple(a))
                    seen=set()
                    for args in candidates:
                        if args in seen:continue
                        seen.add(args)
                        try:
                            out=BoundedCompositionalProgramRepairV3.execute(src,node.name,args)
                            if isinstance(out,(bool,int,float,str)) and not (isinstance(out,str) and len(out)>128):
                                probes.append((args,out))
                        except Exception:pass
                    if probes:stats['integer_probe_any_success']+=1
                    if len(probes)>=8:stats['integer_probe_8_success']+=1
                    if len({canon(x[1]) for x in probes})>=2:stats['integer_probe_2_outputs']+=1
                    if len(examples)<30:
                        examples.append({'path':rel,'function':node.name,'arg_count':n,'probe_successes':len(probes),
                          'distinct_outputs':len({canon(x[1]) for x in probes}),'source':src[:1000]})
        elif isinstance(node,ast.ClassDef):
            stats['methods']+=sum(isinstance(x,ast.FunctionDef) for x in node.body)
report={'schema':'yado.g2.coding_whole_function_discovery_diagnostic.v1','status':'PASS_DIAGNOSTIC',
 'active_source_count':len(sources),'stats':stats,'examples':examples,
 'semantic_boundary':'DIAGNOSTIC ONLY; NO SELECTION, MUTATION, REPAIR, THRESHOLD CHANGE, OR CANONICAL MUTATION.'}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps(report,indent=2,sort_keys=True,default=str))
