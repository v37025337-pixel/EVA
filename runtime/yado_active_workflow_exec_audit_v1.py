from __future__ import annotations
from pathlib import Path
import json,re

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'audits'/'yado-active-workflow-exec-audit-v1.json'
OUT.parent.mkdir(exist_ok=True)

active=[]
missing=[]
checked=[]
for p in (ROOT/'.github/workflows').glob('*.y*ml'):
    text=p.read_text(encoding='utf-8',errors='replace')
    m=re.search(r'branches:\s*\[([^\]]+)\]',text)
    branches=[]
    if m: branches=[x.strip().strip("'\"") for x in m.group(1).split(',')]
    if 'yado-architecture-shadow-search' not in branches:
        continue
    active.append(p.name)

    lines=text.splitlines()
    current_wd=''
    for line in lines:
        wm=re.match(r'^\s*working-directory:\s*([^#]+)',line)
        if wm: current_wd=wm.group(1).strip().strip("'\"")
        for sm in re.finditer(r'python(?:3)?\s+(?!-m\b)([^\s"\'|;&]+\.py)',line):
            raw=sm.group(1)
            rel=Path(current_wd)/raw if current_wd and not raw.startswith('runtime/') else Path(raw)
            rel=rel.as_posix()
            checked.append({'workflow':p.name,'kind':'python','path':rel})
            if not (ROOT/rel).exists():missing.append({'workflow':p.name,'kind':'python','path':rel})
        for rm in re.finditer(r'(?:^|\s)-r\s+([^\s"\'|;&]+)',line):
            raw=rm.group(1)
            rel=Path(current_wd)/raw if current_wd and not raw.startswith('runtime/') else Path(raw)
            rel=rel.as_posix()
            checked.append({'workflow':p.name,'kind':'requirements','path':rel})
            if not (ROOT/rel).exists():missing.append({'workflow':p.name,'kind':'requirements','path':rel})

# Deduplicate.
seen=set();uniq=[]
for x in missing:
    k=(x['workflow'],x['kind'],x['path'])
    if k not in seen: seen.add(k);uniq.append(x)

report={
 'schema':'yado.active_workflow_exec_audit.v1',
 'active_branch_workflows':len(active),
 'required_exec_inputs_checked':len(checked),
 'missing_required_exec_inputs':len(uniq),
 'missing':uniq,
 'status':'PASS' if not uniq else 'FAIL_AUDIT'
}
OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
