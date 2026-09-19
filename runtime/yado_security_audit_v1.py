from __future__ import annotations
from pathlib import Path
import ast,hashlib,importlib.metadata,json,re,subprocess,sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'audits'/'yado-security-audit-v1-report.json'
REQUIREMENTS=('runtime/yado_rc8_v36/requirements-github.txt','successor/requirements.txt')
PIP_REPORT=ROOT/'audits/yado-pip-audit-v1.json'
PIP_EVIDENCE=ROOT/'audits/yado-pip-audit-v1-evidence.json'
EVIDENCE_MAX_AGE_SECONDS=3600

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def run(cmd):
    try:p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    except OSError:return 127,'','COMMAND_UNAVAILABLE'
    return p.returncode,p.stdout,p.stderr

def sha(data):return hashlib.sha256(data).hexdigest()

def current_commit():
    rc,out,_=run(['git','rev-parse','--verify','HEAD'])
    if rc or not re.fullmatch(r'[0-9a-f]{40}',out.strip()):
        raise ValueError('GIT_COMMIT_UNAVAILABLE')
    return out.strip()

def requirement_hashes():
    return {name:sha((ROOT/name).read_bytes()) for name in REQUIREMENTS}

def collect_dependency_evidence():
    """Capture one actual pip-audit invocation; never infer success from JSON alone."""
    # Invalidate old evidence before any operation that can fail.
    PIP_EVIDENCE.write_text(json.dumps({'status':'WITHHOLD_INCOMPLETE_COLLECTION'})+'\n')
    before=requirement_hashes()
    commit=current_commit()
    started=datetime.now(timezone.utc).isoformat()
    command=[sys.executable,'-m','pip_audit','--strict']
    for name in REQUIREMENTS:command.extend(['-r',name])
    command.extend(['-f','json'])
    try:tool_version=importlib.metadata.version('pip-audit')
    except importlib.metadata.PackageNotFoundError:tool_version='UNAVAILABLE'
    try:
        process=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=1200)
        raw,returncode=process.stdout,process.returncode
    except (OSError,subprocess.TimeoutExpired):
        raw,returncode=b'',127
    PIP_REPORT.write_bytes(raw)
    if before!=requirement_hashes() or commit!=current_commit():
        raise ValueError('DEPENDENCY_INPUTS_CHANGED_DURING_AUDIT')
    evidence={
        'schema':'yado.pip_audit_evidence.v1','git_commit':commit,
        'requirements':before,'tool':{'name':'pip-audit','version':tool_version},
        'command':{'requirements':list(REQUIREMENTS),'format':'json'},
        'returncode':returncode,'started_at':started,
        'finished_at':datetime.now(timezone.utc).isoformat(),'report_sha256':sha(raw),
    }
    PIP_EVIDENCE.write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
    # Collection success is distinct from audit success. The verifier below gates it.
    print(json.dumps({'status':'DEPENDENCY_EVIDENCE_COLLECTED','pip_audit_returncode':returncode}))

def release_version(value):
    # The two admitted requirement files use release-only PEP 440 comparisons.
    # Reject unsupported syntax rather than approximate prerelease/marker semantics.
    if type(value) is not str or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)*',value):
        raise ValueError('UNSUPPORTED_DEPENDENCY_RELEASE_VERSION')
    parts=tuple(map(int,value.split('.')))
    while len(parts)>1 and parts[-1]==0:parts=parts[:-1]
    return parts

def declared_requirements():
    required={}
    for relative in REQUIREMENTS:
        rows=[]
        for line in (ROOT/relative).read_text(encoding='utf-8').splitlines():
            line=line.split('#',1)[0].strip()
            if not line:continue
            match=re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9_.-]*)\s*((?:==|!=|>=|<=|>|<).+)',line)
            if not match:raise ValueError('UNSUPPORTED_REQUIREMENT_SYNTAX:'+relative)
            name=re.sub(r'[-_.]+','-',match[1]).lower()
            specs=[]
            for part in match[2].split(','):
                spec=re.fullmatch(r'\s*(==|!=|>=|<=|>|<)\s*([0-9]+(?:\.[0-9]+)*)\s*',part)
                if not spec:raise ValueError('UNSUPPORTED_REQUIREMENT_SPECIFIER:'+relative)
                specs.append((spec[1],release_version(spec[2])))
            required.setdefault(name,[]).extend(specs)
            rows.append(name)
        if not rows:raise ValueError('EMPTY_REQUIREMENT_FILE:'+relative)
    return required

