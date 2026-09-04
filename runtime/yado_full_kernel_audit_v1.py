from __future__ import annotations
from pathlib import Path
import ast, hashlib, json, os, py_compile, re, subprocess, sys, time

ROOT=Path(__file__).resolve().parent.parent
RUNTIME=ROOT/'runtime'
OUTDIR=ROOT/'audits'
OUTDIR.mkdir(exist_ok=True)
REPORT=OUTDIR/'yado-full-kernel-audit-v1-report.json'
SUMMARY=OUTDIR/'yado-full-kernel-audit-v1-summary.md'

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(p.read_bytes())
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str).encode()
def digest_without(o,field):
    x=dict(o);x.pop(field,None);return sha_bytes(canon(x))
def run(cmd,timeout=120):
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
    return {'code':p.returncode,'stdout':p.stdout[-12000:],'stderr':p.stderr[-12000:]}
def add(findings,severity,code,message,details=None):
    findings.append({'severity':severity,'code':code,'message':message,'details':details})

started=time.time()
findings=[]

# ---------- repository inventory ----------
tracked=run(['git','ls-files'])
files=[x for x in tracked['stdout'].splitlines() if x]
# ls-files output may be truncated by helper; use pathlib for exact working tree inventory.
all_files=[p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts]
inventory={}
for p in all_files:
    rel=p.relative_to(ROOT).as_posix();top=rel.split('/')[0]
    inventory[top]=inventory.get(top,0)+1

# ---------- canonical / ledger ----------
head=load(ROOT/'canonical/yado-main-head-g2.json')
core=load(ROOT/'canonical/yado-unified-core-v1.json')
prov=load(ROOT/'canonical/yado-algorithm-provenance-registry-v1.json')
ledger=load(ROOT/'architecture/evolution-ledger.json')
binding=prov.get('current_g2_binding',{})

fronts={
 'head':head.get('current_frontier'),
 'core':core.get('current_frontier'),
 'provenance':binding.get('frontier'),
 'ledger':(ledger.get('open_deficits') or [None])[0],
}
if len(set(fronts.values()))!=1:
    add(findings,'CRITICAL','FRONTIER_DRIFT','Current frontier disagrees across canonical layers.',fronts)
if head.get('canonical_head_digest')!=ledger.get('current_head_digest'):
    add(findings,'CRITICAL','HEAD_LEDGER_DIGEST_DRIFT','Canonical head digest differs from ledger current_head_digest.',
        {'head':head.get('canonical_head_digest'),'ledger':ledger.get('current_head_digest')})
if head.get('generation_id')!=ledger.get('current_head'):
    add(findings,'HIGH','GENERATION_LABEL_DRIFT','Head generation_id differs from ledger current_head.',
        {'head':head.get('generation_id'),'ledger':ledger.get('current_head')})
for obj,field,name in [(head,'canonical_head_digest','head'),(core,'core_digest','core'),(prov,'registry_digest','provenance')]:
    actual=digest_without(obj,field);decl=obj.get(field)
    if actual!=decl:add(findings,'CRITICAL','SELF_DIGEST_MISMATCH',f'{name} self digest mismatch.',{'declared':decl,'actual':actual})

sys.path.insert(0,str(RUNTIME))
try:
    from yado_evolution_ledger_v2 import validate_ledger_v2
    validate_ledger_v2(ledger)
    ledger_validation='PASS'
except Exception as e:
    ledger_validation='FAIL'
    add(findings,'CRITICAL','LEDGER_VALIDATION_FAILED','Evolution ledger validation failed.',repr(e))

guard=run([sys.executable,'runtime/yado_canonical_invariant_guard_v1.py'],timeout=90)
if guard['code']!=0:add(findings,'CRITICAL','CANONICAL_GUARD_FAILED','Canonical invariant guard failed.',guard)

# ---------- JSON integrity ----------
json_errors=[]
json_count=0
for top in ['canonical','architecture','candidates','resources','receipts','experience']:
    d=ROOT/top
    if not d.exists():continue
    for p in d.rglob('*.json'):
        json_count+=1
        try: json.loads(p.read_text(encoding='utf-8'))
        except Exception as e: json_errors.append({'path':p.relative_to(ROOT).as_posix(),'error':repr(e)})
