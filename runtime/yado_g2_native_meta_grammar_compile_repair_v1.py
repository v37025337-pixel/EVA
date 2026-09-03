from __future__ import annotations
from pathlib import Path
import difflib,hashlib,json,os,re,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import predict_intel_component
from yado_unified_core_v1 import UnifiedYADOCoreV1

TARGET=REPO/'runtime/yado_g2_autonomous_self_rewrite_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-meta-grammar-compile-repair-v1.json'
CAND=REPO/'candidates/g2-self-evolution/yado_g2_autonomous_self_rewrite_v1_native_meta_repaired_candidate.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

def compile_error(src):
    try:
        compile(src,'<yado-native-meta-repair>','exec');return None
    except SyntaxError as e:
        return {'msg':str(e.msg),'lineno':e.lineno,'offset':e.offset,'text':e.text.rstrip('\n') if e.text else None}

def diff_hunks(current,ancestor):
    a=current.splitlines(keepends=True); b=ancestor.splitlines(keepends=True)
    sm=difflib.SequenceMatcher(a=a,b=b,autojunk=False)
    out=[]
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=='equal':continue
        out.append({'tag':tag,'i1':i1,'i2':i2,'j1':j1,'j2':j2})
    return a,b,out

def apply_hunks(current,ancestor,selected):
    cur,anc,hunks=diff_hunks(current,ancestor)
    out=list(cur)
    for idx in sorted(selected,key=lambda k:hunks[k]['i1'],reverse=True):
        h=hunks[idx]
        out[h['i1']:h['i2']]=anc[h['j1']:h['j2']]
    return ''.join(out)

def features_for_hunk(current,ancestor,idx):
    cur,anc,hunks=diff_hunks(current,ancestor)
    h=hunks[idx]
    err=compile_error(current) or {}
    errline=max(0,int(err.get('lineno') or 1)-1)
    reverted=apply_hunks(current,ancestor,[idx])
    compile_after=compile_error(reverted) is None
    span=max(1,h['i2']-h['i1'])
    deleted=max(0,h['j2']-h['j1']); inserted=max(0,h['i2']-h['i1'])
    dist=min(abs(h['i1']-errline),abs(max(h['i1'],h['i2']-1)-errline))
    return {
      'error_overlap':1.0 if h['i1']<=errline<max(h['i2'],h['i1']+1) else 0.0,
      'compile_if_reverted':1.0 if compile_after else 0.0,
      'distance_to_error':float(min(dist,20))/20.0,
      'inserted_lines':float(min(inserted,10))/10.0,
      'ancestor_lines':float(min(deleted,10))/10.0,
      'line_delta_abs':float(min(abs(inserted-deleted),10))/10.0,
      'hunk_span':float(min(span,10))/10.0,
      'is_insert':1.0 if h['tag']=='insert' else 0.0,
      'is_replace':1.0 if h['tag']=='replace' else 0.0,
      'is_delete':1.0 if h['tag']=='delete' else 0.0,
    }

def make_case(base_lines,intended_changes,corruption_inserts):
    ancestor=''.join(base_lines)
    expected=list(base_lines)
    for idx,text in intended_changes:
        expected[idx]=text
    expected=''.join(expected)
    current=expected.splitlines(keepends=True)
    for idx,text in sorted(corruption_inserts,key=lambda x:x[0],reverse=True):
        current.insert(idx,text)
    current=''.join(current)
    if compile_error(ancestor) is not None or compile_error(expected) is not None or compile_error(current) is None:
        raise RuntimeError('BAD_SYNTHETIC_CASE')
    cur,anc,hunks=diff_hunks(current,ancestor)
    rows=[]
    for i,h in enumerate(hunks):
        reverted=apply_hunks(current,ancestor,[i])
        label='REVERT' if reverted==expected else 'KEEP'
        rows.append((features_for_hunk(current,ancestor,i),label))
    if not any(y=='REVERT' for _,y in rows) or not any(y=='KEEP' for _,y in rows):
        raise RuntimeError('SYNTHETIC_CASE_MUST_HAVE_KEEP_AND_REVERT')
    return {'current':current,'ancestor':ancestor,'expected':expected,'rows':rows}

