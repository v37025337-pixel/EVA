from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3

HEAD=REPO/'canonical/yado-main-head-g2.json'
MANIFEST=REPO/'canonical/yado-unified-core-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-discovery-v1.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

head=load(HEAD);manifest=load(MANIFEST)
active_sources=[x for x in manifest.get('active_runtime_sources',[]) if x.endswith('.py')]
if 'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3' not in head.get('active_capabilities',[]):
    raise RuntimeError('NEW_CANONICAL_COGNITIVE_LAYER_NOT_ACTIVE')

def stripped_function(node):
    q=copy.deepcopy(node)
    q.decorator_list=[]
    q.returns=None
    q.type_comment=None
    for a in list(q.args.posonlyargs)+list(q.args.args)+list(q.args.kwonlyargs):
        a.annotation=None
        a.type_comment=None
    q.args.defaults=[]
    q.args.kw_defaults=[None for _ in q.args.kwonlyargs]
    ast.fix_missing_locations(q)
    return ast.unparse(q)+'\n'

def callable_shape(node):
    if node.args.vararg is not None or node.args.kwarg is not None:return False
    if node.args.posonlyargs:return False
    if node.args.kwonlyargs:return False
    n=len(node.args.args)
    return 1<=n<=2

def input_grid(n):
    vals=[-5,-3,-2,-1,0,1,2,3,5,7]
    if n==1:return [(x,) for x in vals]
    return [(x,y) for x in vals for y in vals]

def output_ok(x):
    if isinstance(x,bool):return True
    if isinstance(x,int) and not isinstance(x,bool):return abs(x)<=100000
    if isinstance(x,float):return abs(x)<=100000 and x==x and x not in (float('inf'),float('-inf'))
    if isinstance(x,str):return len(x)<=128
    return False

rows=[]
scan_errors=[]
for rel in active_sources:
    p=REPO/rel
    if not p.exists():continue
    try:src=p.read_text(encoding='utf-8');tree=ast.parse(src)
    except Exception as e:
        scan_errors.append({'path':rel,'error':type(e).__name__+':'+str(e)});continue
    for node in tree.body:
        if not isinstance(node,ast.FunctionDef):continue
        if not callable_shape(node):continue
        fn_src=stripped_function(node)
        try:
            parsed=ast.parse(fn_src)
            fname=BoundedCompositionalProgramRepairV3._validate(parsed)
        except Exception as e:
            continue
        args=[a.arg for a in node.args.args]
        if fname!=node.name:continue
        successes=[];failures=[]
        for a in input_grid(len(args)):
            try:
                out=BoundedCompositionalProgramRepairV3.execute(fn_src,node.name,a)
                if output_ok(out):successes.append({'args':list(a),'output':out})
                else:failures.append({'args':list(a),'error':'OUTPUT_TYPE_OR_BOUND'})
            except Exception as e:
                failures.append({'args':list(a),'error':type(e).__name__})
        distinct={canon(x['output']) for x in successes}
        if len(successes)<8 or len(distinct)<2:continue
        op_count=sum(isinstance(x,(ast.BinOp,ast.BoolOp,ast.Compare)) for x in ast.walk(ast.parse(fn_src)))
        const_count=sum(isinstance(x,ast.Constant) and isinstance(x.value,(int,bool)) for x in ast.walk(ast.parse(fn_src)))
        branch_count=sum(isinstance(x,(ast.If,ast.IfExp)) for x in ast.walk(ast.parse(fn_src)))
        token='WF-'+sha(rel+'|'+str(node.lineno)+'|'+fn_src)[:16]
        rows.append({
          'token':token,'path':rel,'line':int(node.lineno),'function_name':node.name,
          'arg_names':args,'arg_count':len(args),'source':fn_src,'source_sha256':sha(fn_src),
          'successful_probe_count':len(successes),'failed_probe_count':len(failures),
          'distinct_output_count':len(distinct),'op_count':op_count,'const_count':const_count,
          'branch_count':branch_count,'sample_successes':successes[:12]
        })

rows.sort(key=lambda r:(r['path'],r['line'],r['function_name']))
files=sorted({r['path'] for r in rows})
branched=[r for r in rows if r['branch_count']>0]
report={
 'schema':'yado.g2.coding_whole_function_discovery.v1',
 'status':'PASS_DISCOVERY' if rows else 'WITHHOLD_NO_ADMISSIBLE_WHOLE_FUNCTIONS',
 'canonical_head_digest':head.get('canonical_head_digest'),
 'active_source_count':len(active_sources),'scan_error_count':len(scan_errors),
 'candidate_count':len(rows),'source_file_count':len(files),'branched_candidate_count':len(branched),
 'source_files':files,'candidates':rows,'scan_errors':scan_errors,
 'constraints':{
   'top_level_function_only':True,'positional_arg_count':[1,2],
   'no_varargs_kwargs_kwonly':True,'bounded_validator_required':True,
   'min_successful_integer_probes':8,'min_distinct_outputs':2,
   'no_external_model':True,'no_canonical_mutation':True
 },
 'semantic_boundary':'DISCOVERY ONLY. CANDIDATES ARE COMPLETE TOP-LEVEL FUNCTIONS FROM CURRENT ACTIVE G2 RUNTIME SOURCES THAT VALIDATE AS STANDALONE BOUNDED PROGRAMS AND EXECUTE ON A MATERIAL INTEGER PROBE SET. NO FUNCTION WAS SELECTED, MUTATED, REPAIRED, OR PROMOTED.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':report['status'],'active_source_count':len(active_sources),
 'candidate_count':len(rows),'source_file_count':len(files),'branched_candidate_count':len(branched),
 'top_candidates':[{'token':r['token'],'path':r['path'],'function':r['function_name'],'args':r['arg_count'],'branches':r['branch_count'],'ops':r['op_count'],'probes':r['successful_probe_count']} for r in rows[:20]],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not rows:raise SystemExit(2)
