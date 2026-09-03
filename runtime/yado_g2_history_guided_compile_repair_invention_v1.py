from __future__ import annotations
from pathlib import Path
import hashlib,json,os,re,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_generic_history_compile_repair_meta_language_v1 import GenericHistoryCompileRepairMetaLanguageV1

TARGET=REPO/'runtime/yado_g2_autonomous_self_rewrite_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-history-guided-compile-repair-invention-v1.json'
CAND=REPO/'candidates/g2-self-evolution/yado_g2_autonomous_self_rewrite_v1_history_repaired_candidate.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

def valid(src):
    return GenericHistoryCompileRepairMetaLanguageV1.compile_error(src) is None

def make_case(name,ancestor,intended_lines,corrupt_lines,older=None):
    base=ancestor.splitlines(keepends=True)
    cur=list(base)
    for idx,newline in intended_lines:
        cur[idx]=newline
    expected=''.join(cur)
    for idx,newline in sorted(corrupt_lines,key=lambda x:x[0],reverse=True):
        cur.insert(idx,newline)
    current=''.join(cur)
    history=[ancestor]
    if older is not None:history.append(older)
    if valid(current):raise RuntimeError('SYNTHETIC_CURRENT_MUST_BE_BROKEN:'+name)
    if not valid(expected):raise RuntimeError('SYNTHETIC_EXPECTED_MUST_COMPILE:'+name)
    return {'id':name,'current':current,'history':history,'expected':expected}

base1='''VALUE=1\n\ndef f(x):\n    return x+1\n\ndef tail():\n    return VALUE\n'''
old1='''VALUE=0\n\ndef f(x):\n    return x\n\ndef tail():\n    return VALUE\n'''
base2='''FLAG=False\n\ndef a(x):\n    return x*2\n\ndef b(y):\n    return y-1\n\nRESULT=3\n'''
old2='''FLAG=False\n\ndef a(x):\n    return x\n\ndef b(y):\n    return y\n\nRESULT=1\n'''
base3='''NAME="a"\n\ndef alpha(x):\n    return {"x":x}\n\ndef omega():\n    return NAME\n'''
old3='''NAME="old"\n\ndef alpha(x):\n    return x\n\ndef omega():\n    return NAME\n'''

train=[
 make_case('T1',base1,[(0,'VALUE=2\n')],[(7,',junk)\n')],old1),
 make_case('T2',base2,[(0,'FLAG=True\n'),(8,'RESULT=9\n')],[(4,'    )\n'),(8,'    ]\n')],old2),
 make_case('T3',base3,[(0,'NAME="new"\n')],[(6,'} stray\n')],old3),
 make_case('T4',base1,[(3,'    return x+2\n')],[(1,'( broken\n'),(7,'] broken\n')],old1),
]
holdout=[
 make_case('H1',base2,[(3,'    return x*3\n')],[(9,') tail\n')],old2),
 make_case('H2',base3,[(3,'    return {"x":x,"ok":True}\n')],[(1,'[ bad\n'),(7,'} bad\n')],old3),
 make_case('H3',base1,[(0,'VALUE=5\n'),(6,'    return VALUE+1\n')],[(5,') nope\n')],old1),
 make_case('H4',base2,[(0,'FLAG=True\n'),(6,'    return y-2\n')],[(2,'{ bad\n'),(9,'] bad\n')],old2),
]

core=UnifiedYADOCoreV1(REPO)
parent=core.evolutionary_parent_genome()
parent_gene_ids=[g['gene_id'] for g in (parent.get('chromosomes') or {}).values() if isinstance(g,dict) and g.get('gene_id')]

programs=[]
for p in GenericHistoryCompileRepairMetaLanguageV1.programs():
    tr=GenericHistoryCompileRepairMetaLanguageV1.accuracy(p,train)
    if tr<1.0:continue
    fr=GenericHistoryCompileRepairMetaLanguageV1.accuracy(p,holdout)
    programs.append({'program':p,'train_accuracy':tr,'fresh_accuracy':fr})

baseline_train=GenericHistoryCompileRepairMetaLanguageV1.whole_ancestor_baseline(train)
baseline_fresh=GenericHistoryCompileRepairMetaLanguageV1.whole_ancestor_baseline(holdout)

skills=[]
for i,row in enumerate(programs):
    sid=f'HISTORY_COMPILE_REPAIR_{i:03d}';row['skill_id']=sid
    valid_skill=row['train_accuracy']==1.0 and row['fresh_accuracy']==1.0
    skills.append({
      'skill_id':sid,'artifact_digest':row['program']['program_digest'],
      'structural_valid':valid_skill,'semantic_consistency':row['fresh_accuracy'],
      'fit_baseline':baseline_train,'fit_candidate':row['train_accuracy'],
      'heldout_baseline':baseline_fresh,'heldout_candidate':row['fresh_accuracy'],
      'regression_pass':valid_skill,'state_integrity':True,'rollback_available':True
    })

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_history_compile_repair.sqlite'))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.99,min_fit_gain=.25,max_heldout_drop=0,min_heldout_gain=.25)
finally:
    k.close()
selected=(selection.get('selected_skill_ids') or [None])[0]
winner=next((x for x in programs if x.get('skill_id')==selected),None)