if json_errors:add(findings,'HIGH','JSON_PARSE_ERRORS',f'{len(json_errors)} JSON artifacts are invalid.',json_errors[:100])

# ---------- Python syntax and local import graph ----------
py_files=list(RUNTIME.rglob('*.py'))
compile_errors=[]
for p in py_files:
    try: py_compile.compile(str(p),doraise=True)
    except Exception as e:compile_errors.append({'path':p.relative_to(ROOT).as_posix(),'error':repr(e)})
if compile_errors:add(findings,'CRITICAL','PYTHON_COMPILE_ERRORS',f'{len(compile_errors)} runtime Python files fail compilation.',compile_errors[:100])

module_names=set()
for p in py_files:
    rel=p.relative_to(RUNTIME).with_suffix('')
    parts=list(rel.parts)
    if parts[-1]=='__init__':parts=parts[:-1]
    if parts:module_names.add('.'.join(parts))
    module_names.add(p.stem)

unresolved=[]
parse_errors=[]
import_edges=0
for p in py_files:
    try:tree=ast.parse(p.read_text(encoding='utf-8',errors='replace'))
    except Exception as e:
        parse_errors.append({'path':p.relative_to(ROOT).as_posix(),'error':repr(e)});continue
    for n in ast.walk(tree):
        names=[]
        if isinstance(n,ast.Import):names=[a.name for a in n.names]
        elif isinstance(n,ast.ImportFrom) and n.module:names=[n.module]
        for name in names:
            if not name.startswith('yado'):continue
            import_edges+=1
            ok=name in module_names or any(m.startswith(name+'.') for m in module_names) or name.split('.')[0] in module_names
            if not ok:unresolved.append({'path':p.relative_to(ROOT).as_posix(),'import':name})
if parse_errors:add(findings,'CRITICAL','AST_PARSE_ERRORS',f'{len(parse_errors)} runtime files fail AST parsing.',parse_errors[:100])
if unresolved:add(findings,'HIGH','UNRESOLVED_LOCAL_IMPORTS',f'{len(unresolved)} local YADO imports do not resolve in runtime tree.',unresolved[:100])

# ---------- active runtime / integrity manifest ----------
missing_active=[]
for s in core.get('active_runtime_sources',[]):
    if not (ROOT/s).exists():missing_active.append(s)
if missing_active:add(findings,'CRITICAL','MISSING_ACTIVE_RUNTIME','Canonical active runtime source is missing.',missing_active)

manifest=core.get('runtime_integrity_manifest',{})
manifest_sources=manifest.get('sources',{}) if isinstance(manifest,dict) else {}
manifest_mismatch=[]
for s,d in manifest_sources.items():
    p=ROOT/s
    if not p.exists():manifest_mismatch.append({'path':s,'problem':'missing'})
    else:
        actual=sha_file(p)
        if actual!=d:manifest_mismatch.append({'path':s,'problem':'digest','declared':d,'actual':actual})
if manifest_mismatch:add(findings,'CRITICAL','RUNTIME_MANIFEST_DRIFT',f'{len(manifest_mismatch)} runtime manifest entries drifted.',manifest_mismatch[:100])
if manifest_sources:
    calc=sha_bytes(canon({k:manifest_sources[k] for k in sorted(manifest_sources)}))
    if calc!=manifest.get('manifest_digest'):
        add(findings,'CRITICAL','RUNTIME_MANIFEST_SELF_DIGEST','Runtime integrity manifest digest does not match its source map.',
            {'declared':manifest.get('manifest_digest'),'actual':calc})

# ---------- exact duplicate / module collision inventory ----------
by_sha={}
for p in py_files:
    by_sha.setdefault(sha_file(p),[]).append(p.relative_to(ROOT).as_posix())
duplicate_groups=[v for v in by_sha.values() if len(v)>1]
by_stem={}
for p in py_files:by_stem.setdefault(p.stem,[]).append(p.relative_to(ROOT).as_posix())
stem_collisions={k:v for k,v in by_stem.items() if len(v)>1}

# ---------- path references from canonical ----------
ref_pattern=re.compile(r'^(runtime|canonical|architecture|resources|receipts|candidates|experience)/[^:*+]+\.(py|json)$')
missing_refs=[]
def walk(o,where=''):
    if isinstance(o,dict):
        for k,v in o.items():walk(v,where+'/'+str(k))
    elif isinstance(o,list):
        for i,v in enumerate(o):walk(v,where+f'/{i}')
    elif isinstance(o,str) and ref_pattern.match(o):
        if not (ROOT/o).exists():missing_refs.append({'where':where,'path':o})