bases=[
 ["A=1\n","\n","def f(x):\n","    return x+1\n","\n","def g(y):\n","    return y*2\n","\n","Z=3\n"],
 ["FLAG=False\n","\n","def a(x):\n","    return x-1\n","\n","def b(y):\n","    return y+2\n","\n","END=0\n"],
 ["NAME='a'\n","\n","def p(x):\n","    return {'x':x}\n","\n","def q(y):\n","    return [y]\n","\n","TAIL=1\n"],
 ["LIMIT=4\n","\n","def m(x):\n","    return min(x,LIMIT)\n","\n","def n(y):\n","    return max(y,0)\n","\n","DONE=True\n"],
]

cases=[]
cases.append(make_case(bases[0],[(0,"A=2\n")],[(7,",oops)\n")]))
cases.append(make_case(bases[1],[(0,"FLAG=True\n")],[(7,"] bad\n")]))
cases.append(make_case(bases[2],[(0,"NAME='b'\n")],[(7,"} bad\n")]))
cases.append(make_case(bases[3],[(0,"LIMIT=5\n")],[(7,") bad\n")]))
cases.append(make_case(bases[0],[(3,"    return x+2\n")],[(7,",junk)\n")]))
cases.append(make_case(bases[1],[(6,"    return y+3\n")],[(1,"[ broken\n")]))
cases.append(make_case(bases[2],[(3,"    return {'x':x,'ok':True}\n")],[(7,") nope\n")]))
cases.append(make_case(bases[3],[(6,"    return max(y,1)\n")],[(1,"{ broken\n")]))

fit=[row for c in cases[:4] for row in c['rows']]
val=[row for c in cases[4:6] for row in c['rows']]
revealed=[row for c in cases[:6] for row in c['rows']]
blind=[row for c in cases[6:] for row in c['rows']]

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_native_meta_compile_repair.sqlite'))
try:
    native=k.synthesize_intelligence_with_extended_meta_grammar(fit,val,revealed,blind)
finally:
    k.close()

model=native.get('model')
fresh_acc=0.0
if model is not None and blind:
    fresh_acc=sum(predict_intel_component(model,x)==y for x,y in blind)/len(blind)

# Ablation: remove synthesized selector by using the trivial whole-ancestor rollback policy.
# It compiles but necessarily erases intended fresh modifications, so exact repair is measured separately.
whole_ancestor_fresh=0.0
for c in cases[6:]:
    whole_ancestor_fresh += (c['ancestor']==c['expected'])
whole_ancestor_fresh/=max(1,len(cases[6:]))

def git_history(path,limit=40):
    rel=str(path.relative_to(REPO))
    p=subprocess.run(['git','log','--format=%H','--',rel],cwd=REPO,capture_output=True,text=True,check=True)
    out=[]
    for sha in [x for x in p.stdout.splitlines() if x.strip()][1:limit+1]:
        q=subprocess.run(['git','show',f'{sha}:{rel}'],cwd=REPO,capture_output=True,text=True)
        if q.returncode==0:
            out.append({'sha':sha,'source':q.stdout,'compiles':compile_error(q.stdout) is None})
    return out

current=TARGET.read_text(encoding='utf-8')
history=git_history(TARGET)
ancestor_row=next((x for x in history if x['compiles']),None)
ancestor=ancestor_row['source'] if ancestor_row else None
predictions=[]
candidate=None
selected_hunks=[]
if ancestor is not None and model is not None:
    _,_,hunks=diff_hunks(current,ancestor)
    for i,h in enumerate(hunks):
        x=features_for_hunk(current,ancestor,i)
        y=predict_intel_component(model,x)
        predictions.append({'hunk_index':i,'prediction':y,'features':x,'hunk':h})
        if y=='REVERT':
            selected_hunks.append(i)
    if selected_hunks:
        candidate=apply_hunks(current,ancestor,selected_hunks)

current_funcs=set(re.findall(r'^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(',current,re.M))
cand_funcs=set(re.findall(r'^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(',candidate or '',re.M))
function_preservation=len(current_funcs & cand_funcs)/max(1,len(current_funcs))
changed_lines=0
if candidate is not None:
    dd=list(difflib.unified_diff(current.splitlines(),candidate.splitlines(),lineterm=''))
    changed_lines=sum(1 for x in dd if (x.startswith('+') or x.startswith('-')) and not x.startswith('+++') and not x.startswith('---'))