def validate_dependency_evidence():
    proof=load(PIP_EVIDENCE)
    if not isinstance(proof,dict) or proof.get('schema')!='yado.pip_audit_evidence.v1':
        raise ValueError('DEPENDENCY_PROOF_SCHEMA')
    if proof.get('git_commit')!=current_commit():raise ValueError('DEPENDENCY_PROOF_COMMIT_MISMATCH')
    if proof.get('requirements')!=requirement_hashes():raise ValueError('DEPENDENCY_PROOF_REQUIREMENTS_MISMATCH')
    if proof.get('command')!={'requirements':list(REQUIREMENTS),'format':'json'}:
        raise ValueError('DEPENDENCY_PROOF_COMMAND_COVERAGE')
    if type(proof.get('returncode')) is not int or proof['returncode']!=0:
        raise ValueError('DEPENDENCY_AUDIT_NONZERO_OR_INVALID_EXIT')
    tool=proof.get('tool')
    if (not isinstance(tool,dict) or tool.get('name')!='pip-audit'
            or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)+',str(tool.get('version','')))):
        raise ValueError('DEPENDENCY_AUDIT_TOOL_UNVERIFIED')
    started=datetime.fromisoformat(proof['started_at'])
    finished=datetime.fromisoformat(proof['finished_at'])
    now=datetime.now(timezone.utc)
    if (started.tzinfo is None or finished.tzinfo is None or started>finished
            or (finished-now).total_seconds()>60 or (now-started).total_seconds()>EVIDENCE_MAX_AGE_SECONDS):
        raise ValueError('DEPENDENCY_PROOF_STALE_OR_INVALID_TIME')
    raw=PIP_REPORT.read_bytes()
    if proof.get('report_sha256')!=sha(raw):raise ValueError('DEPENDENCY_REPORT_DIGEST_MISMATCH')
    report=json.loads(raw)
    if (not isinstance(report,dict) or not isinstance(report.get('dependencies'),list)
            or not report['dependencies'] or 'error' in report):
        raise ValueError('DEPENDENCY_REPORT_SCHEMA_OR_EMPTY')
    dependencies={}
    vulnerabilities=[]
    for row in report['dependencies']:
        if (not isinstance(row,dict) or 'skip_reason' in row or 'error' in row
                or type(row.get('name')) is not str or not row['name']
                or type(row.get('version')) is not str or not row['version']
                or not isinstance(row.get('vulns'),list)):
            raise ValueError('DEPENDENCY_REPORT_SKIPPED_OR_INCOMPLETE')
        name=re.sub(r'[-_.]+','-',row['name']).lower()
        if name in dependencies:raise ValueError('DEPENDENCY_REPORT_DUPLICATE_NAME')
        dependencies[name]=row['version']
        for vuln in row['vulns']:
            if (not isinstance(vuln,dict) or type(vuln.get('id')) is not str or not vuln['id']
                    or not isinstance(vuln.get('fix_versions'),list)
                    or any(type(v) is not str for v in vuln['fix_versions'])):
                raise ValueError('DEPENDENCY_VULNERABILITY_SCHEMA')
            vulnerabilities.append({'dependency':row['name'],'version':row['version'],
                                    'id':vuln['id'],'fix_versions':vuln['fix_versions']})
    for name,specs in declared_requirements().items():
        if name not in dependencies:raise ValueError('DEPENDENCY_REQUIRED_PACKAGE_MISSING:'+name)
        actual=release_version(dependencies[name])
        for op,expected in specs:
            left=actual+(0,)*max(0,len(expected)-len(actual))
            right=expected+(0,)*max(0,len(actual)-len(expected))
            matches={'==':left==right,'!=':left!=right,'>=':left>=right,'<=':left<=right,'>':left>right,'<':left<right}
            if not matches[op]:raise ValueError('DEPENDENCY_VERSION_OUTSIDE_REQUIREMENTS:'+name)
    return vulnerabilities,{'status':'VERIFIED_FRESH_BOUND_EVIDENCE','dependency_count':len(dependencies),
                            'git_commit':proof['git_commit'],'requirements':proof['requirements'],
                            'report_sha256':proof['report_sha256'],'finished_at':proof['finished_at'],'tool':tool}

def valid_test_reference(reference):
    if type(reference) is not str or reference.count('::')!=1:return False
    relative,symbol=reference.split('::')
    path=(ROOT/relative).resolve()
    if not path.is_relative_to(ROOT) or path.suffix!='.py' or not symbol.split('.')[-1].startswith('test_'):
        return False
    try:tree=ast.parse(path.read_text(encoding='utf-8'))
    except (OSError,UnicodeError,SyntaxError):return False
    def symbols(node,prefix=''):
        for child in ast.iter_child_nodes(node):
            if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                name=prefix+child.name
                if not isinstance(child,ast.ClassDef):yield name
                yield from symbols(child,name+'.')
            else:yield from symbols(child,prefix)
    return symbol in set(symbols(tree))