for name,obj in [('head',head),('core',core),('provenance',prov)]:
    walk(obj,name)
if missing_refs:add(findings,'HIGH','MISSING_CANONICAL_REFERENCES',f'{len(missing_refs)} canonical file references point to missing paths.',missing_refs[:100])

# ---------- workflows ----------
workflows=list((ROOT/'.github/workflows').glob('*.y*ml'))
generated_contract_path=ROOT/'.github/yado-generated-workflow-artifacts-v1.json'
generated_contract=json.loads(generated_contract_path.read_text(encoding='utf-8')) if generated_contract_path.exists() else {'workflows':{}}
generated_by_workflow={k:set(v or []) for k,v in (generated_contract.get('workflows') or {}).items()}
workflow_ref_missing=[]
workflow_generated_absent=[]
workflow_branch_counts={}
workflow_request_triggers=0
path_re=re.compile(r'(?<![A-Za-z0-9_])((?:runtime|canonical|architecture|resources|candidates)/[A-Za-z0-9_./-]+\.(?:py|json))')
for p in workflows:
    txt=p.read_text(encoding='utf-8',errors='replace')
    for m in path_re.finditer(txt):
        rel=m.group(1)
        if not (ROOT/rel).exists():
            if rel in generated_by_workflow.get(p.name,set()):
                workflow_generated_absent.append({'workflow':p.name,'path':rel})
            else:
                workflow_ref_missing.append({'workflow':p.name,'path':rel})
    if '-request.json' in txt:workflow_request_triggers+=1
    for b in re.findall(r'branches:\s*\[([^\]]+)\]',txt):
        for x in b.split(','):
            key=x.strip().strip("'\"")
            workflow_branch_counts[key]=workflow_branch_counts.get(key,0)+1
if workflow_ref_missing:add(findings,'HIGH','BROKEN_WORKFLOW_STATIC_REFERENCES',f'{len(workflow_ref_missing)} workflow references point to missing files.',workflow_ref_missing[:150])

# Optional YAML parser
yaml_errors=[]
try:
    import yaml
    for p in workflows:
        try:yaml.safe_load(p.read_text(encoding='utf-8'))
        except Exception as e:yaml_errors.append({'workflow':p.name,'error':repr(e)})
except Exception as e:
    add(findings,'MEDIUM','YAML_PARSER_UNAVAILABLE','PyYAML unavailable; workflow syntax parse skipped.',repr(e))
if yaml_errors:add(findings,'HIGH','WORKFLOW_YAML_ERRORS',f'{len(yaml_errors)} workflow files fail YAML parsing.',yaml_errors[:100])

# ---------- branches / physical closure ----------
branches=[]
br=run(['git','for-each-ref','--format=%(refname:short)','refs/remotes/origin'])
refs=[x.strip() for x in br['stdout'].splitlines() if x.strip() and x.strip()!='origin/HEAD']
for ref in refs:
    name=ref.removeprefix('origin/')
    if name=='yado-architecture-shadow-search':continue
    cnt=run(['git','rev-list','--left-right','--count',f'HEAD...{ref}'])
    try:left,right=[int(x) for x in cnt['stdout'].strip().split()[:2]]
    except:left=right=-1
    unique=run(['git','log','--format=%H%x09%s',f'HEAD..{ref}'])
    commits=[]
    changed=set()
    for line in unique['stdout'].splitlines():
        if not line.strip():continue
        sha,msg=(line.split('\t',1)+[''])[:2];commits.append({'sha':sha,'message':msg})
        ch=run(['git','diff-tree','--no-commit-id','--name-only','-r',sha])
        changed.update(x for x in ch['stdout'].splitlines() if x)
    exact=0;drift=[];branch_only=[]
    for path in sorted(changed):
        hp=run(['git','rev-parse',f'HEAD:{path}'])
        bp=run(['git','rev-parse',f'{ref}:{path}'])
        if bp['code']!=0:continue
        if hp['code']!=0:branch_only.append(path)
        elif hp['stdout'].strip()==bp['stdout'].strip():exact+=1
        else:drift.append(path)
    branches.append({'branch':name,'active_only_commits':left,'branch_only_commits':right,
        'unique_commits':commits,'unique_changed_path_count':len(changed),'exact_tip_path_matches':exact,
        'drift_paths':drift[:80],'branch_only_paths':branch_only[:80]})