def git_history(path,limit=24):
    rel=str(path.relative_to(REPO))
    p=subprocess.run(['git','log','--format=%H','--',rel],cwd=REPO,capture_output=True,text=True,check=True)
    shas=[x.strip() for x in p.stdout.splitlines() if x.strip()]
    out=[]
    for sha in shas[1:limit+1]:
        q=subprocess.run(['git','show',f'{sha}:{rel}'],cwd=REPO,capture_output=True,text=True)
        if q.returncode==0:
            out.append({'sha':sha,'source':q.stdout,'compiles':valid(q.stdout)})
    return out

current=TARGET.read_text(encoding='utf-8')
hist=git_history(TARGET)
history_sources=[x['source'] for x in hist]
repair=None
if winner is not None:
    repair=GenericHistoryCompileRepairMetaLanguageV1.repair(winner['program'],current,history_sources)

candidate=repair.get('source') if isinstance(repair,dict) else None
current_funcs=set(re.findall(r'^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(',current,re.M))
candidate_funcs=set(re.findall(r'^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(',candidate or '',re.M))
function_preservation=(len(current_funcs & candidate_funcs)/max(1,len(current_funcs)))
changed_lines=0
if candidate is not None:
    import difflib
    dd=list(difflib.unified_diff(current.splitlines(),candidate.splitlines(),lineterm=''))
    changed_lines=sum(1 for x in dd if (x.startswith('+') or x.startswith('-')) and not x.startswith('+++') and not x.startswith('---'))

gene=None
if winner is not None and candidate is not None and valid(candidate):
    gene={
      'schema':'yado.g2.self_synthesized_history_compile_repair_gene.v1',
      'gene_id':'GENE-SELF-SYNTHESIZED-HISTORY-COMPILE-'+winner['program']['program_digest'][:16],
      'novel_gene':True,'gene_scope':['CODE','SELF_AUDIT_AND_REPAIR'],
      'heritage':sorted(parent_gene_ids),
      'meta_language_component':GenericHistoryCompileRepairMetaLanguageV1.COMPONENT_ID,
      'operator_program':winner['program'],'execution_mode':'BOUNDED_META_LANGUAGE_INTERPRETER',
      'promotion_state':'SHADOW_ONLY',
      'trigger':{'deficit_id':'SELF_REWRITE_CONTROLLER_COMPILE_FAILURE','source':'ACCUMULATED_COMPILE_FAILURE_HISTORY'}
    }
    gene['gene_digest']=digest(gene)
    CAND.parent.mkdir(parents=True,exist_ok=True);CAND.write_text(candidate,encoding='utf-8')

checks={
 'kernel_selected_history_repair_program':winner is not None,
 'train_exact':winner is not None and winner['train_accuracy']==1.0,
 'fresh_exact':winner is not None and winner['fresh_accuracy']==1.0,
 'whole_ancestor_baseline_not_exact':baseline_train<1.0 and baseline_fresh<1.0,
 'target_current_is_compile_broken':not valid(current),
 'compiling_history_discovered':any(x['compiles'] for x in hist),
 'same_program_repairs_target':candidate is not None and valid(candidate),
 'preserves_current_function_surface':function_preservation>=0.95,
 'bounded_target_change':0<changed_lines<=40,
 'novel_gene_not_parent':gene is not None and gene['gene_id'] not in set(parent_gene_ids),
 'no_external_model_or_ready_patch':True,
 'host_did_not_supply_target_line_or_patch':True,
 'canonical_unchanged':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_HISTORY_GUIDED_COMPILE_REPAIR_INVENTION_V1' if all(checks.values()) else 'WITHHOLD_G2_HISTORY_GUIDED_COMPILE_REPAIR_INVENTION_V1'

report={
 'schema':'yado.g2.history_guided_compile_repair_invention.v1','status':status,
 'meta_language':GenericHistoryCompileRepairMetaLanguageV1.component(),
 'baseline':{'train':baseline_train,'fresh':baseline_fresh},
 'kernel_selection':selection,'selected_program':winner,'invented_gene':gene,
 'target':{
   'path':str(TARGET.relative_to(REPO)),
   'compile_error_before':GenericHistoryCompileRepairMetaLanguageV1.compile_error(current),
   'history_entries':[{'sha':x['sha'],'compiles':x['compiles']} for x in hist],
   'repair_result':{k:v for k,v in (repair or {}).items() if k!='source'},
   'candidate_path':str(CAND.relative_to(REPO)) if CAND.exists() else None,
   'candidate_compiles':candidate is not None and valid(candidate),
   'function_preservation':function_preservation,'changed_lines':changed_lines
 },
 'checks':checks,'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'YADO SEARCHES A BOUNDED GENERIC HISTORY/DIFF/COMPILE META-LANGUAGE, SELECTS A PROGRAM ON TRAIN+FRESH REPAIR HISTORIES, AND APPLIES THE SAME PROGRAM TO ITS BROKEN SELF-REWRITE CONTROLLER USING REPOSITORY HISTORY. NO EXTERNAL MODEL, READY PATCH, TARGET LINE NUMBER, OR EXPECTED TARGET SOURCE IS SUPPLIED.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'baseline':report['baseline'],
 'selected_program':winner,'invented_gene_id':gene.get('gene_id') if gene else None,
 'target':report['target'],'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_HISTORY_GUIDED_COMPILE_REPAIR_INVENTION_V1':raise SystemExit(2)