def reviewed_dynamic_sites(sites):
    path=ROOT/'.github/yado-dynamic-execution-review-v1.json'
    if not path.exists():return [],[]
    try:
        policy=load(path)
        if (not isinstance(policy,dict) or policy.get('schema')!='yado.dynamic_execution_review.v1'
                or not isinstance(policy.get('reviews'),list)):
            raise ValueError('DYNAMIC_REVIEW_POLICY_SCHEMA')
    except (OSError,UnicodeError,ValueError):return [],[{'reason':'UNREADABLE_OR_INVALID_POLICY'}]
    keys=('path','source_sha256','call','call_identity','ast_call_sha256')
    candidates={tuple(site[key] for key in keys):site for site in sites}
    reviewed=[]
    invalid=[]
    seen=set()
    for row in policy['reviews']:
        if not isinstance(row,dict):
            invalid.append({'reason':'INVALID_REVIEW_SCHEMA'})
            continue
        binding=tuple(row.get(key) for key in keys)
        tests=row.get('test_references')
        if (any(type(value) is not str for value in binding) or binding not in candidates or binding in seen
                or type(row.get('boundary')) is not str or not row['boundary'].strip()
                or not isinstance(tests,list) or not tests or not all(valid_test_reference(ref) for ref in tests)):
            invalid.append({'path':row.get('path'),'call_identity':row.get('call_identity'),'reason':'UNBOUND_OR_INCOMPLETE_REVIEW'})
            continue
        seen.add(binding)
        reviewed.append({**candidates[binding],'boundary':row['boundary'],'test_references':tests})
    return reviewed,invalid