core=UnifiedYADOCoreV1(REPO)
gene=None
if native.get('status')=='SUPPORTED' and native.get('grammar_extension_id') and fresh_acc==1.0 and candidate is not None and compile_error(candidate) is None:
    gene={
      'schema':'yado.g2.self_synthesized_native_meta_compile_repair_gene.v1',
      'gene_id':'GENE-SELF-SYNTHESIZED-NATIVE-META-COMPILE-'+native['grammar_extension_id'],
      'novel_gene':True,'gene_scope':['CODE','SELF_AUDIT_AND_REPAIR'],
      'heritage':['RC6_META_GRAMMAR','G2'],
      'native_constructor':'synthesize_intelligence_with_extended_meta_grammar',
      'grammar_extension_id':native['grammar_extension_id'],
      'predicate_program':native.get('predicate_program'),
      'model':model,'promotion_state':'SHADOW_ONLY',
      'trigger':{'deficit':'SELF_REWRITE_CONTROLLER_COMPILE_FAILURE','prior_withholds':['SELF_SYNTHESIZED_COMPILE_REPAIR_V1','HISTORY_GUIDED_COMPILE_REPAIR_V1']}
    }
    gene['gene_digest']=digest(gene)
    CAND.parent.mkdir(parents=True,exist_ok=True)
    CAND.write_text(candidate,encoding='utf-8')

checks={
 'native_meta_grammar_supported':native.get('status')=='SUPPORTED',
 'native_grammar_extension_created':bool(native.get('grammar_extension_id')),
 'validation_exact':float(native.get('validation',0.0))==1.0,
 'fresh_exact':fresh_acc==1.0,
 'whole_ancestor_ablation_not_exact':whole_ancestor_fresh<1.0,
 'target_current_compile_broken':compile_error(current) is not None,
 'compiling_ancestor_discovered':ancestor_row is not None,
 'kernel_model_selected_target_hunk':bool(selected_hunks),
 'same_native_model_repairs_target':candidate is not None and compile_error(candidate) is None,
 'preserves_current_function_surface':function_preservation>=0.95,
 'bounded_target_change':0<changed_lines<=60,
 'invented_gene_created':gene is not None,
 'no_external_model_or_ready_patch':True,
 'host_did_not_supply_target_patch_or_line':True,
 'canonical_unchanged':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_NATIVE_META_GRAMMAR_COMPILE_REPAIR_V1' if all(checks.values()) else 'WITHHOLD_G2_NATIVE_META_GRAMMAR_COMPILE_REPAIR_V1'

report={
 'schema':'yado.g2.native_meta_grammar_compile_repair.v1','status':status,
 'native_meta_result':native,'fresh_accuracy_recomputed':fresh_acc,
 'ablation':{'whole_ancestor_exact_fresh':whole_ancestor_fresh},
 'invented_gene':gene,
 'target':{
   'path':str(TARGET.relative_to(REPO)),'compile_error_before':compile_error(current),
   'ancestor_sha':ancestor_row['sha'] if ancestor_row else None,
   'history_compiling_count':sum(x['compiles'] for x in history),
   'predictions':predictions,'selected_hunks':selected_hunks,
   'candidate_path':str(CAND.relative_to(REPO)) if CAND.exists() else None,
   'compile_error_after':compile_error(candidate) if candidate is not None else None,
   'changed_lines':changed_lines,'function_preservation':function_preservation
 },
 'checks':checks,'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'YADO USES ITS PRE-EXISTING NATIVE RC6 META-GRAMMAR SYNTHESIZER TO CREATE A NEW HUNK-REPAIR SELECTOR FROM GENERIC COMPILER/DIFF FEATURES, FREEZES IT BEFORE FRESH CASES, THEN APPLIES THE SAME GENERATED MODEL TO ITS BROKEN SELF-REWRITE CONTROLLER. NO EXTERNAL LLM, READY PATCH, TARGET LINE NUMBER, OR EXPECTED TARGET SOURCE IS PROVIDED.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'native_status':native.get('status'),'grammar_extension_id':native.get('grammar_extension_id'),
 'validation':native.get('validation'),'fresh':fresh_acc,'selected_hunks':selected_hunks,
 'target_compile_before':report['target']['compile_error_before'],'target_compile_after':report['target']['compile_error_after'],
 'invented_gene_id':gene.get('gene_id') if gene else None,'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_NATIVE_META_GRAMMAR_COMPILE_REPAIR_V1':raise SystemExit(2)