diverged=[b for b in branches if b['branch_only_commits']>0]
if diverged:
    add(findings,'HIGH','PHYSICAL_BRANCH_DIVERGENCE',
        f'{len(diverged)} historical branches retain commits not in active branch ancestry. Logical closure is not physical Git closure.',
        [{'branch':b['branch'],'branch_only_commits':b['branch_only_commits'],'drift_paths':len(b['drift_paths']),'branch_only_paths':len(b['branch_only_paths'])} for b in diverged])

# ---------- architecture planes ----------
planes=[]
for p in core.get('planes',[]):
    planes.append({'plane_id':p.get('plane_id'),'active_components':p.get('active_components',[]),'frontier':p.get('frontier')})

severity_rank={'CRITICAL':4,'HIGH':3,'MEDIUM':2,'LOW':1,'INFO':0}
max_severity=max((severity_rank.get(x['severity'],0) for x in findings),default=0)
status='PASS' if max_severity<2 else ('WITHHOLD' if max_severity==2 else 'FAIL_AUDIT')

report={
 'schema':'yado.full_kernel_audit.v1',
 'status':status,
 'audited_commit':run(['git','rev-parse','HEAD'])['stdout'].strip(),
 'elapsed_seconds':time.time()-started,
 'inventory':inventory,
 'counts':{
   'runtime_python_files':len(py_files),'json_files':json_count,'workflow_files':len(workflows),
   'active_runtime_sources':len(core.get('active_runtime_sources',[])),
   'active_capabilities':len(head.get('active_capabilities',[])),
   'architecture_planes':len(planes),'ledger_events':ledger.get('event_count'),
   'duplicate_python_groups':len(duplicate_groups),'module_stem_collisions':len(stem_collisions),
   'local_import_edges':import_edges,'historical_branches_audited':len(branches)
 },
 'canonical':{
   'generation':head.get('generation_id'),'g3_genesis_performed':head.get('g3_genesis_performed'),
   'frontiers':fronts,'head_digest':head.get('canonical_head_digest'),
   'ledger_validation':ledger_validation,'canonical_guard':'PASS' if guard['code']==0 else 'FAIL',
   'execution_label':binding.get('current_execution_label')
 },
 'planes':planes,
 'code':{
   'compile_error_count':len(compile_errors),'unresolved_local_import_count':len(unresolved),
   'duplicate_groups':duplicate_groups[:100],'stem_collisions':stem_collisions
 },
 'workflows':{
   'count':len(workflows),'static_missing_reference_count':len(workflow_ref_missing),'declared_generated_absent_count':len(workflow_generated_absent),
   'yaml_error_count':len(yaml_errors),'request_trigger_count':workflow_request_triggers,
   'branch_trigger_counts':workflow_branch_counts
 },
 'branches':branches,
 'findings':sorted(findings,key=lambda x:-severity_rank.get(x['severity'],0))
}
REPORT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

lines=[
 '# YADO Full Kernel Audit V1','',
 f"- Status: **{status}**",
 f"- Commit: `{report['audited_commit']}`",
 f"- Generation: `{head.get('generation_id')}`; G3 started: `{head.get('g3_genesis_performed')}`",
 f"- Frontier: `{fronts['head']}`",
 f"- Runtime Python: {len(py_files)}; workflows: {len(workflows)}; JSON artifacts: {json_count}; ledger events: {ledger.get('event_count')}",
 f"- Canonical guard: {report['canonical']['canonical_guard']}; ledger: {ledger_validation}",
 '',
 '## Findings'
]
if findings:
    for f in report['findings']:
        lines.append(f"- **{f['severity']} {f['code']}** — {f['message']}")
else:lines.append('- No audit findings.')
lines += ['','## Branches']
for b in branches:
    lines.append(f"- `{b['branch']}`: active-only {b['active_only_commits']}, branch-only {b['branch_only_commits']}, drift paths {len(b['drift_paths'])}, branch-only paths {len(b['branch_only_paths'])}.")
SUMMARY.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'findings':report['findings'],'counts':report['counts'],'canonical':report['canonical']},indent=2,default=str))