def main():
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'status':'WITHHOLD_INCOMPLETE_SECURITY_AUDIT'})+'\n')
    if len(sys.argv)>1:
        if sys.argv[1:]!=['--collect-dependencies']:raise SystemExit('Usage: yado_security_audit_v1.py [--collect-dependencies]')
        collect_dependency_evidence()
        raise SystemExit(0)

    findings=[]
    def add(sev,code,msg,details=None):
        findings.append({'severity':sev,'code':code,'message':msg,'details':details})

    rc,out,err=run(['git','ls-files'])
    if rc:add('HIGH','GIT_TRACKED_FILE_SCAN_UNAVAILABLE','Cannot establish the tracked-file scan.',{'exit_code':rc})
    tracked=[ROOT/x for x in out.splitlines() if x.strip()]
    if not tracked:add('HIGH','EMPTY_TRACKED_FILE_SCAN','No tracked files were established for scanning.')
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
    active_scanned=0
    for rel in active:
        p=ROOT/rel
        if not p.is_file() or not p.resolve().is_relative_to(ROOT):
            add('HIGH','ACTIVE_SOURCE_MISSING_OR_OUTSIDE_ROOT','Declared active source cannot be scanned.',{'path':rel})
            continue
        try:
            raw=p.read_bytes()
            tree=ast.parse(raw.decode('utf-8'))
        except (OSError,UnicodeError,SyntaxError):
            add('HIGH','ACTIVE_SOURCE_UNREADABLE_OR_INVALID','Declared active source cannot be parsed.',{'path':rel})
            continue
        active_scanned+=1
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
                risk_calls.append({'path':rel,'line':n.lineno,'column':n.col_offset,'call':name,
                                   'call_identity':f'{name}:{n.lineno}:{n.col_offset}','source_sha256':sha(raw),
                                   'ast_call_sha256':sha(ast.dump(n,include_attributes=False).encode('utf-8'))})
    unsafe=[x for x in risk_calls if x['call'] in {'eval','exec','pickle.loads','marshal.loads','yaml.load','os.system'}]
    reviewed_sites,invalid_reviews=reviewed_dynamic_sites(unsafe)
    reviewed_bindings={(row['path'],row['call_identity']) for row in reviewed_sites}
    unreviewed=[row for row in unsafe if (row['path'],row['call_identity']) not in reviewed_bindings]
    if invalid_reviews:add('HIGH','INVALID_DYNAMIC_EXECUTION_REVIEW','Dynamic-execution review is stale, unbound, or incomplete.',invalid_reviews)
    if unreviewed:add('HIGH','UNSAFE_DYNAMIC_EXECUTION_PRIMITIVES','Dynamic-execution sites require explicit source-bound boundary review.',unreviewed)
    if reviewed_sites:add('INFO','REVIEWED_DYNAMIC_EXECUTION_BOUNDARIES','Reviewed call sites have specific boundaries; this is not a general Python sandbox.',reviewed_sites)
    subproc=[x for x in risk_calls if x['call'].startswith('subprocess.')]
    if subproc:add('INFO','ACTIVE_RUNTIME_SUBPROCESS_USAGE','Active runtime uses subprocess; review remains bounded by call sites.',subproc)

    wfs=list((ROOT/'.github/workflows').glob('*.y*ml'))
    allowlist_path=ROOT/'.github/yado-active-workflow-allowlist-v1.json'
    allowlist=json.loads(allowlist_path.read_text(encoding='utf-8')) if allowlist_path.exists() else {}
    active_allow=set(allowlist.get('active_workflows') or [])
    write_allow=set(allowlist.get('write_authorized_workflows') or [])
    workflow_names={p.name for p in wfs}
    unauthorized_active=sorted(workflow_names-active_allow)
    missing_active=sorted(active_allow-workflow_names)
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

    if unauthorized_active:add('CRITICAL','WORKFLOW_OUTSIDE_SINGLE_CORE_ALLOWLIST','Executable workflows exist outside the single-core allowlist.',unauthorized_active)
    if missing_active:add('MEDIUM','ALLOWLIST_REFERENCES_MISSING_WORKFLOW','Allowlist references workflows not present in the executable directory.',missing_active)
    if len(wfs)>int(allowlist.get('max_active_workflow_count') or 40):add('HIGH','ACTIVE_WORKFLOW_COUNT_EXCEEDS_BOUND',f'{len(wfs)} executable workflows exceed the bounded single-core limit.',[p.name for p in wfs][:120])
    if pull_request_target:add('CRITICAL','PULL_REQUEST_TARGET_PRESENT','pull_request_target workflows require manual security review.',pull_request_target)
    unauthorized_write=sorted(set(contents_write)-write_allow)
    if unauthorized_write:add('HIGH','UNAUTHORIZED_WRITE_ENABLED_WORKFLOW','Workflows request contents: write without explicit single-core authorization.',unauthorized_write)
    elif contents_write:add('INFO','AUTHORIZED_BOUNDED_WRITE_WORKFLOW_SURFACE',f'{len(contents_write)} active G2 workflows have explicit contents: write authorization.',sorted(contents_write)[:120])
    if unpinned:add('MEDIUM','ACTIONS_NOT_PINNED_TO_COMMIT',f'{len(unpinned)} action references use tags/branches rather than immutable commit SHAs.',unpinned[:150])
    if third_party:add('MEDIUM','THIRD_PARTY_ACTIONS_USED',f'{len(third_party)} third-party action references are present.',third_party[:100])

    dep_vulns=[]
    dep_error=None
    dependency_evidence={'status':'WITHHOLD_UNVERIFIED_DEPENDENCIES'}
    try:dep_vulns,dependency_evidence=validate_dependency_evidence()
    except (OSError,ValueError,TypeError,KeyError) as error:dep_error=type(error).__name__+':'+str(error)
    if dep_vulns:add('HIGH','KNOWN_DEPENDENCY_VULNERABILITIES',f'{len(dep_vulns)} known dependency vulnerability records found.',dep_vulns[:100])
    elif dep_error:add('MEDIUM','DEPENDENCY_AUDIT_UNAVAILABLE','Fresh, complete, bound dependency evidence is required.',dep_error)

    rank={'CRITICAL':4,'HIGH':3,'MEDIUM':2,'LOW':1,'INFO':0}
    status='PASS' if not any(rank.get(f['severity'],0)>=2 for f in findings) else 'FAIL_AUDIT'
    report={
     'schema':'yado.security_audit.v1','status':status,
     'tracked_files_scanned':len(tracked),'active_runtime_files_scanned':active_scanned,'active_runtime_files_declared':len(active),'workflow_files_scanned':len(wfs),
     'high_confidence_secret_hits':len(secret_hits),'generic_credential_hits':len(generic_hits),
     'active_runtime_risk_calls':risk_calls,
     'dynamic_execution_review':{'site_count':len(unsafe),'reviewed_count':len(reviewed_sites),
                                 'unreviewed_count':len(unreviewed),'invalid_review_count':len(invalid_reviews),
                                 'general_python_sandbox':False},
     'workflow_summary':{'contents_write':len(contents_write),'pull_request_target':len(pull_request_target),'unpinned_actions':len(unpinned),'third_party_actions':len(third_party),'secret_ref_workflows':len(secret_refs)},
     'dependency_vulnerability_count':None if dep_error else len(dep_vulns),'dependency_evidence':dependency_evidence,
     'findings':sorted(findings,key=lambda x:-rank.get(x['severity'],0))
    }
    OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2,sort_keys=True))
    if status!='PASS':raise SystemExit(2)


if __name__=='__main__':
    main()
