from __future__ import annotations
from pathlib import Path
import ast,json,re,subprocess

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'audits'/'yado-security-audit-v1-report.json'
OUT.parent.mkdir(exist_ok=True)

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def run(cmd):
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    return p.returncode,p.stdout,p.stderr

findings=[]
def add(sev,code,msg,details=None):
    findings.append({'severity':sev,'code':code,'message':msg,'details':details})

rc,out,err=run(['git','ls-files'])
tracked=[ROOT/x for x in out.splitlines() if x.strip()]
patterns=[
 ('PRIVATE_KEY',re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')),
 ('GITHUB_TOKEN',re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b')),
 ('GITHUB_PAT',re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b')),
 ('OPENAI_KEY',re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b')),
 ('AWS_ACCESS_KEY',re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
 ('GOOGLE_API_KEY',re.compile(r'\bAIza[0-9A-Za-z_-]{35}\b')),
]
generic=re.compile(r'(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*["\']([^"\']{12,})["\']')
secret_hits=[]
generic_hits=[]
for p in tracked:
    try:
        b=p.read_bytes()
        if b'\x00' in b or len(b)>3_000_000: continue
        s=b.decode('utf-8')
    except Exception:
        continue
    rel=p.relative_to(ROOT).as_posix()
    for i,line in enumerate(s.splitlines(),1):
        for name,rx in patterns:
            if rx.search(line):
                secret_hits.append({'path':rel,'line':i,'pattern':name})
        m=generic.search(line)
        if m:
            v=m.group(2).lower()
            if not any(x in v for x in ['example','dummy','placeholder','changeme','not-a-real','test-only','unset','github.']):
                generic_hits.append({'path':rel,'line':i,'kind':m.group(1).lower()})
if secret_hits:add('CRITICAL','HIGH_CONFIDENCE_SECRET_MATERIAL','High-confidence secret-like material exists in tracked files.',secret_hits[:100])
if generic_hits:add('HIGH','HARDCODED_CREDENTIAL_LIKE_VALUES','Credential-like literal values require review.',generic_hits[:100])

core=load(ROOT/'canonical/yado-unified-core-v1.json')
active=list(core.get('active_runtime_sources',[]))
if 'runtime/yado_unified_core_v1.py' not in active:active.append('runtime/yado_unified_core_v1.py')
risk_calls=[]
for rel in active:
    p=ROOT/rel
    if not p.exists():continue
    try:tree=ast.parse(p.read_text(encoding='utf-8'))
    except Exception:continue
    for n in ast.walk(tree):
        if not isinstance(n,ast.Call):continue
        name=''
        if isinstance(n.func,ast.Name):name=n.func.id
        elif isinstance(n.func,ast.Attribute):
            parts=[];cur=n.func
            while isinstance(cur,ast.Attribute):parts.append(cur.attr);cur=cur.value
            if isinstance(cur,ast.Name):parts.append(cur.id)
            name='.'.join(reversed(parts))
        if name in {'eval','exec','compile','pickle.loads','marshal.loads','yaml.load','os.system','subprocess.Popen','subprocess.run'}:
            risk_calls.append({'path':rel,'line':getattr(n,'lineno',None),'call':name})
unsafe=[x for x in risk_calls if x['call'] in {'eval','exec','pickle.loads','marshal.loads','yaml.load','os.system'}]
if unsafe:add('HIGH','UNSAFE_DYNAMIC_EXECUTION_PRIMITIVES','Unsafe dynamic-execution/deserialization primitives are present in active runtime.',unsafe)
subproc=[x for x in risk_calls if x['call'].startswith('subprocess.')]
if subproc:add('INFO','ACTIVE_RUNTIME_SUBPROCESS_USAGE','Active runtime uses subprocess; review remains bounded by call sites.',subproc)

wfs=list((ROOT/'.github/workflows').glob('*.y*ml'))
contents_write=[]
pull_request_target=[]
unpinned=[]
third_party=[]
secret_refs=[]
for p in wfs:
    s=p.read_text(encoding='utf-8',errors='replace')
    if re.search(r'(?m)^\s*contents:\s*write\s*$',s):contents_write.append(p.name)
    if re.search(r'(?m)^\s*pull_request_target\s*:',s):pull_request_target.append(p.name)
    for m in re.finditer(r'(?m)^\s*-?\s*uses:\s*([^\s#]+)',s):
        spec=m.group(1).strip().strip('"\'')
        if spec.startswith('./'):continue
        if '@' in spec:
            action,ver=spec.rsplit('@',1)
            if not re.fullmatch(r'[0-9a-fA-F]{40}',ver):unpinned.append({'workflow':p.name,'uses':spec})
            if not action.startswith('actions/'):third_party.append({'workflow':p.name,'uses':spec})
    if '${{ secrets.' in s:secret_refs.append(p.name)

if pull_request_target:add('CRITICAL','PULL_REQUEST_TARGET_PRESENT','pull_request_target workflows require manual security review.',pull_request_target)
if contents_write:add('HIGH','LARGE_WRITE_ENABLED_WORKFLOW_SURFACE',f'{len(contents_write)} workflows request contents: write.',contents_write[:120])
if unpinned:add('MEDIUM','ACTIONS_NOT_PINNED_TO_COMMIT',f'{len(unpinned)} action references use tags/branches rather than immutable commit SHAs.',unpinned[:150])
if third_party:add('MEDIUM','THIRD_PARTY_ACTIONS_USED',f'{len(third_party)} third-party action references are present.',third_party[:100])

pip_path=ROOT/'audits'/'yado-pip-audit-v1.json'
dep_vulns=[]
dep_error=None
if pip_path.exists():
    try:
        pdata=json.loads(pip_path.read_text(encoding='utf-8'))
        deps=pdata.get('dependencies',pdata if isinstance(pdata,list) else [])
        for d in deps:
            for v in d.get('vulns',[]) or []:
                dep_vulns.append({'dependency':d.get('name'),'version':d.get('version'),'id':v.get('id'),'fix_versions':v.get('fix_versions',[])})
    except Exception as e:dep_error=repr(e)
else:dep_error='pip-audit output missing'
if dep_vulns:add('HIGH','KNOWN_DEPENDENCY_VULNERABILITIES',f'{len(dep_vulns)} known dependency vulnerability records found.',dep_vulns[:100])
elif dep_error:add('MEDIUM','DEPENDENCY_AUDIT_UNAVAILABLE','Dependency audit output could not be parsed.',dep_error)

rank={'CRITICAL':4,'HIGH':3,'MEDIUM':2,'LOW':1,'INFO':0}
status='PASS' if not any(rank.get(f['severity'],0)>=2 for f in findings) else 'FAIL_AUDIT'
report={
 'schema':'yado.security_audit.v1','status':status,
 'tracked_files_scanned':len(tracked),'active_runtime_files_scanned':len(active),'workflow_files_scanned':len(wfs),
 'high_confidence_secret_hits':len(secret_hits),'generic_credential_hits':len(generic_hits),
 'active_runtime_risk_calls':risk_calls,
 'workflow_summary':{'contents_write':len(contents_write),'pull_request_target':len(pull_request_target),'unpinned_actions':len(unpinned),'third_party_actions':len(third_party),'secret_ref_workflows':len(secret_refs)},
 'dependency_vulnerability_count':len(dep_vulns),'findings':sorted(findings,key=lambda x:-rank.get(x['severity'],0))
}
OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
